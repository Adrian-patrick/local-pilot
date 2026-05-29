"""AppWindow — main application window orchestrator.

Replaces App.tsx. Manages the application state machine and coordinates
all child widgets: Header, FileInfoCard, AskSection, EmptyState, ErrorState.
"""

from __future__ import annotations

import enum
import logging
import sys
import threading
import time
import os
import dotenv

# Load environment variables
dotenv.load_dotenv()

import customtkinter as ctk

from app.file_service import FileMetadata, get_file_metadata, read_file_content
from app.gui import theme
from app.gui.ask_section import AskSection
from app.gui.empty_state import EmptyState
from app.gui.error_state import ErrorState
from app.gui.file_info_card import FileInfoCard
from app.gui.header import Header
from app.gui.loading_state import LoadingState
from app.prompt_builder import build_prompt
from app import ollama_service
from app import groq_service
from app.agent.orchestrator import AgentOrchestrator

log = logging.getLogger(__name__)


class AppState(enum.Enum):
    LOADING = "loading"
    FILE_INFO = "file_info"
    EMPTY = "empty"
    ERROR = "error"


class AppWindow(ctk.CTk):
    """Main Local Pilot application window."""

    def __init__(self, file_path: str | None = None):
        super().__init__()

        # ── Window configuration ─────────────────────────────────────────
        self.title("Local Pilot")
        self.geometry(f"{theme.WINDOW_WIDTH}x{theme.WINDOW_HEIGHT}")
        self.minsize(600, 500)
        self.configure(fg_color=theme.BG_PRIMARY)

        # Set app appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # ── Internal state ───────────────────────────────────────────────
        self._file_path = file_path
        self._metadata: FileMetadata | None = None
        self._file_content: str = ""
        self._state = AppState.LOADING if file_path else AppState.EMPTY
        self._active_model: str | None = None
        self._ollama_connected = False
        self._generation_thread: threading.Thread | None = None

        # ── Daemon lifecycle ─────────────────────────────────────────────
        self.protocol("WM_DELETE_WINDOW", self._hide_window)

        # ── Build layout ─────────────────────────────────────────────────
        self._build_layout()

        # ── Start background tasks ───────────────────────────────────────
        if file_path:
            threading.Thread(target=self._load_file, daemon=True).start()

        # Always try to connect to Ollama in background
        threading.Thread(target=self._init_ollama, daemon=True).start()

    def _build_layout(self):
        """Construct the main layout container."""
        # Main scrollable container
        self._container = ctk.CTkFrame(self, fg_color="transparent")
        self._container.pack(fill="both", expand=True, padx=theme.PAD_LG, pady=theme.PAD_LG)

        # ── Header (always visible) ──────────────────────────────────────
        self._header = Header(self._container)
        self._header.pack(fill="x", pady=(0, theme.PAD_MD))

        # ── Content area (swapped based on state) ────────────────────────
        self._content_frame = ctk.CTkFrame(self._container, fg_color="transparent")
        self._content_frame.pack(fill="both", expand=True)

        self._show_state(self._state)

    def _clear_content(self):
        """Remove all widgets from the content area."""
        for widget in self._content_frame.winfo_children():
            widget.destroy()

    def _hide_window(self):
        """Hide the window instead of destroying it (Daemon mode)."""
        self.withdraw()

    def load_new_context(self, file_path: str | None):
        """Called by the daemon listener to show the window with new context."""
        self.deiconify()
        self.lift()
        self.focus_force()

        if file_path == self._file_path:
            return  # Already loaded

        self._file_path = file_path
        self._metadata = None
        self._file_content = ""
        
        if file_path:
            self._show_state(AppState.LOADING)
            threading.Thread(target=self._load_file, daemon=True).start()
        else:
            self._show_state(AppState.EMPTY)

    def _show_state(self, state: AppState, error_msg: str = ""):
        """Switch the content area to a given state."""
        self._state = state
        self._clear_content()

        if state == AppState.LOADING:
            loading = LoadingState(self._content_frame)
            loading.pack(fill="x")

        elif state == AppState.EMPTY:
            empty = EmptyState(self._content_frame)
            empty.pack(fill="x")
            # Still show the ask section even without a file
            self._add_ask_section()

        elif state == AppState.FILE_INFO:
            if self._metadata:
                card = FileInfoCard(self._content_frame, self._metadata)
                card.pack(fill="x", pady=(0, theme.PAD_SM))
            self._add_ask_section()

        elif state == AppState.ERROR:
            err = ErrorState(
                self._content_frame,
                error=error_msg,
                file_path=self._file_path,
            )
            err.pack(fill="x")
            # Still show ask section for general questions
            self._add_ask_section()

    def _add_ask_section(self):
        """Add the chat interface at the bottom."""
        models = []
        selected = self._active_model

        if self._ollama_connected:
            try:
                models = ollama_service.get_ollama_models()
            except (ConnectionError, RuntimeError):
                pass

        self._ask_section = AskSection(
            self._content_frame,
            models=models,
            selected_model=selected,
            on_submit=self._handle_ask,
        )
        self._ask_section.pack(fill="both", expand=True, pady=(theme.PAD_SM, 0))

        if not self._ollama_connected:
            self._ask_section.set_status("⏳ Connecting to Ollama...")

    # ── Background tasks ─────────────────────────────────────────────────

    def _load_file(self):
        """Load file metadata and content in a background thread."""
        try:
            self._metadata = get_file_metadata(self._file_path)
            self._file_content = read_file_content(self._file_path)
            self.after(0, lambda: self._show_state(AppState.FILE_INFO))
        except FileNotFoundError as exc:
            log.error("File not found: %s", exc)
            self.after(0, lambda: self._show_state(AppState.ERROR, str(exc)))
        except PermissionError as exc:
            log.error("Permission denied: %s", exc)
            self.after(0, lambda: self._show_state(AppState.ERROR, str(exc)))
        except Exception as exc:
            log.error("Unexpected error loading file: %s", exc)
            self.after(0, lambda: self._show_state(AppState.ERROR, str(exc)))

    def _init_ollama(self):
        """Initialize Ollama connection and ensure a model is available."""
        # Try to ensure Ollama is running
        if not ollama_service.ensure_ollama_running():
            self.after(0, self._on_ollama_offline)
            return

        self._ollama_connected = True

        # Auto-select and pull the best model
        def progress_cb(status: str, percent: float):
            pct_str = f" ({percent:.0%})" if percent > 0 else ""
            self.after(
                0,
                lambda s=status, p=pct_str: self._update_ollama_status(f"📥 {s}{p}"),
            )

        model = ollama_service.auto_select_and_ensure_model(progress_callback=progress_cb)

        if model:
            self._active_model = model
            self.after(0, self._on_ollama_ready)
        else:
            self.after(0, self._on_ollama_no_model)

    def _on_ollama_ready(self):
        """Called on the main thread when Ollama is connected and model ready."""
        self._header.set_status("Connected", theme.STATUS_CONNECTED)
        if hasattr(self, "_ask_section"):
            try:
                models = ollama_service.get_ollama_models()
            except (ConnectionError, RuntimeError):
                models = [self._active_model] if self._active_model else []

            # Check for Groq API Key and add Cloud models
            groq_key = os.getenv("groq_api_key") or os.getenv("GROQ_API_KEY")
            if groq_key:
                models.extend([
                    "groq:llama-3.3-70b-versatile",
                    "groq:llama-3.1-8b-instant",
                    "groq:qwen/qwen3-32b",
                    "groq:allam-2-7b"
                ])

            self._ask_section.update_models(models, self._active_model)
            self._ask_section.set_status(f"✅ Ready — using {self._active_model}")

    def _on_ollama_offline(self):
        """Called when Ollama is not available."""
        self._header.set_status("Offline", theme.STATUS_OFFLINE_TEXT)
        if hasattr(self, "_ask_section"):
            self._ask_section.set_status(
                "⚠ Ollama is not running. Please install and start Ollama."
            )

    def _on_ollama_no_model(self):
        """Called when Ollama is running but no model could be pulled."""
        self._header.set_status("No Model", theme.STATUS_WARNING_TEXT)
        if hasattr(self, "_ask_section"):
            self._ask_section.set_status(
                "⚠ No model available. Check your internet connection."
            )

    def _update_ollama_status(self, text: str):
        """Update the ask section status text."""
        if hasattr(self, "_ask_section"):
            self._ask_section.set_status(text)

    # ── Chat handling ─────────────────────────────────────────────────────

    def _handle_ask(self, model: str, query: str):
        """Handle a user question submission."""
        if self._generation_thread and self._generation_thread.is_alive():
            return  # Already generating

        # Build the prompt
        prompt = build_prompt(self._metadata, self._file_content, query)

        # Update UI
        self._ask_section.append_user_message(query)
        self._ask_section.set_generating(True)
        self._ask_section.set_status(f"🔄 Generating with {model}...")

        # Run inference in background thread
        self._generation_thread = threading.Thread(
            target=self._run_inference,
            args=(model, prompt),
            daemon=True,
        )
        self._generation_thread.start()

    def _run_inference(self, model: str, prompt: str):
        """Run streaming inference in a background thread."""
        try:
            self._current_rate_limits = None
            
            # Use multi-agent orchestrator if Agent Mode is toggled
            if hasattr(self, "_ask_section") and self._ask_section.is_agent_mode():
                # For Agent Mode, we only use the query, not the full built prompt which contains file context
                # because the agent can read files itself.
                query = prompt.split("Question:")[-1].strip() if "Question:" in prompt else prompt
                base_dir = os.path.dirname(self._file_path) if self._file_path else os.getcwd()
                
                orchestrator = AgentOrchestrator(model=model, base_dir=base_dir)
                def handle_rate_limit(limits):
                    self._current_rate_limits = limits
                    
                for token in orchestrator.run(query, on_rate_limit=handle_rate_limit):
                    self._ask_section.append_response(token)
            else:
                # Standard single-shot mode
                if model.startswith("groq:"):
                    real_model = model.split("groq:")[1]
                    api_key = os.getenv("groq_api_key") or os.getenv("GROQ_API_KEY")
                    if not api_key:
                        raise ValueError("Groq API key is missing from .env file.")
                    
                    def handle_rate_limit(limits):
                        self._current_rate_limits = limits

                    for token in groq_service.ask_groq_stream(real_model, prompt, api_key, on_rate_limit=handle_rate_limit):
                        self._ask_section.append_response(token)
                else:
                    for token in ollama_service.ask_ollama_stream(model, prompt):
                        self._ask_section.append_response(token)

            self.after(0, self._on_generation_complete)

        except TimeoutError as exc:
            log.error("API Timeout: %s", exc)
            self.after(0, lambda: self._on_generation_error(str(exc)))
        except ConnectionError as exc:
            log.error("Ollama connection error: %s", exc)
            self.after(
                0,
                lambda: self._on_generation_error(
                    "Connection to Ollama lost. Is it still running?"
                ),
            )
        except RuntimeError as exc:
            log.error("Ollama error: %s", exc)
            self.after(0, lambda: self._on_generation_error(str(exc)))
        except Exception as exc:
            log.error("Unexpected inference error: %s", exc)
            self.after(0, lambda: self._on_generation_error(str(exc)))

    def _on_generation_complete(self):
        """Called when generation finishes successfully."""
        self._ask_section.set_generating(False)
        self._ask_section.set_status(f"✅ Response complete — {self._active_model}")
        
        if getattr(self, "_current_rate_limits", None):
            self._ask_section.update_rate_limit(self._current_rate_limits)

    def _on_generation_error(self, error: str):
        """Called when generation encounters an error."""
        self._ask_section.set_generating(False)
        self._ask_section.set_status(f"❌ Error: {error}")
        self._ask_section.append_response(f"\n\n[Error: {error}]")
