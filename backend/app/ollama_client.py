from .llm import LLMError, generate_text


class OllamaError(LLMError):
    pass


def generate_with_ollama(prompt: str) -> str:
    try:
        return generate_text(prompt)
    except LLMError as exc:
        raise OllamaError(str(exc)) from exc
