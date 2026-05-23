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

