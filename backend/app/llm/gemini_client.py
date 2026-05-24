from __future__ import annotations

from .base import GenerationConfig, LLMError
from .http import post_json
from ..config import Settings


def generate(prompt: str, settings: Settings, config: GenerationConfig) -> str:
    if not settings.gemini_api_key:
        raise LLMError("Gemini API key is not configured.")

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": config.temperature,
            "maxOutputTokens": config.max_tokens,
        },
    }
    data = post_json(url, payload, headers={}, timeout=config.timeout_seconds)
    try:
        parts = data["candidates"][0]["content"]["parts"]
        return "\n".join(part.get("text", "") for part in parts).strip()
    except (KeyError, IndexError) as exc:
        raise LLMError("Gemini returned an unexpected response.") from exc
