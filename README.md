# Local Pilot

Local Pilot is a completely native, intelligent OS companion for Windows. It embeds an AI layer directly into your Windows context menu, allowing you to seamlessly analyze code, summarize documents, and execute complex autonomous tasks on any file in your system.

## 🚀 Key Features

*   **Contextual OS Integration**: Right-click *any* file on your computer and select "Ask Local Pilot" to instantly spin up the agent with that file's context loaded.
*   **Multi-Agent Orchestrator**: Toggle "Agent Mode" to transform Local Pilot from a Q&A chatbot into an autonomous ReAct (Reason + Act) agent. It can read folders, read files, and write code/docs autonomously.
*   **Dual Inference Engine**:
    *   **Cloud Mode**: Supports blazing-fast API inference via the Groq Cloud API (Llama 3, Mixtral).
    *   **Local Mode**: Native support for Ollama allowing 100% offline, private inference using local LLMs.
*   **Live Token Tracking**: Features an interactive UI with live token progression bars and auto-cooldown handling for strict API limits.

## 🛠️ Easy Installation

We have built automated installer scripts to make setup incredibly easy on Windows.

1.  **Configure Environment**:
    *   Rename `.env.example` to `.env`.
    *   Open it and add your [Groq API Key](https://console.groq.com/keys) if you want to use the cloud agent. (Local Ollama does not require an API key).
2.  **Run Setup**:
    *   Double-click `setup.bat`.
    *   This will automatically install Python dependencies, create a secure virtual environment, and register the necessary registry keys for the Windows Right-Click context menu.

## 💻 Usage

*   **Quick Access**: Right-click any file in Windows Explorer and click `Ask Local Pilot`.
*   **Standalone Mode**: Double-click `run.bat` to launch the application directly.
*   **Agent Mode**: Once the app is open, toggle "Agent Mode" and give it a mission (e.g., *"Analyze the `scripts` folder and write a setup guide into `docs.md`"*).

## 🛡️ Architecture
Built entirely in Python using `customtkinter` for a lightweight, beautiful, and native Windows GUI. It runs an invisible background daemon to ensure instant startup speeds without the overhead of heavy web frameworks like Electron.
