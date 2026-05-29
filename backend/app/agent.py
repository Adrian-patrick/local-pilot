from .agentic_rag import answer


def answer_question(path: str, question: str, answer_mode: str = "selected_files_only") -> dict:
    return answer([path], question, answer_mode=answer_mode)
