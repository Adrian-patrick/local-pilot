from __future__ import annotations

from . import anthropic_client, gemini_client, groq_client, ollama, openai_client
from .base import GenerationConfig, LLMError
from ..config import get_settings


PROVIDERS = {"ollama", "openai", "anthropic", "gemini", "groq", "auto"}


def generate_text(prompt: str, config: GenerationConfig | None = None) -> str:
    settings = get_settings()
    generation_config = config or GenerationConfig()
    provider = settings.model_provider

    if provider not in PROVIDERS:
        raise LLMError(f"Unsupported model provider: {provider}")

    if provider == "auto":
        return _generate_auto(prompt, generation_config)

    return _generate_with_provider(provider, prompt, generation_config)


def _generate_auto(prompt: str, config: GenerationConfig) -> str:
    settings = get_settings()
    try:
        return ollama.generate(prompt, settings, config)
    except LLMError as local_error:
        if not settings.allow_cloud_fallback:
            raise local_error

        for provider in ("openai", "anthropic", "gemini", "groq"):
            try:
                return _generate_with_provider(provider, prompt, config)
            except LLMError:
                continue
        raise LLMError("Local model failed and no configured cloud fallback worked.") from local_error


def _generate_with_provider(provider: str, prompt: str, config: GenerationConfig) -> str:
    settings = get_settings()
    if provider == "ollama":
        return ollama.generate(prompt, settings, config)
    if provider == "openai":
        return openai_client.generate(prompt, settings, config)
    if provider == "anthropic":
        return anthropic_client.generate(prompt, settings, config)
    if provider == "gemini":
        return gemini_client.generate(prompt, settings, config)
    if provider == "groq":
        return groq_client.generate(prompt, settings, config)
    raise LLMError(f"Unsupported model provider: {provider}")
