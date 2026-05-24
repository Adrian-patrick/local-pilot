from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    path: str = Field(..., description="Selected file or folder path")
    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    selected_path: str
    sources: list[str]


class ContextResponse(BaseModel):
    path: str
    kind: str
    name: str
    summary: str
    sources: list[str]
    text_preview: str | None = None


class SettingsResponse(BaseModel):
    model_provider: str
    ollama_base_url: str
    ollama_model: str
    openai_model: str
    anthropic_model: str
    gemini_model: str
    groq_model: str
    allow_cloud_fallback: bool
    has_openai_key: bool
    has_anthropic_key: bool
    has_gemini_key: bool
    has_groq_key: bool


class SettingsUpdateRequest(BaseModel):
    model_provider: str | None = None
    allow_cloud_fallback: bool | None = None
    ollama_base_url: str | None = None
    ollama_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    anthropic_api_key: str | None = None
    anthropic_model: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    groq_api_key: str | None = None
    groq_model: str | None = None
