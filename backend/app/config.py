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
    ollama_base_url: str
    ollama_model: str
    max_file_chars: int
    max_folder_files: int


@lru_cache
def get_settings() -> Settings:
    return Settings(
        model_provider=os.getenv("LOCAL_PILOT_MODEL_PROVIDER", "mock"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        max_file_chars=int(os.getenv("LOCAL_PILOT_MAX_FILE_CHARS", "120000")),
        max_folder_files=int(os.getenv("LOCAL_PILOT_MAX_FOLDER_FILES", "200")),
    )
