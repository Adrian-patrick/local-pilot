from __future__ import annotations

from .base import GenerationConfig, LLMError
from .http import post_json
from ..config import Settings


def generate(prompt: str, settings: Settings, config: GenerationConfig) -> str:
    if not settings.openai_api_key:
        raise LLMError("OpenAI API key is not configured.")

    payload = {
        "model": settings.openai_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    data = post_json(
        "https://api.openai.com/v1/chat/completions",
        payload,
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        timeout=config.timeout_seconds,
    )
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as exc:
        raise LLMError("OpenAI returned an unexpected response.") from exc
