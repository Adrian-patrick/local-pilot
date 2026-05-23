from __future__ import annotations

import re

from .context_collector import collect_context
from .ollama_client import OllamaError, generate_with_ollama
from .rag_store import (
    connect,
    content_hash,
    create_workspace,
    get_item,
    load_chunks,
    load_history,
    load_workspace_chunks,
    load_workspace_history,
    path_id,
    replace_chunks,
    save_message,
    upsert_item,
)


CHUNK_SIZE = 1_400
CHUNK_OVERLAP = 180
TOP_K = 6
MAX_CONTEXT_CHARS = 8_000


def answer_with_rag(path: str, question: str) -> dict:
    return answer_workspace([path], question)


def answer_workspace(paths: list[str], question: str) -> dict:
    contexts = [collect_context(path) for path in paths]
    workspace = _ensure_workspace(contexts)
    extracted_text = "\n\n".join(context.get("text") or "" for context in contexts)

    with connect() as con:
        chunks = load_workspace_chunks(con, workspace["id"])
        history = load_workspace_history(con, workspace["id"])
        retrieved = retrieve_chunks(question, chunks, top_k=TOP_K)

    if not retrieved:
        answer = "I don't see readable content in the selected workspace."
        sources = workspace["paths"]
    else:
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

        chunks = _chunk_text(text, source=context["path"])
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


def _chunk_text(text: str, source: str) -> list[dict]:
    clean = _normalize_text(text)
    if not clean:
        return []

    chunks: list[dict] = []
    start = 0
    chunk_index = 0
    while start < len(clean):
        end = min(start + CHUNK_SIZE, len(clean))
        chunk_text = clean[start:end].strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "source": source,
                    "metadata": {},
                }
            )
            chunk_index += 1
        if end >= len(clean):
            break
        start = max(0, end - CHUNK_OVERLAP)

    return chunks


def retrieve_chunks(question: str, chunks: list[dict], top_k: int = TOP_K) -> list[dict]:
    query_terms = _terms(question)
    scored = []

    for chunk in chunks:
        text = chunk["text"]
        chunk_terms = _terms(text)
        exact_hits = sum(text.lower().count(term) for term in query_terms)
        overlap = len(query_terms & chunk_terms)
        density = overlap / max(1, len(query_terms))
        score = exact_hits * 2.0 + overlap + density
        scored.append((score, chunk))

    ranked = [chunk for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]
    if not ranked:
        ranked = chunks[:top_k]
    return ranked[:top_k]


def _deterministic_answer(question: str, chunks: list[dict], extracted_text: str = "") -> str | None:
    lowered = question.lower()
    text = extracted_text or "\n".join(chunk["text"] for chunk in chunks)
    is_project_request = "project" in lowered and not lowered.startswith("extract only technical")
    if is_project_request:
        return _deterministic_projects(text)
    if "skill" in lowered:
        return _deterministic_skills(text)
    if "experience" in lowered:
        return _deterministic_experience(text)


def _deterministic_projects(text: str) -> str | None:
    project_section = _section_between(
        text,
        start_markers=("Projects",),
        end_markers=("Education", "Certifications", "Leadership", "Achievements"),
    )

    projects = _extract_project_lines(project_section or text)
    if len(projects) < 2 and project_section:
        projects = _merge_unique(projects, _extract_project_lines(text))
    if not projects:
        return None

    return "Projects mentioned:\n" + "\n".join(f"- {project}" for project in projects)


def _deterministic_skills(text: str) -> str | None:
    section = _section_between(
        text,
        start_markers=("Technical Skills", "Skills"),
        end_markers=("Research", "Experience", "Projects", "Education"),
    )
    if not section:
        return None
    lines = _clean_section_lines(section, skip_headers=("Technical Skills", "Skills"))
    if not lines:
        return None
    return "Skills mentioned:\n" + "\n".join(f"- {line}" for line in lines[:10])


def _deterministic_experience(text: str) -> str | None:
    research = _section_between(
        text,
        start_markers=("Research",),
        end_markers=("Experience", "Projects", "Education"),
    )
    experience = _section_between(
        text,
        start_markers=("Experience",),
        end_markers=("Projects", "Education", "Publication", "Certifications"),
    )
    blocks = []
    if research:
        blocks.append("Research:\n" + "\n".join(_clean_section_lines(research, skip_headers=("Research",))[:6]))
    if experience:
        blocks.append("Experience:\n" + "\n".join(_clean_section_lines(experience, skip_headers=("Experience",))[:10]))
    if not blocks:
        return None
    return "\n\n".join(blocks)


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
    lower = text.lower()
    starts = [lower.find(marker.lower()) for marker in markers]
    starts = [index for index in starts if index >= 0]
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


def _merge_unique(first: list[str], second: list[str]) -> list[str]:
    merged = list(first)
    for item in second:
        if item not in merged:
            merged.append(item)
    return merged


def _generate_corrected_answer(
    question: str,
    chunks: list[dict],
    history: list[dict],
    workspace: dict,
) -> tuple[str, str]:
    prompt = _build_grounded_prompt(question, chunks, history, workspace)
    try:
        answer = generate_with_ollama(prompt)
    except OllamaError as exc:
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
        return generate_with_ollama(retry_prompt), "RETRIED"
    except OllamaError:
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
        "For list questions about projects, skills, experience, tools, education, or achievements, "
        "return a clear bullet list with short evidence from the context.\n"
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
    if "skill" in lowered:
        return (
            "Return only skills. Group them as Programming, AI/ML, Frameworks/Libraries, "
            "Cloud/MLOps, and Tools. Exclude project names, company names, dates, links, "
            "paper names, datasets, and certifications unless they are clearly skills/tools."
        )
    if "project" in lowered:
        return (
            "Return only actual project names with one-line descriptions. Exclude standalone "
            "tools, technologies, datasets, companies, paper titles, dates, and links."
        )
    if "experience" in lowered:
        return (
            "Return only work, internship, and research experience. Include role, organization, "
            "timeframe when present, and concrete work done."
        )
    if "summar" in lowered or "profile" in lowered:
        return "Summarize the selected document into concise, useful bullets."
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

    context_terms = _terms(" ".join(chunk["text"] for chunk in chunks))
    answer_terms = {term for term in _terms(answer) if len(term) >= 5}
    if not answer_terms:
        return "PASS", "Short answer."

    unsupported = answer_terms - context_terms
    unsupported_ratio = len(unsupported) / max(1, len(answer_terms))
    if unsupported_ratio > 0.65:
        return "FAIL", "Too many answer terms are not present in retrieved context."
    return "PASS", "Answer appears grounded in retrieved context."


def _terms(text: str) -> set[str]:
    stopwords = {
        "about",
        "after",
        "again",
        "also",
        "because",
        "before",
        "being",
        "could",
        "document",
        "from",
        "have",
        "into",
        "only",
        "selected",
        "that",
        "their",
        "there",
        "these",
        "this",
        "using",
        "what",
        "when",
        "where",
        "which",
        "with",
        "would",
    }
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9_+#.-]{3,}", text.lower())
        if token not in stopwords
    }


def _normalize_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())


def _setup_help(workspace: dict, question: str, error: str) -> str:
    return (
        "I opened the selected item, but I could not get an answer from Ollama yet.\n\n"
        f"Selected: {workspace['title']}\n"
        f"Question: {question}\n\n"
        f"Problem: {error}\n\n"
        "Fix:\n"
        "1. Open Ollama.\n"
        "2. Make sure the selected model is installed.\n"
        "3. Try Local Pilot again."
    )
