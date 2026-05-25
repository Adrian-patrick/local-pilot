# Local Pilot

Local Pilot is an OS-native contextual AI assistant for files, folders, and codebases.

The core workflow is simple:

```text
Right click a file or folder -> Local Pilot opens -> ask questions -> get grounded answers with sources
```

Instead of opening a chatbot, uploading files, and explaining context manually, Local Pilot starts from the file or folder the user is already working with.

## Current Stage

Stage 1 is a Windows-first MVP.

Currently implemented:

- Windows Explorer right-click integration
- Desktop popup chat UI
- Local Ollama support
- Optional OpenAI, Claude, Gemini, and Groq provider settings
- Setup checker for Python, context menu, Ollama, provider, and local storage
- PDF, DOCX, PPTX, XLSX, TXT, Markdown, JSON, CSV, SQL, log, and code-file extraction
- Folder scanning with ignored build/cache/binary folders
- Local SQLite memory for indexed chunks and chat history
- Per-file and workspace-style answering
- Source references for answers

Not yet included:

- Packaged installer
- Modern Windows 11 main context-menu shell extension
- Image OCR
- Old `.doc` and `.ppt` parsing
- Full vector database retrieval
- Autonomous code-editing agent
- macOS Finder or Linux file-manager integration

## Product Architecture

This project combines two ideas:

1. A real working Local Pilot desktop app.
2. A clean layered agentic pipeline inspired by the 7-layer architecture plan.

The long-term product is not just a PDF chatbot. Local Pilot should become a context-aware specialist router:

```text
Right-click selection
    |
    v
Type + Task Detector
    |
    v
Specialist Router
    |
    v
Correct workflow for the selected context
```

This means Local Pilot should treat different selections differently:

| Selected Context | Specialist | Main Jobs |
| --- | --- | --- |
| PDF, TXT, DOCX, PPTX, XLSX, Markdown | Document Specialist | Summarize, explain, extract key points, answer from sources, rewrite, translate |
| Single code file | Code Specialist | Explain code, debug, find issues, suggest fixes, refactor, generate tests |
| Project folder or repository | Repository Specialist | Map architecture, trace flows, explain modules, find important files, debug across files |
| Empty or new project folder | Project Builder Specialist | Plan architecture, create files, generate code, run/test step by step |

The important design principle is:

```text
One strong context engine first.
Specialist behaviors on top.
```

Local Pilot should not start as a complicated multi-agent system. It should first build reliable context, memory, retrieval, and citations. Specialist workflows can then use that same engine.

The final product architecture is:

```text
Windows Explorer
    |
    v
Right-Click Context Menu
    |
    v
Local Pilot Desktop App
    |
    v
Selection Gateway
    |
    v
Type + Task Detector
    |
    v
Specialist Router
    |
    v
Context Engine / RAG Pipeline
    |
    v
Model Router
    |
    v
Ollama / OpenAI / Claude / Gemini / Groq
    |
    v
Chat UI + Sources + Actions + History
```

## Specialist Workflows

### Document Specialist

For PDFs, text files, Word documents, PowerPoint files, spreadsheets, Markdown, and similar documents.

Supported actions:

- summarize the document
- explain the document
- answer questions from the document
- extract action items
- find names, dates, risks, requirements, skills, projects, or decisions
- rewrite or translate content
- compare multiple selected documents later

Document modes:

```text
Strict Sources
    Answer only from the selected document or selected files.
    If the answer is not present, say it was not found.

Smart Assist
    Use the selected document plus general model knowledge.
    Clearly separate document facts from outside analysis or suggestions.
```

### Code Specialist

For a selected source-code file.

Supported actions:

- explain what the code does
- find bugs or risky logic
- suggest fixes
- refactor
- generate tests
- explain errors
- propose safe edits with user approval

Code modes:

```text
Repo Only
    Use only selected code/project context.

Repo + AI Knowledge
    Use project context plus general programming knowledge.

Generate Standalone
    Generate independent code when no existing project context is needed.
```

### Repository Specialist

For selected folders, codebases, and project directories.

Supported actions:

- explain project structure
- identify entry points
- trace authentication, API, database, frontend, or build flows
- summarize modules
- detect missing files or broken architecture
- generate documentation
- suggest improvements

The Repository Specialist should build a repo map before answering:

```text
folder tree
    |
    v
important files
    |
    v
modules/functions/classes
    |
    v
relationships and flows
    |
    v
retrieved evidence for the question
```

### Project Builder Specialist

For creating a new project or extending an existing one.

Supported actions:

- ask for missing requirements
- generate architecture
- create project structure
- write files step by step
- run checks/tests
- debug failures
- explain what changed

