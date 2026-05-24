from fastapi import FastAPI, HTTPException
from .agent import answer_question
from .config import get_settings
from .context_collector import collect_context
from .schemas import (
    AskRequest,
    AskResponse,
    ContextResponse,
    ModelsResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)
from .llm.base import LLMError
from .llm.model_discovery import list_models
from .settings_store import save_env_values


app = FastAPI(title="Local Pilot", version="0.1.0")


@app.get("/")
def root() -> dict:
    return {
        "app": "Local Pilot",
        "status": "running",
        "routes": {
            "health": "/health",
            "api_docs": "/docs",
            "context": "/context?path=.",
            "ask": "POST /ask",
            "settings": "GET/POST /settings",
            "models": "/models?provider=ollama",
        },
    }


@app.get("/health")
def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "app": "Local Pilot",
        "model_provider": settings.model_provider,
        "ollama_model": settings.ollama_model,
    }


@app.get("/settings", response_model=SettingsResponse)
def settings() -> dict:
    settings = get_settings()
    return _settings_response(settings)


@app.post("/settings", response_model=SettingsResponse)
def update_settings(request: SettingsUpdateRequest) -> dict:
    key_map = {
        "model_provider": "LOCAL_PILOT_MODEL_PROVIDER",
        "allow_cloud_fallback": "LOCAL_PILOT_ALLOW_CLOUD_FALLBACK",
        "ollama_base_url": "OLLAMA_BASE_URL",
        "ollama_model": "OLLAMA_MODEL",
        "openai_api_key": "OPENAI_API_KEY",
        "openai_model": "OPENAI_MODEL",
        "anthropic_api_key": "ANTHROPIC_API_KEY",
        "anthropic_model": "ANTHROPIC_MODEL",
        "gemini_api_key": "GEMINI_API_KEY",
        "gemini_model": "GEMINI_MODEL",
        "groq_api_key": "GROQ_API_KEY",
        "groq_model": "GROQ_MODEL",
    }
    updates = {}
    payload = request.model_dump(exclude_none=True)
    for field, value in payload.items():
        env_key = key_map[field]
        updates[env_key] = str(value).lower() if isinstance(value, bool) else str(value)

    if updates:
        save_env_values(updates)

    return _settings_response(get_settings())


@app.get("/models", response_model=ModelsResponse)
def models(provider: str = "ollama") -> dict:
    try:
        return {"provider": provider, "models": list_models(provider)}
    except LLMError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/context", response_model=ContextResponse)
def context(path: str) -> dict:
    try:
        data = collect_context(path)
        return {
            "path": data["path"],
            "kind": data["kind"],
            "name": data["name"],
            "summary": data["summary"],
            "sources": data["sources"],
            "text_preview": data.get("text_preview"),
        }
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict:
    try:
        return answer_question(request.path, request.question)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _settings_response(settings) -> dict:
    return {
        "model_provider": settings.model_provider,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_model": settings.ollama_model,
        "openai_model": settings.openai_model,
        "anthropic_model": settings.anthropic_model,
        "gemini_model": settings.gemini_model,
        "groq_model": settings.groq_model,
        "allow_cloud_fallback": settings.allow_cloud_fallback,
        "has_openai_key": bool(settings.openai_api_key),
        "has_anthropic_key": bool(settings.anthropic_api_key),
        "has_gemini_key": bool(settings.gemini_api_key),
        "has_groq_key": bool(settings.groq_api_key),
    }
