# Stage 1 Build Plan

## Goal

Right click a file or folder, choose `Ask Local Pilot`, and get a contextual answer without manually uploading anything.

## First Milestone

1. Windows context menu calls Local Pilot with the selected path.
2. Local Pilot detects whether the path is a file or folder.
3. Text, Markdown, code, and PDF files can be read.
4. Folders can be scanned for structure.
5. A simple API can answer questions using the collected context.

## Current Prototype

The current scaffold includes:

- `backend/app/main.py`: FastAPI app with `/health`, `/context`, and `/ask`.
- `backend/local_pilot_cli.py`: command-line entry point for right-click testing.
- `desktop/registry/add-local-pilot-dev.reg`: Windows Explorer context menu entry for development.
- `desktop/registry/remove-local-pilot.reg`: cleanup script.

## Next Implementation Steps

1. Replace mock answers with Ollama.
2. Add OpenAI fallback.
3. Add a minimal Electron or Tauri response window.
4. Package the Python backend and desktop app.
5. Replace the development registry command with the packaged executable path.

