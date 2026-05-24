from __future__ import annotations

from .base import GenerationConfig, LLMError
from .http import post_json
from ..config import Settings


def generate(prompt: str, settings: Settings, config: GenerationConfig) -> str:
    if not settings.anthropic_api_key:
        raise LLMError("Anthropic API key is not configured.")

    payload = {
        "model": settings.anthropic_model,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
        "messages": [{"role": "user", "content": prompt}],
    }
    data = post_json(
        "https://api.anthropic.com/v1/messages",
        payload,
        headers={
            "x-api-key": settings.anthropic_api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=config.timeout_seconds,
    )
    try:
        parts = data["content"]
        return "\n".join(part.get("text", "") for part in parts if part.get("type") == "text").strip()
    except KeyError as exc:
        raise LLMError("Anthropic returned an unexpected response.") from exc
