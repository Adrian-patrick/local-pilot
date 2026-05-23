from .context_collector import collect_context
from .ollama_client import OllamaError, generate_with_ollama


def answer_question(path: str, question: str) -> dict:
    context = collect_context(path)
    answer = _ollama_answer(context, question)

    return {
        "answer": answer,
        "selected_path": context["path"],
        "sources": context["sources"],
    }


def _ollama_answer(context: dict, question: str) -> str:
    prompt = _build_prompt(context, question)
    try:
        return generate_with_ollama(prompt)
    except OllamaError as exc:
        return _setup_help(context, question, str(exc))


def _build_prompt(context: dict, question: str) -> str:
    text = context.get("text") or ""
    preview = text[:20_000].strip() or "[No readable text found]"
    sources = "\n".join(f"- {source}" for source in context.get("sources", [])[:15])

    return (
        "You are Local Pilot, a local AI assistant that answers questions about "
        "the selected file or folder on the user's computer.\n\n"
        "Rules:\n"
        "- Answer using the provided context.\n"
        "- If the context is not enough, say what is missing.\n"
        "- Be concise, useful, and practical.\n"
        "- Mention relevant file names when helpful.\n\n"
        f"Selected item: {context['path']}\n"
        f"Selected type: {context['kind']}\n"
        f"Summary: {context['summary']}\n\n"
        f"Sources:\n{sources}\n\n"
        f"Context:\n{preview}\n\n"
        f"User question: {question}\n\n"
        "Answer:"
    )


def _setup_help(context: dict, question: str, error: str) -> str:
    return (
        "I opened the selected item, but I could not get an answer from Ollama yet.\n\n"
        f"Selected: {context['path']}\n"
        f"Question: {question}\n\n"
        f"Problem: {error}\n\n"
        "Fix:\n"
        "1. Install and open Ollama.\n"
        "2. Run: ollama pull qwen3:8b\n"
        "3. Try Local Pilot again.\n\n"
        "For a slower computer, use: ollama pull qwen3:4b"
    )
