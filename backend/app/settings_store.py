from __future__ import annotations

import os
from pathlib import Path

from .config import get_settings


ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

SETTING_KEYS = (
    "LOCAL_PILOT_MODEL_PROVIDER",
    "LOCAL_PILOT_ALLOW_CLOUD_FALLBACK",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
    "GEMINI_API_KEY",
    "GEMINI_MODEL",
    "GROQ_API_KEY",
    "GROQ_MODEL",
)


def read_env_values() -> dict[str, str]:
    values: dict[str, str] = {}
    if not ENV_PATH.exists():
        return values

    for raw in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def save_env_values(updates: dict[str, str]) -> None:
    current = read_env_values()
    for key, value in updates.items():
        if key in SETTING_KEYS:
            current[key] = value.strip()
            os.environ[key] = value.strip()

    lines = [f"{key}={current.get(key, '')}" for key in SETTING_KEYS]
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    get_settings.cache_clear()
