from fastapi import FastAPI, HTTPException
from .agent import answer_question
from .context_collector import collect_context
from .schemas import AskRequest, AskResponse, ContextResponse


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
        },
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": "Local Pilot"}


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
