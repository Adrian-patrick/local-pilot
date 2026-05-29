from __future__ import annotations

from ..rag_store import connect, load_workspace_chunks, load_workspace_history, save_message
from .corrective_agent import append_source_note, answer_with_correction
from .ingestion import collect_and_index
from .retriever import retrieve


def answer(paths: list[str], question: str) -> dict:
    workspace, _extracted_text = collect_and_index(paths)

    with connect() as con:
        chunks = load_workspace_chunks(con, workspace.id)
        history = load_workspace_history(con, workspace.id)

    if _is_memory_question(question):
        answer_text = _memory_answer(history)
        sources: list[str] = []
    else:
        retrieved = retrieve(question, chunks)
        if not retrieved:
            answer_text = "I don't see readable content in the selected workspace."
            sources = workspace.paths
        else:
            result = answer_with_correction(
                question=question,
                chunks=retrieved,
                history=history,
                workspace=workspace,
            )
            answer_text = append_source_note(result.answer, retrieved)
            sources = result.sources

    with connect() as con:
        primary_item_id = workspace.item_ids[0]
        save_message(con, primary_item_id, "user", question, workspace_id=workspace.id)
        save_message(con, primary_item_id, "assistant", answer_text, workspace_id=workspace.id)

    return {
        "answer": answer_text,
        "selected_path": workspace.selection_label,
        "sources": sources,
    }


def _is_memory_question(question: str) -> bool:
    lowered = question.lower()
    return any(
        phrase in lowered
        for phrase in (
            "past conversation",
            "past chat",
            "past question",
            "previous conversation",
            "previous chat",
            "previous question",
            "conversation history",
            "chat history",
            "did i ask",
            "have i asked",
            "what did i ask",
        )
    )


def _memory_answer(history: list[dict]) -> str:
    user_questions = [msg["content"].strip() for msg in history if msg["role"] == "user" and msg["content"].strip()]
    if not user_questions:
        return "No, I don't see any past conversation for this selected file or workspace yet."

    recent = user_questions[-5:]
    lines = "\n".join(f"- {question}" for question in recent)
    return "Yes. For this selected file or workspace, I found these previous questions:\n" + lines
