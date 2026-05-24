# Local Pilot

Local Pilot is an OS-native contextual AI layer for files, folders, and codebases.

The Stage 1 prototype proves one core workflow:

```text
Right click a file or folder -> Ask Local Pilot -> get a contextual answer
```

## Stage 1 Scope

The first build focuses on Windows Explorer integration.

Supported early inputs:

- PDF files
- DOCX and PPTX files
- TXT and Markdown files
- Python, JavaScript, TypeScript, HTML, CSS, JSON, YAML, and similar text/code files
- Folders and code repositories

Stage 1 does not include autonomous agents, voice control, browser control, full OS memory, or cross-device sync.

## Current Project Structure

```text
local-pilot/
  backend/
    app/
      main.py              FastAPI app
      agent.py             Stage 1 answer runtime
      rag_engine.py        Local corrective RAG flow
      setup_check.py       First-run readiness checks
      llm/                 Model router for Ollama/OpenAI/Claude/Gemini/Groq
      rag_store.py         SQLite item memory and chunk store
      context_collector.py File/folder context and readable content collection
      extractors.py        Text, PDF, DOCX, and PPTX extraction
      folder_scanner.py    Folder scanner with binary/build output filtering
      schemas.py           API request/response models
    local_pilot_cli.py     CLI entry point for context-menu testing
  desktop/
    registry/
      add-local-pilot-dev.reg
      remove-local-pilot.reg
  docs/
    github-ownership.md
    stage-1-build-plan.md
```

## Run The CLI Prototype

From the repo root:

```bash
pip install -r requirements.txt
python backend/local_pilot_cli.py "C:\Path\To\FileOrFolder"
```

## Run The API

```bash
uvicorn backend.app.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/health
```

Example API request:

```bash
curl -X POST http://127.0.0.1:8000/ask ^
  -H "Content-Type: application/json" ^
  -d "{\"path\":\"C:\\Path\\To\\FileOrFolder\",\"question\":\"Summarize this\"}"
```

## Add Windows Context Menu Entry

For development, run:

```text
powershell.exe -ExecutionPolicy Bypass -File desktop/registry/install-local-pilot-dev.ps1
```

Then:

1. Right click a file or folder.
2. On Windows 11, choose `Show more options`.
3. Click `Local Pilot`.
4. Ask a question in the popup chat window.

The popup uses Ollama locally. Quick test model:

```bash
ollama pull gemma3:1b
```

Stronger model:

```bash
ollama pull qwen3:8b
```

For slower machines:

```bash
ollama pull qwen3:4b
```

If `ollama` is not recognized in PowerShell, open the Ollama app once or restart your terminal after installing Ollama.

The popup also has a `Settings` button where you can choose the model provider, change model names, and add API keys.
Use the `Setup` button to check whether Ollama, the context menu, the selected provider, and local memory are ready.

## AI Providers

Local Pilot uses Ollama by default so selected file content stays on your computer.

In the popup, click `Settings` to configure:

- provider: Ollama, auto, OpenAI, Claude, Gemini, or Groq
- model names
- API keys
- cloud fallback behavior

Configure the provider with environment variables:

```bash
LOCAL_PILOT_MODEL_PROVIDER=ollama
OLLAMA_MODEL=gemma3:1b
```

Supported provider values:

```text
ollama
openai
anthropic
gemini
groq
auto
```

Cloud providers need API keys:

```bash
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...
GROQ_API_KEY=...
```

`auto` tries Ollama first. Cloud fallback is disabled unless explicitly enabled:

```bash
LOCAL_PILOT_MODEL_PROVIDER=auto
LOCAL_PILOT_ALLOW_CLOUD_FALLBACK=true
```

Privacy rule: cloud providers receive the selected chunks needed to answer the question.

The backend also exposes provider settings for a future React/Electron settings screen:

```text
GET  /settings
POST /settings
GET  /models?provider=ollama
GET  /setup/status
```

## Local RAG Memory

Local Pilot stores per-file/folder memory locally:

```text
backend/data/local_pilot.db
```

For each selected item it stores:

- extracted chunks
- content hash
- chat history
- source references

Answers are built from retrieved chunks from the selected item, then sent to Ollama.
For folders, Local Pilot stores the folder structure plus readable contents from supported files.

## Workspace Engine

Every selection is treated as a workspace internally:

```text
one file -> workspace with one item
many files -> workspace with many items
folder -> workspace with folder context
```

The current right-click popup still passes one path, but the backend now supports multi-path workspaces through `answer_workspace(paths, question)`.

To remove it, double-click:

```text
desktop/registry/remove-local-pilot.reg
```

## GitHub Authorship

This repo can be owned by Adrian while your commits still show as yours. See:

```text
docs/github-ownership.md
```
