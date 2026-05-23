from .rag_engine import answer_with_rag


def answer_question(path: str, question: str) -> dict:
    return answer_with_rag(path, question)
