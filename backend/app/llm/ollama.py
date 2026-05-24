from __future__ import annotations

from .base import GenerationConfig, LLMError
from .http import post_json
from ..config import Settings


def generate(prompt: str, settings: Settings, config: GenerationConfig) -> str:
    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {
        "model": settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": config.temperature,
            "num_ctx": 4096,
            "num_predict": config.max_tokens,
        },
    }
    data = post_json(url, payload, headers={}, timeout=config.timeout_seconds)
    answer = data.get("response", "").strip()
    if not answer:
        raise LLMError("Ollama returned an empty response.")
    return answer
