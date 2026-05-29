from .agentic_rag import answer


def answer_question(path: str, question: str) -> dict:
    return answer([path], question)