Project Builder rules:

```text
New empty project
    RAG is optional at the start.
    The model can create an architecture from requirements.

Existing project
    RAG/context is required.
    The model must follow the existing structure, imports, style, and dependencies.
```

## Context Modes

Local Pilot should expose a clear mode switch because users sometimes want strict grounded answers and sometimes want broader help.

For documents:

```text
[Strict Sources] [Smart Assist]
```

For code:

```text
[Repo Only] [Repo + AI Knowledge] [Generate Standalone]
```

For folders:

```text
[Explain] [Debug] [Improve] [Generate Docs]
```

For project building:

```text
[Plan First] [Create Files] [Run/Test]
```

Default mode should be strict and local-first:

```text
Documents -> Strict Sources
Code -> Repo Only
Folders -> Explain from selected folder
```

This keeps Local Pilot trustworthy. The user can switch to Smart Assist when they want broader reasoning.

## When RAG Is Needed

RAG is required when the answer must depend on selected files, folders, or existing project context.

| Task | RAG Needed? | Reason |
| --- | --- | --- |
| Answer questions from a document | Yes | The answer must be grounded in the selected document. |
| Summarize selected file/folder | Yes | The selected content is the source. |
| Explain existing code | Yes | The model needs the actual code. |
| Debug existing code | Yes | Bugs depend on implementation details. |
| Modify an existing project | Yes | Generated code must fit current files, imports, style, and dependencies. |
| Explain a repository architecture | Yes | Architecture comes from the folder and files. |
| Generate a standalone script | Optional | General model knowledge may be enough. |
| Create a brand-new empty project | Optional at first | The model can start from requirements, then store the generated project as context. |
| Extend an existing project | Yes | Existing context is required to avoid breaking the project. |

## Internal RAG Pipeline

The RAG pipeline is the brain of Local Pilot. Context building, extraction, indexing, memory, retrieval, and correction all belong inside this pipeline.

```text
RAG Pipeline
    |
    v
User Action Layer
    |
    v
OS Context Layer
    |
    v
Context Builder
    |
    v
Content Router
    |
    v
Extraction Pipeline
    |
    v
Chunking + Indexing
    |
    v
Per-File / Per-Folder Memory
    |
    v
Hybrid Retrieval
    |
    v
Agentic Corrective RAG
    |
    v
Grounded Answer Package
```

### Layer Responsibilities

| Layer | Responsibility |
| --- | --- |
| User Action Layer | Receives the selected file, files, or folder from Explorer. |
| OS Context Layer | Normalizes paths and captures platform/context-menu metadata. |
| Context Builder | Builds the workspace context: selected item, parent folder, neighboring files, and previous memory. |
| Content Router | Chooses the correct processor for PDFs, Office files, text, code, folders, and future images. |
| Extraction Pipeline | Converts supported files into clean text plus metadata. |
| Chunking + Indexing | Splits extracted content into searchable source chunks and stores them locally. |
| Memory | Keeps per-file, per-folder, and workspace chat history. |
| Hybrid Retrieval | Finds the best evidence using lexical search now, with embeddings/reranking planned. |
| Agentic Corrective RAG | Generates an answer, checks grounding, and retries or says it cannot find enough evidence. |
| Answer Package | Returns answer text, source references, confidence signals, and suggested actions. |

## Pipeline Diagram

```mermaid
flowchart TD
    A[Windows Explorer Selection] --> B[Local Pilot Context Menu]
    B --> C[Desktop Popup Chat UI]
    C --> D[Selection Gateway]
    D --> T[Type + Task Detector]
    T --> S[Specialist Router]

    S --> SD[Document Specialist]
    S --> SC[Code Specialist]
    S --> SR[Repository Specialist]
    S --> SP[Project Builder Specialist]

    SD --> E[RAG Pipeline]
    SC --> E
    SR --> E
    SP --> E

    subgraph E[RAG Pipeline]
        E1[User Action Layer]
        E2[OS Context Layer]
        E3[Context Builder]
        E4[Content Router]
        E5[Extraction Pipeline]
        E6[Chunking + Indexing]
        E7[Per-File / Per-Folder Memory]
        E8[Hybrid Retrieval]
        E9[Agentic Corrective RAG]
        E10[Grounded Answer Package]

        E1 --> E2 --> E3 --> E4 --> E5 --> E6 --> E7 --> E8 --> E9 --> E10
    end

    E10 --> F[Model Router]
    F --> G1[Ollama Local]
    F --> G2[OpenAI]
    F --> G3[Claude]
    F --> G4[Gemini]
    F --> G5[Groq]
    G1 --> H[Answer UI]
    G2 --> H
    G3 --> H
    G4 --> H
    G5 --> H
```

