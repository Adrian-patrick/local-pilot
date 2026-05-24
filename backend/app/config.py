from dataclasses import dataclass
from functools import lru_cache
import os


try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


@dataclass(frozen=True)
class Settings:
    model_provider: str
    openai_api_key: str | None
    anthropic_api_key: str | None
    gemini_api_key: str | None
    groq_api_key: str | None
    ollama_base_url: str
    ollama_model: str
    openai_model: str
    anthropic_model: str
    gemini_model: str
    groq_model: str
    allow_cloud_fallback: bool
    max_file_chars: int
    max_folder_files: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        model_provider=os.getenv("LOCAL_PILOT_MODEL_PROVIDER", "ollama").lower(),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        groq_api_key=os.getenv("GROQ_API_KEY"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "gemma3:1b"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-haiku-latest"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
        groq_model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        allow_cloud_fallback=os.getenv("LOCAL_PILOT_ALLOW_CLOUD_FALLBACK", "false").lower()
        in {"1", "true", "yes", "on"},
        max_file_chars=int(os.getenv("LOCAL_PILOT_MAX_FILE_CHARS", "120000")),
        max_folder_files=int(os.getenv("LOCAL_PILOT_MAX_FOLDER_FILES", "200")),
    )
