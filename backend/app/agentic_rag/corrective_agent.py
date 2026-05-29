from __future__ import annotations

import re

from ..llm import LLMError, generate_text
from ..rag.retriever import terms
from .models import AgentResult, SMART_MODE, STRICT_MODE, WorkspaceState, normalize_answer_mode


MAX_CONTEXT_CHARS = 14_000
MAX_RETRIES = 2


def answer_with_correction(
    *,
    question: str,
    chunks: list[dict],
    history: list[dict],
    workspace: WorkspaceState,
    answer_mode: str = STRICT_MODE,
) -> AgentResult:
    mode = normalize_answer_mode(answer_mode)
    prompt = _build_prompt(question, chunks, history, workspace, mode)
    try:
        answer = generate_text(prompt)
    except LLMError as exc:
        return AgentResult(
            answer=_setup_help(workspace, question, str(exc)),
            validation="ERROR",
            sources=_sources(chunks),
        )

    verdict, reason = validate_answer(answer, chunks, mode)
    retry_count = 0
    while verdict == "FAIL" and retry_count < MAX_RETRIES:
        retry_count += 1
        retry_prompt = (
            prompt
            + "\n\nYour previous answer failed grounding validation.\n"
            + f"Reason: {reason}\n"
            + _retry_instruction(mode)
        )
        try:
            answer = generate_text(retry_prompt)
        except LLMError:
            break
        verdict, reason = validate_answer(answer, chunks, mode)

    answer = _clean_model_artifacts(answer, mode)
    validation = verdict if retry_count == 0 else f"{verdict}_AFTER_{retry_count}_RETRY"
    return AgentResult(answer=answer, validation=validation, sources=_sources(chunks))


def validate_answer(answer: str, chunks: list[dict], answer_mode: str = STRICT_MODE) -> tuple[str, str]:
    lowered = answer.lower()
    if "i don't see" in lowered or "not in the selected" in lowered:
        return "PASS", "Answer says context does not contain the information."

    if normalize_answer_mode(answer_mode) == SMART_MODE:
        return "PASS", "Smart mode permits general model knowledge with selected-file grounding instructions."

    context_terms = set(terms(" ".join(chunk["text"] for chunk in chunks)))
    answer_terms = {term for term in terms(answer) if len(term) >= 5}
    if not answer_terms:
        return "PASS", "Short answer."

    unsupported = answer_terms - context_terms
    unsupported_ratio = len(unsupported) / max(1, len(answer_terms))
    if unsupported_ratio > 0.65:
        return "FAIL", f"{unsupported_ratio:.0%} of answer terms were not in retrieved context."
    return "PASS", "Answer appears grounded."


def _build_prompt(
    question: str,
    chunks: list[dict],
    history: list[dict],
    workspace: WorkspaceState,
    answer_mode: str,
) -> str:
    mode_policy = _mode_policy(answer_mode)
    return (
        "You are Local Pilot, a source-grounded agentic RAG assistant.\n"
        "First infer the selected content type: document, report, resume, slides, spreadsheet, code, notes, folder, or repository.\n"
        "Then answer the user according to that content type.\n"
        f"{mode_policy}\n"
        "Prefer concise answers with bullets when helpful.\n"
        "Mention evidence from the selected file when useful.\n"
        "Never output fake tool calls, tool_code blocks, or markdown code fences unless the user explicitly asks for code.\n"
        "For code, explain only files/functions/flows visible in the chunks.\n"
        "For documents, answer from the document content, not from assumptions about the file name.\n\n"
        f"Answer mode: {answer_mode}\n\n"
        f"Intent instructions:\n{_intent_instructions(question)}\n\n"
        f"Workspace: {workspace.title}\n"
        f"Selection type: {workspace.selection_type}\n"
        f"Selected paths:\n{_format_paths(workspace.paths)}\n\n"
        f"Recent chat memory for this workspace:\n{_format_history(history)}\n\n"
        f"Retrieved source chunks:\n{_format_chunks(chunks)}\n\n"
        f"Question: {question}\n\n"
        "Answer:"
    )


def _mode_policy(answer_mode: str) -> str:
    if answer_mode == SMART_MODE:
        return (
            "Mode: Files + AI Knowledge.\n"
            "Use the selected chunks as the primary facts. You may also use general pretrained model knowledge "
            "for explanations, recommendations, comparisons, and improvements.\n"
            "Start the answer exactly with these three headings, in this order:\n"
            "From selected file:\n"
            "- Only factual points found in the selected chunks. No advice in this section.\n"
            "AI knowledge / suggestions:\n"
            "- General reasoning, best practices, comparisons, improvements, or advice.\n"
            "Next steps:\n"
            "- Concrete recommended actions.\n"
            "Do not write an introduction before 'From selected file:'.\n"
            "Do not copy internal chunk labels such as 'Retrieved source chunks', 'Source:', or 'Chunk' into the answer.\n"
            "Never invent facts about the selected file; label outside advice as model knowledge or suggestions."
        )
    return (
        "Mode: Selected Files Only.\n"
        "Use ONLY the selected workspace chunks below. Do not use outside knowledge.\n"
        "If the selected chunks do not contain the answer, say: \"I don't see that in the selected workspace.\""
    )


