from __future__ import annotations

import re

from .context_collector import collect_context
from .llm import LLMError, generate_text
from .rag import chunk_text, retrieve_chunks, terms
from .rag_store import (
    connect,
    content_hash,
    create_workspace,
    get_item,
    load_workspace_chunks,
    load_workspace_history,
    path_id,
    replace_chunks,
    save_message,
    upsert_item,
)


TOP_K = 10
MAX_CONTEXT_CHARS = 14_000


def answer_with_rag(path: str, question: str) -> dict:
    return answer_workspace([path], question)


def answer_workspace(paths: list[str], question: str) -> dict:
    contexts = [collect_context(path) for path in paths]
    workspace = _ensure_workspace(contexts)
    extracted_text = "\n\n".join(context.get("text") or "" for context in contexts)

    with connect() as con:
        chunks = load_workspace_chunks(con, workspace["id"])
        history = load_workspace_history(con, workspace["id"])

    memory_question = _is_memory_question(question)
    if memory_question:
        answer = _memory_answer(history)
        sources = []
    else:
        retrieved = retrieve_chunks(question, chunks, top_k=TOP_K)
        retrieved = _expand_context_for_question(question, chunks, retrieved)

    if not memory_question and not retrieved:
        answer = "I don't see readable content in the selected workspace."
        sources = workspace["paths"]
    elif not memory_question:
        extracted_answer = _profile_answer(question, chunks, extracted_text)
        if not extracted_answer:
            extracted_answer = _named_person_answer(question, extracted_text)
        if not extracted_answer:
            extracted_answer = _deterministic_answer(question, chunks, extracted_text)
        if extracted_answer:
            answer = extracted_answer
        else:
            answer, validation = _generate_corrected_answer(question, retrieved, history, workspace)
        sources = sorted({chunk["source"] for chunk in retrieved})
        answer = _append_source_note(answer, retrieved)

    with connect() as con:
        primary_item_id = workspace["item_ids"][0]
        save_message(con, primary_item_id, "user", question, workspace_id=workspace["id"])
        save_message(con, primary_item_id, "assistant", answer, workspace_id=workspace["id"])

    return {
        "answer": answer,
        "selected_path": workspace["selection_label"],
        "sources": sources,
    }


def _ensure_workspace(contexts: list[dict]) -> dict:
    item_ids = [_ensure_indexed(context) for context in contexts]
    workspace_id = _workspace_id(item_ids)
    selection_type = "single" if len(item_ids) == 1 else "multi"
    title = _workspace_title(contexts)

    with connect() as con:
        create_workspace(
            con,
            workspace_id=workspace_id,
            title=title,
            selection_type=selection_type,
            item_ids=item_ids,
        )

    return {
        "id": workspace_id,
        "item_ids": item_ids,
        "title": title,
        "selection_type": selection_type,
        "selection_label": title,
        "paths": [context["path"] for context in contexts],
    }


def _workspace_id(item_ids: list[str]) -> str:
    return "ws_" + content_hash("|".join(sorted(item_ids)))[:24]


def _workspace_title(contexts: list[dict]) -> str:
    if len(contexts) == 1:
        return contexts[0]["path"]
    return f"{len(contexts)} selected items"


def _ensure_indexed(context: dict) -> str:
    item_id = path_id(context["path"])
    text = context.get("text") or ""
    item_hash = content_hash(text)

    with connect() as con:
        existing = get_item(con, item_id)
        if existing and existing["content_hash"] == item_hash:
            return item_id

        chunks = chunk_text(text, source=context["path"])
        upsert_item(
            con,
            item_id=item_id,
            path=context["path"],
            kind=context["kind"],
            name=context["name"],
            item_hash=item_hash,
        )
        replace_chunks(con, item_id, chunks)

    return item_id


def _deterministic_answer(question: str, chunks: list[dict], extracted_text: str = "") -> str | None:
    lowered = question.lower()
    if _is_general_document_question(lowered) and not _requested_sections(lowered):
        return None

    text = extracted_text or "\n".join(chunk["text"] for chunk in chunks)
    sections = _requested_sections(lowered)
    if not sections:
        return None

    blocks = []
    for section_name in sections:
        section = _section_between(text, (section_name,), COMMON_SECTION_HEADINGS)
        if section_name == "Projects":
            lines = _extract_project_lines(section)
        else:
            lines = _clean_section_lines(section, skip_headers=(section_name,))
        if lines:
            blocks.append(f"{section_name}:\n" + "\n".join(f"- {line}" for line in lines[:10]))

    if not blocks:
        return None
    return "\n\n".join(blocks)


