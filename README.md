# Stage 1 Prototype — Local Pilot MVP

## Goal

Prove that OS-native contextual AI interactions are dramatically better than traditional chatbot workflows.

The prototype focuses on:

> Right Click → Ask Agent

for files and folders directly inside the operating system.

---

# Core Experience

Instead of:
- opening ChatGPT
- uploading files
- manually explaining context

Users can:

1. Right click a file or folder
2. Select `Ask Local Pilot`
3. Ask a question
4. Receive contextual answers instantly

---

# Supported Inputs

## Files
- PDF
- TXT
- Markdown
- Python / JS / Code files
- Images

## Folders
- Code repositories
- Project folders
- Documentation folders

---

# Supported Actions

## File Actions
- Summarize file
- Explain file
- Ask custom questions
- Extract action items
- Rewrite content
- Translate content

---

## Folder Actions
- Explain project structure
- Summarize repository
- Identify important files
- Trace architecture flow
- Generate documentation

---

# Example Workflow

## Example 1 — PDF

Right Click:
`report.pdf`

Ask:
> "Summarize the key risks"

Local Pilot:
- reads PDF
- extracts text
- understands context
- generates concise answer

---

## Example 2 — Codebase

Right Click:
`backend-service/`

Ask:
> "Explain authentication flow"

Local Pilot:
- scans repository
- identifies auth-related files
- traces logic flow
- explains architecture

---

# Stage 1 Features

## 1. OS Context Menu Integration
Adds:
> Ask Local Pilot

inside:
- Windows Explorer
- Finder
- Linux File Managers

---

## 2. Context Collector

Automatically gathers:
- selected file
- file type
- metadata
- folder structure
- neighboring files

without manual upload.

---

## 3. File Understanding Engine

Processes:
- PDFs
- text
- code
- images

using:
- parsers
- OCR
- embeddings

---

## 4. AI Agent Runtime

Handles:
- summarization
- Q&A
- contextual retrieval
- code understanding

---

## 5. Lightweight Native UI

Minimal popup/overlay:
- fast
- distraction-free
- OS-native feeling

---

# Tech Stack

## Frontend
- Tauri / Electron

## Backend
- Python
- FastAPI

## AI
- Ollama
- Local LLMs
- OpenAI fallback

## Retrieval
- ChromaDB / FAISS

## Parsing
- PyMuPDF
- Tree-sitter
- OCR

---

# Architecture

┌──────────────────────────────┐
│      Operating System        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│     Context Menu Hook        │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│      Context Collector       │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│   File Understanding Layer   │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Agent Runtime          │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│       Response Window        │
└──────────────────────────────┘

---

# Non-Goals (Stage 1)

The MVP will NOT include:
- autonomous agents
- voice assistant
- browser control
- full OS memory
- proactive actions
- cross-device sync

Focus is:
- contextual AI
- native workflows
- file intelligence

---

# Success Criteria

The prototype succeeds if users feel:

> "I never want to manually upload files into chatbots again."

Key validation:
- reduced friction
- faster workflows
- contextual usefulness
- strong UX feel

---

# Future Stages

## Stage 2
- repository-wide memory
- semantic search
- cross-file reasoning

## Stage 3
- workflow automation
- cross-app orchestration
- persistent memory

## Stage 4
- proactive AI operating system
- voice-native interaction
- autonomous task execution
