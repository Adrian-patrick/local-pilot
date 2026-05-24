from __future__ import annotations

from .base import LLMError
from .http import get_json
from ..config import get_settings


ANTHROPIC_MODELS = [
    "claude-3-5-haiku-latest",
    "claude-3-5-sonnet-latest",
    "claude-3-7-sonnet-latest",
]

GROQ_FALLBACK_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
]


def list_models(provider: str, overrides: dict[str, str] | None = None) -> list[str]:
    settings = get_settings()
    values = overrides or {}
    provider = provider.lower()

    if provider == "auto":
        provider = "ollama"
    if provider == "ollama":
        return _ollama_models(values.get("OLLAMA_BASE_URL") or settings.ollama_base_url)
    if provider == "openai":
        return _openai_models(values.get("OPENAI_API_KEY") or settings.openai_api_key)
    if provider == "anthropic":
        return ANTHROPIC_MODELS
    if provider == "gemini":
        return _gemini_models(values.get("GEMINI_API_KEY") or settings.gemini_api_key)
    if provider == "groq":
        return _groq_models(values.get("GROQ_API_KEY") or settings.groq_api_key)

    raise LLMError(f"Unsupported provider for model discovery: {provider}")


def test_provider(provider: str, overrides: dict[str, str] | None = None) -> str:
    models = list_models(provider, overrides=overrides)
    if not models:
        raise LLMError(f"No models found for {provider}.")
    return models[0]


def _ollama_models(base_url: str) -> list[str]:
    data = get_json(f"{base_url.rstrip('/')}/api/tags", headers={}, timeout=20)
    models = [item.get("name", "") for item in data.get("models", [])]
    return sorted(model for model in models if model)


def _openai_models(api_key: str | None) -> list[str]:
    if not api_key:
        raise LLMError("OpenAI API key is required to fetch models.")
    api_key = api_key.strip()
    data = get_json(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20,
    )
    models = [item.get("id", "") for item in data.get("data", [])]
    return sorted(model for model in models if model)


def _groq_models(api_key: str | None) -> list[str]:
    if not api_key:
        return GROQ_FALLBACK_MODELS
    api_key = api_key.strip()
    data = get_json(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20,
    )
    models = [item.get("id", "") for item in data.get("data", [])]
    return sorted(model for model in models if model)


def _gemini_models(api_key: str | None) -> list[str]:
    if not api_key:
        raise LLMError("Gemini API key is required to fetch models.")
    api_key = api_key.strip()
    data = get_json(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}",
        headers={},
        timeout=20,
    )
    models = []
    for item in data.get("models", []):
        name = item.get("name", "").replace("models/", "")
        methods = item.get("supportedGenerationMethods", [])
        if name and "generateContent" in methods:
            models.append(name)
    return sorted(models)