def _profile_answer(question: str, chunks: list[dict], extracted_text: str = "") -> str | None:
    lowered = question.lower()
    if not _is_general_document_question(lowered) or _requested_sections(lowered):
        return None

    text = extracted_text or "\n".join(chunk["text"] for chunk in chunks)
    if not _looks_like_profile_document(text):
        return None

    profile = _clean_section_lines(
        _section_between(text, ("Profile", "Summary", "Objective", "Overview"), COMMON_SECTION_HEADINGS),
        skip_headers=("Profile", "Summary", "Objective", "Overview"),
    )
    if not profile:
        return None

    subject = _document_subject(text)
    profile_sentence = _join_lines(profile[:6])
    if not profile_sentence:
        return None

    answer_parts = [f"{subject} is {profile_sentence[0].lower() + profile_sentence[1:] if subject != 'This document' else profile_sentence}"]

    skills = _compact_section_points(
        _section_between(text, ("Technical Skills", "Skills"), COMMON_SECTION_HEADINGS),
        skip_headers=("Technical Skills", "Skills"),
        limit=4,
    )
    if skills:
        answer_parts.append("Key areas: " + "; ".join(skills) + ".")

    experience = _compact_section_points(
        _section_between(text, ("Experience",), COMMON_SECTION_HEADINGS),
        skip_headers=("Experience",),
        limit=3,
    )
    if experience:
        answer_parts.append("Relevant experience: " + "; ".join(experience) + ".")

    return "\n\n".join(answer_parts)


def _looks_like_profile_document(text: str) -> bool:
    lowered = text.lower()
    profile_signals = sum(
        1
        for signal in (
            "technical skills",
            "skills",
            "experience",
            "projects",
            "intern",
            "github",
            "linkedin",
            "resume",
        )
        if signal in lowered
    )
    report_signals = sum(
        1
        for signal in (
            "certificate",
            "declaration",
            "submitted in partial",
            "chapter",
            "activity point programme",
            "visvesvaraya technological university",
        )
        if signal in lowered
    )
    return profile_signals >= 3 and report_signals < 3


def _named_person_answer(question: str, text: str) -> str | None:
    match = re.search(r"\bwho\s+(?:is|are|was|were)\s+([a-zA-Z][a-zA-Z ._-]{1,60})\??", question.strip(), re.I)
    if not match or not text:
        return None

    name = re.sub(r"\s+", " ", match.group(1)).strip(" ?.")
    name_terms = [term.lower() for term in re.findall(r"[a-zA-Z]{2,}", name)]
    if not name_terms:
        return None

    lines = [re.sub(r"\s+", " ", line.strip()) for line in text.splitlines()]
    lines = [line for line in lines if line]
    match_indexes = [
        index
        for index, line in enumerate(lines)
        if all(term in line.lower() for term in name_terms)
    ]
    if not match_indexes:
        return None

    evidence: list[str] = []
    for index in match_indexes[:4]:
        start = max(0, index - 4)
        end = min(len(lines), index + 9)
        for line in lines[start:end]:
            cleaned = _clean_evidence_line(line)
            if cleaned and cleaned not in evidence:
                evidence.append(cleaned)

    if not evidence:
        return None

    compact = " ".join(evidence[:18])
    compact = re.sub(r"\s+", " ", compact).strip()

    usn_match = re.search(r"\bUSN[:\s]+([A-Z0-9]+)", compact, re.I)
    degree_match = re.search(
        r"(Bachelor of Engineering in Computer Science\s*&?\s*Engineering\s*\(?Artificial Intelligence\)?)",
        compact,
        re.I,
    )
    college_match = re.search(
        r"(Dayananda Sagar Academy of Technology\s*&?\s*Management|DSATM)",
        compact,
        re.I,
    )
    programme_match = re.search(r"(AICTE Activity Point Programme)", compact, re.I)

    subject = _title_name(name)
    facts = []
    if degree_match:
        facts.append(f"is a student of {degree_match.group(1)}")
    elif "student" in compact.lower():
        facts.append("is described as a student")

    if college_match:
        facts.append(f"at {college_match.group(1)}")
    if usn_match:
        facts.append(f"with USN {usn_match.group(1)}")
    if programme_match:
        facts.append(f"connected to the {programme_match.group(1)}")

    if facts:
        answer = f"According to the selected document, {subject} " + ", ".join(facts) + "."
    else:
        answer = f"According to the selected document, {subject} is mentioned in this context: " + compact[:500]

    return answer + "\n\nEvidence found:\n" + "\n".join(f"- {line}" for line in evidence[:8])