## Memory Design

Local Pilot stores memory locally in SQLite:

```text
data/local_pilot.db
```

The memory model is:

```text
File memory
    - path
    - content hash
    - extracted chunks
    - metadata
    - chat history for that file

Folder memory
    - folder path
    - folder structure
    - indexed supported files
    - workspace chat history

Workspace memory
    - one file
    - multiple selected files
    - one folder
    - future mixed selections
```

This means each selected item can have its own stored knowledge, while multi-file and folder workflows can answer using the whole workspace.

## Model Routing

Local Pilot is local-first.

```text
Default: Ollama
Optional: OpenAI / Claude / Gemini / Groq
Mode: auto with cloud fallback only if enabled
```

Provider flow:

```text
Question + retrieved chunks
    |
    v
Model Router
    |
    +--> Ollama if local mode is selected
    +--> Cloud provider if selected and API key exists
    +--> Cloud fallback only if the user enabled fallback
```

Privacy rule:

```text
Local mode keeps selected context on this computer.
Cloud mode can send selected retrieved chunks to the chosen API provider.
```

## Codebase Direction

The current app works, but the long-term codebase should be organized around a clean pipeline module:

```text
backend/
  local_pilot_popup.py
  app/
    pipeline/
      state.py
      orchestrator.py
      user_action.py
      os_context.py
      context_builder.py
      content_router.py
      extraction.py
      indexing.py
      retrieval.py
      agent.py
      response.py
    extractors.py
    rag_engine.py
    rag_store.py
    settings_store.py
    setup_check.py
    llm/
      router.py
      ollama_client.py
      openai_client.py
      anthropic_client.py
      gemini_client.py
      groq_client.py
```

The current MVP can keep working while logic is gradually moved into `backend/app/pipeline/`.

## Current Project Structure

```text
local-pilot/
  backend/
    app/
      main.py
      rag_engine.py
      setup_check.py
      context_collector.py
      extractors.py
      folder_scanner.py
      rag_store.py
      settings_store.py
      schemas.py
      llm/
    local_pilot_popup.py
    local_pilot_cli.py
  desktop/
    registry/
      install-local-pilot-dev.ps1
      check-local-pilot-dev.ps1
      add-local-pilot-dev.reg
      remove-local-pilot.reg
  data/
    local_pilot.db
  docs/
  requirements.txt
```

## Run The Desktop MVP

Install dependencies:

```bash
pip install -r requirements.txt
```

Install the development context-menu entry:

```powershell
powershell.exe -ExecutionPolicy Bypass -File desktop\registry\install-local-pilot-dev.ps1
```

Check setup:

```powershell
powershell.exe -ExecutionPolicy Bypass -File desktop\registry\check-local-pilot-dev.ps1
```

Then:

1. Right click a file or folder.
2. On Windows 11, choose `Show more options` if needed.
3. Click `Local Pilot`.
4. Ask questions in the popup chat window.

## Ollama Setup

Local Pilot uses Ollama by default.

Small fast model:

```bash
ollama pull gemma3:1b
```

Stronger model:

```bash
ollama pull qwen3:8b
```

Check installed models:

```bash
ollama list
```

If `ollama` is not recognized, open the Ollama desktop app once or restart the terminal.

## API And CLI

Run the API:

```bash
uvicorn backend.app.main:app --reload
```

Health check:

```text
http://127.0.0.1:8000/health
```

CLI test:

```bash
python backend/local_pilot_cli.py "C:\Path\To\FileOrFolder"
```

## Roadmap

### Stage 1: Working Contextual File Chat

- Windows right-click integration
- Local popup chat UI
- File/folder extraction
- Local memory
- Ollama/local model answering
- Optional cloud providers

### Stage 2: Strong RAG Engine

- Clean `pipeline/` module
- Better retrieval
- Embeddings
- BM25 + vector hybrid search
- Reranking
- Better citations with page/slide/file references
- Multi-file selection

### Stage 3: Codebase Intelligence

- Code-aware chunking
- Repository map
- Dependency/function/class understanding
- Architecture explanation
- Debugging assistance
- Safe code-change suggestions

### Stage 4: Agentic Workflows

- Corrective RAG validation loop
- Action planning
- File edits with approval
- Test runner integration
- Documentation generation

### Stage 5: Distribution

- Installer
- First-run setup wizard
- Ollama detection and guidance
- Context-menu install/uninstall
- Signed release builds

## Development Principle

Local Pilot should stay:

- local-first
- source-grounded
- file/folder aware
- fast from Explorer
- honest when the selected context does not contain the answer

The goal is not just another chatbot. The goal is an AI assistant that understands the thing the user already selected.