def _retry_instruction(answer_mode: str) -> str:
    if answer_mode == SMART_MODE:
        return (
            "Rewrite the answer so all file-specific claims are supported by selected chunks. "
            "Move any outside reasoning into an 'AI knowledge / suggestions' section and do not invent file facts."
        )
    return (
        "Rewrite the answer using only the selected workspace chunks. "
        "If the chunks do not contain the answer, say you do not see it."
    )


def _intent_instructions(question: str) -> str:
    lowered = question.lower()
    if re.search(r"\bwho\s+(is|are|was|were)\b", lowered):
        return (
            "Identify the named person/entity from nearby evidence. "
            "If text says 'Submitted by <name>', interpret that as authorship/submission, not as 'the person is submitted'."
        )
    if "summar" in lowered or "overview" in lowered or "what is this" in lowered:
        return "Summarize the selected file/workspace and identify its purpose."
    if "key point" in lowered or "important" in lowered:
        return "Extract the most important points from the selected context."
    if "action" in lowered or "next step" in lowered or "risk" in lowered or "requirement" in lowered:
        return "Extract action items, next steps, requirements, risks, and decisions when present."
    if "structure" in lowered or "architecture" in lowered or "flow" in lowered:
        return "Explain structure and flow using file paths or visible sections."
    if "skill" in lowered:
        return "Return only skills/tools clearly present in the selected context."
    if "project" in lowered:
        return "Return projects or project-related work clearly present in the selected context."
    return "Answer directly from the selected chunks."


def _format_chunks(chunks: list[dict]) -> str:
    lines: list[str] = []
    total = 0
    for chunk in chunks:
        block = f"[Source: {chunk['source']} | Chunk {chunk['chunk_index']}]\n{chunk['text']}"
        if total + len(block) > MAX_CONTEXT_CHARS:
            break
        lines.append(block)
        total += len(block)
    return "\n\n---\n\n".join(lines) if lines else "No retrieved chunks."


def _format_history(history: list[dict]) -> str:
    if not history:
        return "None"
    return "\n".join(f"{msg['role']}: {msg['content'][:500]}" for msg in history[-6:])


def _format_paths(paths: list[str]) -> str:
    return "\n".join(f"- {path}" for path in paths)


def _sources(chunks: list[dict]) -> list[str]:
    return sorted({chunk["source"] for chunk in chunks})


def _clean_model_artifacts(answer: str, answer_mode: str) -> str:
    cleaned = re.sub(r"```tool_code\s*([\s\S]*?)```", r"\1", answer).strip()
    cleaned = re.sub(r"(?im)^print\((['\"])(.*?)\1\)\s*$", r"\2", cleaned)
    if answer_mode == SMART_MODE:
        match = re.search(r"(?i)\bfrom selected file\s*:", cleaned)
        if match and match.start() > 0:
            cleaned = cleaned[match.start() :].lstrip()
        if not re.search(r"(?i)\bfrom selected file\s*:", cleaned):
            cleaned = (
                "From selected file:\n"
                "- Relevant chunks from the selected file/workspace were used as the grounding context.\n\n"
                "AI knowledge / suggestions:\n"
                f"{cleaned}\n\n"
                "Next steps:\n"
                "- Review the suggestions against the selected file.\n"
                "- Ask a more specific follow-up if you want edits, risks, action items, or a rewritten version."
            )
    return cleaned


def append_source_note(answer: str, chunks: list[dict]) -> str:
    labels = []
    for chunk in chunks[:4]:
        label = f"{chunk['source']} (chunk {chunk['chunk_index']})"
        if label not in labels:
            labels.append(label)
    if not labels:
        return answer
    return answer.rstrip() + "\n\nSources used:\n" + "\n".join(f"- {label}" for label in labels)


def _setup_help(workspace: WorkspaceState, question: str, error: str) -> str:
    return (
        "I opened the selected item, but I could not get an answer from the selected model yet.\n\n"
        f"Selected: {workspace.title}\n"
        f"Question: {question}\n\n"
        f"Problem: {error}\n\n"
        "Fix:\n"
        "1. Open Local Pilot Settings.\n"
        "2. Choose Ollama or add a cloud API key.\n"
        "3. Make sure the selected model is available.\n"
        "4. Try again."
    )