def _clean_evidence_line(line: str) -> str:
    cleaned = line.strip(" -*•\t")
    cleaned = re.sub(r"[.…_]{4,}", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return ""
    if len(cleaned) > 180:
        return ""
    if cleaned.lower() in {"signature of", "signature of hod", "signature of principal"}:
        return ""
    return cleaned


def _title_name(name: str) -> str:
    parts = [part.capitalize() for part in re.findall(r"[a-zA-Z]+", name)]
    return " ".join(parts) if parts else name


def _document_subject(text: str) -> str:
    for raw in text.splitlines()[:8]:
        line = re.sub(r"\s+", " ", raw.strip())
        if not line:
            continue
        if any(marker in line for marker in ("@", "http", "linkedin", "github", "+91")):
            continue
        if 2 <= len(line) <= 80:
            return line
    return "This document"


def _join_lines(lines: list[str]) -> str:
    text = " ".join(line.rstrip(".") for line in lines if line)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[,;]\s*$", "", text)
    text = text.replace(",.", ".").replace(";.", ".")
    return text + "." if text and not text.endswith(".") else text


def _compact_section_points(section: str, skip_headers: tuple[str, ...], limit: int) -> list[str]:
    points = []
    for line in _clean_section_lines(section, skip_headers=skip_headers):
        if len(line) > 180:
            continue
        if re.search(r"^\d{4}|present$|india$|bengaluru", line.lower()):
            continue
        points.append(line.rstrip("."))
        if len(points) >= limit:
            break
    return points


COMMON_SECTION_HEADINGS = (
    "Summary",
    "Profile",
    "Objective",
    "Technical Skills",
    "Skills",
    "Research",
    "Experience",
    "Projects",
    "Education",
    "Publications",
    "Publication & Certifications",
    "Certifications",
    "Achievements",
    "Action Items",
    "Requirements",
    "Risks",
    "Decisions",
    "Next Steps",
)


def _requested_sections(question: str) -> list[str]:
    mapping = [
        (r"\btechnical skills\b", "Technical Skills"),
        (r"\bskills?\b", "Skills"),
        (r"\bresearch\b", "Research"),
        (r"\b(experience|experiences|experince|experinence|expirience)\b|\bwork history\b|\binternships?\b", "Experience"),
        (r"\bprojects\b|\blist\b.*\bproject\b|\bproject list\b", "Projects"),
        (r"\beducation\b", "Education"),
        (r"\bcertifications?\b", "Certifications"),
        (r"\bpublications?\b", "Publications"),
        (r"\baction items?\b", "Action Items"),
        (r"\brequirements?\b", "Requirements"),
        (r"\brisks?\b", "Risks"),
        (r"\bdecisions?\b", "Decisions"),
        (r"\bnext steps?\b", "Next Steps"),
    ]
    sections = []
    for pattern, section in mapping:
        if re.search(pattern, question) and section not in sections:
            sections.append(section)
    return sections


def _is_memory_question(question: str) -> bool:
    lowered = question.lower()
    return bool(
        re.search(r"\bpast\s+(conversation|chat|question|history)\b", lowered)
        or re.search(r"\bprevious\s+(conversation|chat|question|history)\b", lowered)
        or re.search(r"\bconversation\s+history\b", lowered)
        or re.search(r"\bchat\s+history\b", lowered)
        or re.search(r"\bdid i ask\b", lowered)
        or re.search(r"\bhave i asked\b", lowered)
        or re.search(r"\bwhat did i ask\b", lowered)
    )


def _memory_answer(history: list[dict]) -> str:
    user_questions = [msg["content"].strip() for msg in history if msg["role"] == "user" and msg["content"].strip()]

    if not user_questions:
        return "No, I don't see any past conversation for this selected file or workspace yet."

    recent = user_questions[-5:]
    lines = "\n".join(f"- {question}" for question in recent)
    return "Yes. For this selected file or workspace, I found these previous questions:\n" + lines


def _expand_context_for_question(question: str, chunks: list[dict], retrieved: list[dict]) -> list[dict]:
    if not chunks:
        return []

    expanded: list[dict] = []
    if _is_general_document_question(question.lower()):
        expanded.extend(chunks[:3])
        expanded.extend(_chunks_with_sections(chunks, {"summary", "profile", "objective", "overview"}))
        expanded.extend(_chunks_with_sections(chunks, {"skills", "experience", "projects"}))

    expanded.extend(retrieved)
    return _unique_chunks(expanded)[:TOP_K]


def _chunks_with_sections(chunks: list[dict], section_names: set[str]) -> list[dict]:
    matches = []
    for chunk in chunks:
        section = str((chunk.get("metadata") or {}).get("section") or "").lower()
        if any(name in section for name in section_names):
            matches.append(chunk)
    return matches


def _unique_chunks(chunks: list[dict]) -> list[dict]:
    unique = []
    seen: set[tuple[str, int]] = set()
    for chunk in chunks:
        key = (chunk["source"], int(chunk["chunk_index"]))
        if key in seen:
            continue
        seen.add(key)
        unique.append(chunk)
    return unique


def _is_general_document_question(question: str) -> bool:
    return bool(
        re.search(r"\bwho\s+(is|are|was|were)\b", question)
        or re.search(r"\bwhat\s+(is|are)\b", question)
        or re.search(r"\bwhat\s+does\b", question)
        or re.search(r"\btell me about\b", question)
        or re.search(r"\bdescribe\b", question)
        or re.search(r"\boverview\b", question)
        or re.search(r"\bprofile\b", question)
    )


def _section_between(text: str, start_markers: tuple[str, ...], end_markers: tuple[str, ...]) -> str:
    start = _find_heading(text, start_markers)
    if start < 0:
        return ""

    end = len(text)
    for marker in end_markers:
        marker_index = _find_heading(text[start + 1 :], (marker,))
        if marker_index >= 0:
            end = min(end, start + 1 + marker_index)
    return text[start:end]


def _find_heading(text: str, markers: tuple[str, ...]) -> int:
    for marker in markers:
        match = re.search(rf"(?im)^\s*{re.escape(marker)}\s*$", text)
        if match:
            return match.start()
    starts = []
    for marker in markers:
        match = re.search(rf"(?im)^\s*{re.escape(marker)}\b", text)
        if match:
            starts.append(match.start())
    return min(starts) if starts else -1


def _extract_project_lines(section: str) -> list[str]:
    lines = [line.strip(" -*•\t") for line in section.splitlines() if line.strip()]
    projects: list[str] = []

    for line in lines:
        lower = line.lower()
        cleaned = re.sub(r"\s+", " ", line)
        if len(cleaned) > 160:
            continue
        if cleaned.lower() == "projects":
            continue
        if not ("[github" in lower or "[live" in lower):
            continue
        if lower.startswith(("co-authored", "springer", "publication")):
            continue
        if cleaned not in projects:
            projects.append(cleaned)

    return projects[:8]


def _clean_section_lines(section: str, skip_headers: tuple[str, ...] = ()) -> list[str]:
    lines: list[str] = []
    for raw in section.splitlines():
        line = re.sub(r"\s+", " ", raw.strip(" -*•\t"))
        if not line:
            continue
        if any(line.lower() == header.lower() for header in skip_headers):
            continue
        if line not in lines:
            lines.append(line)
    return lines


def _generate_corrected_answer(
    question: str,
    chunks: list[dict],
    history: list[dict],
    workspace: dict,
) -> tuple[str, str]:
    prompt = _build_grounded_prompt(question, chunks, history, workspace)
    try:
        answer = generate_text(prompt)
    except LLMError as exc:
        return _setup_help(workspace, question, str(exc)), "ERROR"

    verdict, reason = _validate_answer(answer, chunks)
    if verdict == "PASS":
        return answer, verdict

    retry_prompt = (
        _build_grounded_prompt(question, chunks, history, workspace)
        + "\n\nYour previous answer was rejected because: "
        + reason
        + "\nRewrite the answer using only the provided workspace chunks."
    )
    try:
        return generate_text(retry_prompt), "RETRIED"
    except LLMError:
        return answer, "FAILED_VALIDATION"


def _build_grounded_prompt(
    question: str,
    chunks: list[dict],
    history: list[dict],
    workspace: dict,
) -> str:
    context_text = _format_chunks(chunks)
    history_text = _format_history(history)

    return (
        "You are Local Pilot, a workspace-grounded AI assistant.\n"
        "Answer ONLY using the selected workspace context below.\n"
        "Do not use outside knowledge.\n"
        "If the answer is present, answer directly and do not add uncertainty disclaimers.\n"
        "If the answer is not present in the selected files, say: "
        "\"I don't see that in the selected workspace.\"\n"
        "When possible, mention the source file.\n"
        "Handle any readable file type: documents, notes, data files, slides, code, or folders.\n"
        "For list questions, return a clear bullet list with short evidence from the context.\n"
        "For code or folder questions, explain files, functions, dependencies, and flow only when "
        "the selected context shows them.\n"
        "Do not stop after the first matching item if the context contains more.\n\n"
        f"Intent-specific instructions:\n{_intent_instructions(question)}\n\n"
        f"Workspace: {workspace['title']}\n"
        f"Selection type: {workspace['selection_type']}\n"
        f"Selected paths:\n{_format_paths(workspace['paths'])}\n\n"
        f"Previous conversation for this workspace:\n{history_text}\n\n"
        f"Selected workspace chunks:\n{context_text}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )


def _format_chunks(chunks: list[dict]) -> str:
    lines: list[str] = []
    total = 0
    for chunk in chunks:
        block = (
            f"[Source: {chunk['source']} | Chunk {chunk['chunk_index']}]\n"
            f"{chunk['text']}"
        )
        if total + len(block) > MAX_CONTEXT_CHARS:
            break
        lines.append(block)
        total += len(block)
    return "\n\n---\n\n".join(lines)


def _intent_instructions(question: str) -> str:
    lowered = question.lower()
    if "key point" in lowered or "important" in lowered:
        return "Extract the most important points from the selected context. Group related points when helpful."
    if "action" in lowered or "next step" in lowered or "risk" in lowered or "requirement" in lowered:
        return "Extract action items, decisions, requirements, risks, or next steps. If none are present, say so."
    if "named item" in lowered or "entities" in lowered or "records" in lowered:
        return "List important named items from the selected context with short descriptions grounded in the text."
    if "structure" in lowered or "architecture" in lowered or "flow" in lowered:
        return "Explain the structure and how the selected files connect, using file paths and code references when present."
    if "skill" in lowered:
        return (
            "Return only skills. Group them as Programming, AI/ML, Frameworks/Libraries, "
            "Cloud/MLOps, and Tools. Exclude project names, company names, dates, links, "
            "paper names, datasets, and certifications unless they are clearly skills/tools."
        )
    if re.search(r"\bprojects\b|\blist\b.*\bproject\b|\bproject list\b", lowered):
        return (
            "Return only actual project names with one-line descriptions. Exclude standalone "
            "tools, technologies, datasets, companies, paper titles, dates, and links."
        )
    if re.search(r"\b(experience|experiences|experince|experinence|expirience)\b|\bwork history\b|\binternships?\b", lowered):
        return (
            "Return only work, internship, and research experience. Include role, organization, "
            "timeframe when present, and concrete work done."
        )
    if "summar" in lowered or "profile" in lowered:
        return "Summarize the selected document into concise, useful bullets."
    if _is_general_document_question(lowered):
        return (
            "Answer as a general document-understanding question. Identify the main person, "
            "topic, object, project, or entity from the selected context, then summarize the "
            "most relevant facts from across the document. Do not return only one matching "
            "section unless the question explicitly asks for that section."
        )
    return "No special formatting beyond answering from the selected context."


def _append_source_note(answer: str, chunks: list[dict]) -> str:
    sources = []
    for chunk in chunks[:3]:
        source = chunk["source"]
        label = f"{source} (chunk {chunk['chunk_index']})"
        if label not in sources:
            sources.append(label)
    if not sources:
        return answer
    return answer.rstrip() + "\n\nSources used:\n" + "\n".join(f"- {source}" for source in sources)


def _format_history(history: list[dict]) -> str:
    if not history:
        return "None"
    return "\n".join(f"{msg['role']}: {msg['content'][:500]}" for msg in history[-6:])


def _format_paths(paths: list[str]) -> str:
    return "\n".join(f"- {path}" for path in paths)


def _validate_answer(answer: str, chunks: list[dict]) -> tuple[str, str]:
    lowered = answer.lower()
    if "i don't see" in lowered or "not in the selected document" in lowered:
        return "PASS", "Answer correctly says the document lacks the information."

    context_terms = set(terms(" ".join(chunk["text"] for chunk in chunks)))
    answer_terms = {term for term in terms(answer) if len(term) >= 5}
    if not answer_terms:
        return "PASS", "Short answer."

    unsupported = answer_terms - context_terms
    unsupported_ratio = len(unsupported) / max(1, len(answer_terms))
    if unsupported_ratio > 0.65:
        return "FAIL", "Too many answer terms are not present in retrieved context."
    return "PASS", "Answer appears grounded in retrieved context."


def _setup_help(workspace: dict, question: str, error: str) -> str:
    return (
        "I opened the selected item, but I could not get an answer from Ollama yet.\n\n"
        f"Selected: {workspace['title']}\n"
        f"Question: {question}\n\n"
        f"Problem: {error}\n\n"
        "Fix:\n"
        "1. Open Local Pilot Settings.\n"
        "2. Choose Ollama or add a cloud API key.\n"
        "3. Make sure the selected model is available.\n"
        "4. Try Local Pilot again."
    )
