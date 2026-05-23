from .context_collector import collect_context


def answer_question(path: str, question: str) -> dict:
    context = collect_context(path)
    answer = _mock_answer(context, question)

    return {
        "answer": answer,
        "selected_path": context["path"],
        "sources": context["sources"],
    }


def _mock_answer(context: dict, question: str) -> str:
    text = context.get("text") or ""
    kind = context["kind"]

    if kind == "folder":
        return (
            f"Local Pilot scanned the selected folder '{context['name']}'.\n\n"
            f"Question: {question}\n\n"
            "Initial folder context:\n"
            f"{context.get('text_preview') or '[No files found]'}\n\n"
            "Next step: connect Ollama or OpenAI so this folder context can be "
            "summarized and searched semantically."
        )

    if text.startswith("[Unsupported"):
        return (
            f"Local Pilot received '{context['name']}', but this file type is not "
            "supported by the Stage 1 extractor yet."
        )

    preview = text[:2_000].strip() or "[No readable text found]"
    return (
        f"Local Pilot read '{context['name']}'.\n\n"
        f"Question: {question}\n\n"
        "Readable preview:\n"
        f"{preview}\n\n"
        "Next step: connect Ollama or OpenAI to generate a real answer from this context."
    )

