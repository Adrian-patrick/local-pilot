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
      context_collector.py File/folder context collection
      extractors.py        Text and PDF extraction
      folder_scanner.py    Folder structure scanner
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

For development, double-click:

```text
desktop/registry/add-local-pilot-dev.reg
```

Then:

1. Right click a file or folder.
2. On Windows 11, choose `Show more options`.
3. Click `Local Pilot`.
4. Ask a question in the popup chat window.

The popup uses Ollama locally. Recommended first model:

```bash
ollama pull qwen3:8b
```

For slower machines:

```bash
ollama pull qwen3:4b
```

If `ollama` is not recognized in PowerShell, open the Ollama app once or restart your terminal after installing Ollama.

To remove it, double-click:

```text
desktop/registry/remove-local-pilot.reg
```

## GitHub Authorship

This repo can be owned by Adrian while your commits still show as yours. See:

```text
docs/github-ownership.md
```
