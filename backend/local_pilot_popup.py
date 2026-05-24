import argparse
from pathlib import Path
import queue
import sys
import threading
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.agent import answer_question
from app.config import get_settings
from app.context_collector import collect_context
from app.llm.base import LLMError
from app.llm.model_discovery import list_models, test_provider
from app.setup_check import get_setup_status
from app.settings_store import read_env_values, save_env_values


class LocalPilotPopup:
    def __init__(self, selected_path: str):
        self.selected_path = selected_path
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()
        self.context_summary = "Loading selected item..."
        self.settings = get_settings()

        self.root = tk.Tk()
        self.root.title("Local Pilot")
        self.root.geometry("860x660")
        self.root.minsize(680, 500)
        self.root.configure(bg="#f5f7fb")

        self.colors = {
            "bg": "#f5f7fb",
            "panel": "#ffffff",
            "border": "#d9e0ea",
            "text": "#172033",
            "muted": "#64748b",
            "brand": "#2563eb",
            "brand_dark": "#1d4ed8",
            "assistant": "#ffffff",
            "user": "#e8f0ff",
            "input": "#ffffff",
        }

        self._configure_style()
        self._build_ui()
        self._load_context_preview()
        self.root.after(100, self._drain_messages)

    def run(self) -> None:
        self.root.mainloop()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Accent.TButton",
            background=self.colors["brand"],
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
            padding=(18, 12),
        )
        style.map(
            "Accent.TButton",
            background=[("active", self.colors["brand_dark"]), ("disabled", "#94a3b8")],
            foreground=[("disabled", "#eef2ff")],
        )
        style.configure(
            "Ghost.TButton",
            background=self.colors["bg"],
            foreground=self.colors["brand"],
            borderwidth=1,
            focusthickness=0,
            font=("Segoe UI", 9, "bold"),
            padding=(10, 8),
        )

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        shell = tk.Frame(self.root, bg=self.colors["bg"], padx=22, pady=20)
        shell.grid(row=0, column=0, rowspan=4, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        header = tk.Frame(shell, bg=self.colors["bg"])
        header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=0)

        mark = tk.Canvas(header, width=42, height=42, bg=self.colors["bg"], highlightthickness=0)
        mark.grid(row=0, column=0, rowspan=2, sticky="nw", padx=(0, 12))
        mark.create_oval(3, 3, 39, 39, fill=self.colors["brand"], outline="")
        mark.create_text(21, 21, text="LP", fill="#ffffff", font=("Segoe UI", 10, "bold"))

        tk.Label(
            header,
            text="Local Pilot",
            font=("Segoe UI", 20, "bold"),
            fg=self.colors["text"],
            bg=self.colors["bg"],
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")

        tk.Label(
            header,
            text="Ask questions about the file or folder you selected.",
            font=("Segoe UI", 10),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", pady=(2, 0))

        provider_area = tk.Frame(header, bg=self.colors["bg"])
        provider_area.grid(row=0, column=2, rowspan=2, sticky="ne")

        self.provider_badge = tk.Label(
            provider_area,
            text=self._provider_badge_text(),
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["brand"],
            bg="#eef4ff",
            padx=10,
            pady=6,
        )
        self.provider_badge.grid(row=0, column=0, sticky="e", padx=(0, 8))

        ttk.Button(
            provider_area,
            text="Settings",
            style="Ghost.TButton",
            command=self._open_settings,
        ).grid(row=0, column=1, sticky="e")

        ttk.Button(
            provider_area,
            text="Setup",
            style="Ghost.TButton",
            command=self._open_setup,
        ).grid(row=0, column=2, sticky="e", padx=(8, 0))

        context_card = tk.Frame(
            shell,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        context_card.grid(row=1, column=0, sticky="new", pady=(0, 12))
        context_card.columnconfigure(0, weight=1)

        self.context_title = tk.Label(
            context_card,
            text="Selected item",
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["brand"],
            bg=self.colors["panel"],
            anchor="w",
        )
        self.context_title.grid(row=0, column=0, sticky="ew")

        self.path_label = tk.Label(
            context_card,
            text=self.selected_path,
            font=("Segoe UI", 9),
            fg=self.colors["text"],
            bg=self.colors["panel"],
            anchor="w",
            wraplength=760,
            justify="left",
        )
        self.path_label.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.summary_label = tk.Label(
            context_card,
            text=self.context_summary,
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            anchor="w",
            wraplength=760,
            justify="left",
        )
        self.summary_label.grid(row=2, column=0, sticky="ew", pady=(4, 0))

        actions = tk.Frame(shell, bg=self.colors["bg"])
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        actions.columnconfigure(4, weight=1)

        quick_actions = [
            (
                "Overview",
                "Give a concise overview of the selected file in 5 bullets. Use only information from the file.",
            ),
            (
                "Key Points",
                "Extract the key points from the selected file. Group related points when helpful. Do not add outside information.",
            ),
            (
                "Find Items",
                "List the important named items in this file, such as projects, sections, entities, tasks, or records. Include short descriptions only when the file provides them.",
            ),
            (
                "Actions",
                "Extract action items, decisions, requirements, risks, or next steps from this file. If none are present, say so.",
            ),
        ]
        for index, (label, prompt) in enumerate(quick_actions):
            tk.Button(
                actions,
                text=label,
                font=("Segoe UI", 9, "bold"),
                fg=self.colors["brand"],
                bg="#eef4ff",
                activebackground="#dbeafe",
                activeforeground=self.colors["brand_dark"],
                relief=tk.FLAT,
                padx=12,
                pady=7,
                command=lambda value=prompt: self._ask_prompt(value),
            ).grid(row=0, column=index, sticky="w", padx=(0, 8))

        chat_panel = tk.Frame(
            shell,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
        )
        chat_panel.grid(row=3, column=0, sticky="nsew", pady=(0, 12))
        chat_panel.columnconfigure(0, weight=1)
        chat_panel.rowconfigure(0, weight=1)

        self.chat_canvas = tk.Canvas(chat_panel, bg=self.colors["panel"], highlightthickness=0)
        self.chat_canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(chat_panel, orient="vertical", command=self.chat_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.chat_canvas.configure(yscrollcommand=scrollbar.set)

        self.messages_frame = tk.Frame(self.chat_canvas, bg=self.colors["panel"], padx=14, pady=14)
        self.messages_window = self.chat_canvas.create_window(
            (0, 0), window=self.messages_frame, anchor="nw"
        )
        self.messages_frame.bind("<Configure>", self._sync_scroll_region)
        self.chat_canvas.bind("<Configure>", self._sync_message_width)
        self.chat_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        input_card = tk.Frame(
            shell,
            bg=self.colors["input"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        input_card.grid(row=4, column=0, sticky="ew")
        input_card.columnconfigure(0, weight=1)

        self.question = tk.Text(
            input_card,
            height=3,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            fg=self.colors["text"],
            bg=self.colors["input"],
            bd=0,
            padx=4,
            pady=4,
            insertbackground=self.colors["brand"],
        )
        self.question.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.question.bind("<Control-Return>", self._ask)

        self.ask_button = ttk.Button(
            input_card,
            text="Ask",
            style="Accent.TButton",
            command=self._ask,
        )
        self.ask_button.grid(row=0, column=1, sticky="ns")

        footer = tk.Frame(shell, bg=self.colors["bg"])
        footer.grid(row=5, column=0, sticky="ew", pady=(8, 0))
        footer.columnconfigure(0, weight=1)

        self.status = tk.Label(
            footer,
            text="Ctrl+Enter to ask",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
        )
        self.status.grid(row=0, column=0, sticky="ew")

        self.privacy_label = tk.Label(
            footer,
            text=self._privacy_text(),
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="e",
        )
        self.privacy_label.grid(row=0, column=1, sticky="e")

    def _load_context_preview(self) -> None:
        try:
            context = collect_context(self.selected_path)
            self.summary_label.configure(text=context["summary"])
            self._append(
                "Local Pilot",
                f"Loaded {context['kind']}: {context['name']}\n\n"
                "Ask me anything about it.",
            )
        except Exception as exc:
            self.summary_label.configure(text="Could not load selected item.")
            self._append("Local Pilot", f"Could not load selected item:\n{exc}")

    def _provider_badge_text(self) -> str:
        provider = self.settings.model_provider
        model = {
            "ollama": self.settings.ollama_model,
            "openai": self.settings.openai_model,
            "anthropic": self.settings.anthropic_model,
            "gemini": self.settings.gemini_model,
            "groq": self.settings.groq_model,
            "auto": f"auto -> {self.settings.ollama_model}",
        }.get(provider, provider)
        return f"{provider.title()} | {model}"

    def _privacy_text(self) -> str:
        if self.settings.model_provider == "ollama":
            return "Local mode: selected context stays on this computer"
        if self.settings.model_provider == "auto" and not self.settings.allow_cloud_fallback:
            return "Auto mode: local first, cloud fallback off"
        return "Cloud mode: selected chunks may be sent to the provider"

    def _refresh_settings_view(self) -> None:
        self.settings = get_settings()
        self.provider_badge.configure(text=self._provider_badge_text())
        self.privacy_label.configure(text=self._privacy_text())

    def _open_setup(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Local Pilot Setup")
        dialog.geometry("760x560")
        dialog.minsize(680, 460)
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        header = tk.Frame(dialog, bg=self.colors["bg"], padx=22, pady=18)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = tk.Label(
            header,
            text="Setup Status",
            font=("Segoe UI", 16, "bold"),
            fg=self.colors["text"],
            bg=self.colors["bg"],
            anchor="w",
        )
        title.grid(row=0, column=0, sticky="ew")

        subtitle = tk.Label(
            header,
            text="Check whether Local Pilot is ready for right-click AI workflows.",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
        )
        subtitle.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        checks_panel = tk.Frame(
            dialog,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=14,
            pady=14,
        )
        checks_panel.grid(row=1, column=0, sticky="nsew", padx=22)
        checks_panel.columnconfigure(0, weight=1)

        footer = tk.Frame(dialog, bg=self.colors["bg"], padx=22, pady=14)
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        status = tk.Label(
            footer,
            text="",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
        )
        status.grid(row=0, column=0, sticky="ew")

        def clear_checks() -> None:
            for child in checks_panel.winfo_children():
                child.destroy()

        def render() -> None:
            clear_checks()
            status.configure(text="Running setup checks...")
            dialog.update_idletasks()
            setup_status = get_setup_status()
            title.configure(text="Setup Status: Ready" if setup_status.ready else "Setup Status: Needs Attention")
            status.configure(
                text="Local Pilot is ready." if setup_status.ready else "Fix the items marked Needs attention."
            )

            for row_index, check in enumerate(setup_status.checks):
                row = tk.Frame(checks_panel, bg=self.colors["panel"])
                row.grid(row=row_index, column=0, sticky="ew", pady=(0, 12))
                row.columnconfigure(1, weight=1)

                badge_text = "OK" if check.ok else "Needs attention"
                badge_bg = "#dcfce7" if check.ok else "#fee2e2"
                badge_fg = "#166534" if check.ok else "#991b1b"

                tk.Label(
                    row,
                    text=badge_text,
                    font=("Segoe UI", 8, "bold"),
                    fg=badge_fg,
                    bg=badge_bg,
                    padx=8,
                    pady=4,
                ).grid(row=0, column=0, sticky="nw", padx=(0, 12))

                text_block = tk.Frame(row, bg=self.colors["panel"])
                text_block.grid(row=0, column=1, sticky="ew")
                text_block.columnconfigure(0, weight=1)

                tk.Label(
                    text_block,
                    text=check.name,
                    font=("Segoe UI", 10, "bold"),
                    fg=self.colors["text"],
                    bg=self.colors["panel"],
                    anchor="w",
                ).grid(row=0, column=0, sticky="ew")
                tk.Label(
                    text_block,
                    text=check.detail,
                    font=("Segoe UI", 9),
                    fg=self.colors["muted"],
                    bg=self.colors["panel"],
                    anchor="w",
                    justify="left",
                    wraplength=590,
                ).grid(row=1, column=0, sticky="ew", pady=(2, 0))
                if not check.ok:
                    tk.Label(
                        text_block,
                        text=f"Action: {check.action}",
                        font=("Segoe UI", 9, "bold"),
                        fg=self.colors["brand"],
                        bg=self.colors["panel"],
                        anchor="w",
                        justify="left",
                        wraplength=590,
                    ).grid(row=2, column=0, sticky="ew", pady=(4, 0))

        buttons = tk.Frame(footer, bg=self.colors["bg"])
        buttons.grid(row=0, column=1, sticky="e")
        ttk.Button(buttons, text="Refresh", command=render).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Settings", command=self._open_settings).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(buttons, text="Close", command=dialog.destroy).grid(row=0, column=2)

        render()

    def _open_settings(self) -> None:
        values = read_env_values()
        dialog = tk.Toplevel(self.root)
        dialog.title("Local Pilot Settings")
        dialog.geometry("940x620")
        dialog.minsize(860, 560)
        dialog.configure(bg=self.colors["bg"])
        dialog.transient(self.root)
        dialog.grab_set()

        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        header = tk.Frame(dialog, bg=self.colors["bg"], padx=22, pady=20)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        body_shell = tk.Frame(dialog, bg=self.colors["bg"], padx=22)
        body_shell.grid(row=1, column=0, sticky="nsew")
        body_shell.columnconfigure(0, weight=1)
        body_shell.rowconfigure(0, weight=1)

        settings_canvas = tk.Canvas(body_shell, bg=self.colors["bg"], highlightthickness=0)
        settings_canvas.grid(row=0, column=0, sticky="nsew")

        scrollbar = ttk.Scrollbar(body_shell, orient="vertical", command=settings_canvas.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        settings_canvas.configure(yscrollcommand=scrollbar.set)

        body = tk.Frame(settings_canvas, bg=self.colors["bg"])
        body_window = settings_canvas.create_window((0, 0), window=body, anchor="nw")
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        def sync_scroll_region(event: object | None = None) -> None:
            settings_canvas.configure(scrollregion=settings_canvas.bbox("all"))

        def sync_body_width(event: tk.Event) -> None:
            settings_canvas.itemconfigure(body_window, width=event.width)

        def on_settings_mousewheel(event: tk.Event) -> None:
            settings_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        body.bind("<Configure>", sync_scroll_region)
        settings_canvas.bind("<Configure>", sync_body_width)
        settings_canvas.bind("<MouseWheel>", on_settings_mousewheel)
        body.bind("<MouseWheel>", on_settings_mousewheel)

        tk.Label(
            header,
            text="AI Provider Settings",
            font=("Segoe UI", 16, "bold"),
            fg=self.colors["text"],
            bg=self.colors["bg"],
            anchor="w",
        ).grid(row=0, column=0, sticky="ew")

        tk.Label(
            header,
            text="Local mode is private. Cloud mode can send selected file chunks to the API provider. Leave key fields blank to keep saved keys.",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
            wraplength=700,
            justify="left",
        ).grid(row=1, column=0, sticky="ew", pady=(4, 14))

        form = tk.Frame(
            body,
            bg=self.colors["panel"],
            highlightbackground=self.colors["border"],
            highlightthickness=1,
            padx=16,
            pady=14,
        )
        form.grid(row=2, column=0, sticky="nsew")
        form.columnconfigure(0, weight=1, uniform="settings")
        form.columnconfigure(1, weight=1, uniform="settings")

        entries: dict[str, tk.Entry] = {}
        model_entries: dict[str, ttk.Combobox] = {}
        secret_keys = {"OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"}
        provider_var = tk.StringVar(value=values.get("LOCAL_PILOT_MODEL_PROVIDER", self.settings.model_provider))
        fallback_var = tk.BooleanVar(
            value=values.get(
                "LOCAL_PILOT_ALLOW_CLOUD_FALLBACK",
                str(self.settings.allow_cloud_fallback).lower(),
            ).lower()
            in {"1", "true", "yes", "on"}
        )

        top = tk.Frame(form, bg=self.colors["panel"])
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)

        self._settings_label(top, "Provider", 0)
        provider_box = ttk.Combobox(
            top,
            textvariable=provider_var,
            values=("ollama", "auto", "openai", "anthropic", "gemini", "groq"),
            state="readonly",
            font=("Segoe UI", 10),
        )
        provider_box.grid(row=0, column=1, sticky="ew", padx=(0, 18))

        fallback = tk.Checkbutton(
            top,
            text="Allow cloud fallback in auto mode",
            variable=fallback_var,
            fg=self.colors["text"],
            bg=self.colors["panel"],
            activebackground=self.colors["panel"],
            font=("Segoe UI", 9),
            anchor="w",
        )
        fallback.grid(row=0, column=2, columnspan=2, sticky="w")

        left = self._settings_section(form, "Local Ollama", 1, 0)
        right = self._settings_section(form, "Cloud Providers", 1, 1)

        local_rows = [
            ("Ollama URL", "OLLAMA_BASE_URL", self.settings.ollama_base_url, False),
            ("Ollama model", "OLLAMA_MODEL", self.settings.ollama_model, False),
        ]
        cloud_rows = [
            ("OpenAI key", "OPENAI_API_KEY", "", True),
            ("OpenAI model", "OPENAI_MODEL", self.settings.openai_model, False),
            ("Claude key", "ANTHROPIC_API_KEY", "", True),
            ("Claude model", "ANTHROPIC_MODEL", self.settings.anthropic_model, False),
            ("Gemini key", "GEMINI_API_KEY", "", True),
            ("Gemini model", "GEMINI_MODEL", self.settings.gemini_model, False),
            ("Groq key", "GROQ_API_KEY", "", True),
            ("Groq model", "GROQ_MODEL", self.settings.groq_model, False),
        ]

        def fetch_models_for(provider: str) -> None:
            model_key = self._model_key_for_provider(provider)
            if not model_key or model_key not in model_entries:
                status.configure(text=f"No model field for {provider}.")
                return

            overrides = {key: entry.get() for key, entry in entries.items() if entry.get()}
            status.configure(text=f"Fetching {provider} models...")
            dialog.update_idletasks()

            try:
                models = list_models(provider, overrides=overrides)
            except LLMError as exc:
                fallback = self._fallback_models_for_provider(provider)
                if fallback:
                    model_box = model_entries[model_key]
                    model_box.configure(values=fallback)
                    if model_box.get() not in fallback:
                        model_box.set(fallback[0])
                    status.configure(
                        text=self._friendly_model_error(provider, str(exc))
                        + " Showing common models instead."
                    )
                    return
                status.configure(text=self._friendly_model_error(provider, str(exc)))
                return

            if not models:
                status.configure(text=f"No models found for {provider}.")
                return

            model_box = model_entries[model_key]
            model_box.configure(values=models)
            if model_box.get() not in models:
                model_box.set(models[0])
            status.configure(text=f"Loaded {len(models)} models for {provider}.")

        def test_provider_for(provider: str) -> None:
            overrides = {key: entry.get() for key, entry in entries.items() if entry.get()}
            status.configure(text=f"Testing {provider} connection...")
            dialog.update_idletasks()
            try:
                model = test_provider(provider, overrides=overrides)
            except LLMError as exc:
                status.configure(text=self._friendly_model_error(provider, str(exc)))
                return
            status.configure(text=f"{provider.title()} connection works. Example model: {model}")

        self._settings_entries(
            left,
            local_rows,
            values,
            entries,
            secret_keys,
            model_entries,
            fetch_models_for,
            test_provider_for,
        )
        self._settings_entries(
            right,
            cloud_rows,
            values,
            entries,
            secret_keys,
            model_entries,
            fetch_models_for,
            test_provider_for,
        )

        key_status = self._key_status_text()
        tk.Label(
            right,
            text=key_status,
            font=("Segoe UI", 8),
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            anchor="w",
            justify="left",
            wraplength=380,
        ).grid(row=len(cloud_rows) + 1, column=0, columnspan=2, sticky="ew", pady=(4, 8))

        button_bar = tk.Frame(dialog, bg=self.colors["bg"], padx=22, pady=14)
        button_bar.grid(row=2, column=0, sticky="ew")
        button_bar.columnconfigure(0, weight=1)

        status = tk.Label(
            button_bar,
            text="",
            font=("Segoe UI", 9),
            fg=self.colors["muted"],
            bg=self.colors["bg"],
            anchor="w",
            justify="left",
            wraplength=620,
        )
        status.grid(row=0, column=0, sticky="ew")

        buttons = tk.Frame(button_bar, bg=self.colors["bg"])
        buttons.grid(row=0, column=1, sticky="e")

        def save() -> None:
            updates = {
                "LOCAL_PILOT_MODEL_PROVIDER": provider_var.get(),
                "LOCAL_PILOT_ALLOW_CLOUD_FALLBACK": str(fallback_var.get()).lower(),
            }
            for key, entry in entries.items():
                value = entry.get()
                if key in secret_keys and not value:
                    continue
                updates[key] = value
            save_env_values(updates)
            self._refresh_settings_view()
            status.configure(text="Saved. New questions will use these settings.")

        ttk.Button(buttons, text="Save", style="Accent.TButton", command=save).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(buttons, text="Close", command=dialog.destroy).grid(row=0, column=1)

    def _settings_section(self, parent: tk.Frame, title: str, row: int, column: int) -> tk.Frame:
        section = tk.Frame(parent, bg=self.colors["panel"])
        section.grid(row=row, column=column, sticky="nsew", padx=(0, 16) if column == 0 else (16, 0))
        section.columnconfigure(1, weight=1)
        section.columnconfigure(2, weight=0)
        section.columnconfigure(3, weight=0)
        tk.Label(
            section,
            text=title,
            font=("Segoe UI", 10, "bold"),
            fg=self.colors["brand"],
            bg=self.colors["panel"],
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        return section

    def _settings_entries(
        self,
        parent: tk.Frame,
        rows: list[tuple[str, str, str, bool]],
        values: dict[str, str],
        entries: dict[str, tk.Entry],
        secret_keys: set[str],
        model_entries: dict[str, ttk.Combobox],
        fetch_models_for,
        test_provider_for,
    ) -> None:
        for row_index, (label, key, default, secret) in enumerate(rows, start=1):
            self._settings_label(parent, label, row_index)
            if key.endswith("_MODEL") or key == "OLLAMA_MODEL":
                entry = ttk.Combobox(parent, font=("Segoe UI", 10), values=())
                model_entries[key] = entry
            else:
                entry = tk.Entry(
                    parent,
                    font=("Segoe UI", 10),
                    fg=self.colors["text"],
                    bg="#ffffff",
                    relief=tk.SOLID,
                    bd=1,
                    show="*" if secret else "",
                )
            if key in secret_keys:
                entry.insert(0, "")
            else:
                entry.insert(0, values.get(key, default or ""))
            entry.grid(row=row_index, column=1, sticky="ew", pady=(0, 9), ipady=4)
            entries[key] = entry
            provider = self._provider_for_model_key(key)
            if provider:
                ttk.Button(
                    parent,
                    text="Fetch",
                    command=lambda value=provider: fetch_models_for(value),
                ).grid(row=row_index, column=2, sticky="e", padx=(8, 0), pady=(0, 9))
                ttk.Button(
                    parent,
                    text="Test",
                    command=lambda value=provider: test_provider_for(value),
                ).grid(row=row_index, column=3, sticky="e", padx=(8, 0), pady=(0, 9))

    def _model_key_for_provider(self, provider: str) -> str | None:
        return {
            "ollama": "OLLAMA_MODEL",
            "auto": "OLLAMA_MODEL",
            "openai": "OPENAI_MODEL",
            "anthropic": "ANTHROPIC_MODEL",
            "gemini": "GEMINI_MODEL",
            "groq": "GROQ_MODEL",
        }.get(provider)

    def _provider_for_model_key(self, model_key: str) -> str | None:
        return {
            "OLLAMA_MODEL": "ollama",
            "OPENAI_MODEL": "openai",
            "ANTHROPIC_MODEL": "anthropic",
            "GEMINI_MODEL": "gemini",
            "GROQ_MODEL": "groq",
        }.get(model_key)

    def _key_status_text(self) -> str:
        statuses = [
            ("OpenAI", bool(self.settings.openai_api_key)),
            ("Claude", bool(self.settings.anthropic_api_key)),
            ("Gemini", bool(self.settings.gemini_api_key)),
            ("Groq", bool(self.settings.groq_api_key)),
        ]
        return "Saved keys: " + ", ".join(f"{name} {'yes' if present else 'no'}" for name, present in statuses)

    def _friendly_model_error(self, provider: str, error: str) -> str:
        if "HTTP 403" in error:
            return (
                f"Could not fetch {provider} models: provider rejected access. "
                "Check the API key. For Groq, the key should usually start with gsk_."
            )
        if "API key is required" in error:
            return f"Add a {provider} API key first, then click Fetch."
        return f"Could not fetch {provider} models: {error}"

    def _fallback_models_for_provider(self, provider: str) -> list[str]:
        if provider == "groq":
            return [
                "llama-3.1-8b-instant",
                "llama-3.3-70b-versatile",
                "gemma2-9b-it",
                "mixtral-8x7b-32768",
            ]
        return []

    def _settings_label(self, parent: tk.Frame, text: str, row: int) -> None:
        tk.Label(
            parent,
            text=text,
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["muted"],
            bg=self.colors["panel"],
            anchor="w",
        ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=(0, 10))

    def _ask(self, event: object | None = None) -> str:
        question = self.question.get("1.0", tk.END).strip()
        if not question:
            return "break"

        self._submit_question(question)
        return "break"

    def _ask_prompt(self, prompt: str) -> None:
        self._submit_question(prompt)

    def _submit_question(self, question: str) -> None:
        self.question.delete("1.0", tk.END)
        self._append("You", question)
        self._set_busy(True)

        thread = threading.Thread(target=self._answer_in_background, args=(question,), daemon=True)
        thread.start()

    def _answer_in_background(self, question: str) -> None:
        try:
            result = answer_question(self.selected_path, question)
            self.messages.put(("Local Pilot", result["answer"]))
        except Exception as exc:
            self.messages.put(("Local Pilot", f"Something went wrong:\n{exc}"))
        finally:
            self.messages.put(("status", "ready"))

    def _drain_messages(self) -> None:
        while True:
            try:
                sender, text = self.messages.get_nowait()
            except queue.Empty:
                break

            if sender == "status":
                self._set_busy(False)
            else:
                self._append(sender, text)

        self.root.after(100, self._drain_messages)

    def _append(self, sender: str, text: str) -> None:
        is_user = sender == "You"
        row = tk.Frame(self.messages_frame, bg=self.colors["panel"])
        row.pack(fill="x", pady=(0, 12))
        row.columnconfigure(0, weight=1)

        bubble = tk.Frame(
            row,
            bg=self.colors["user"] if is_user else self.colors["assistant"],
            highlightbackground="#c7d2fe" if is_user else self.colors["border"],
            highlightthickness=1,
            padx=12,
            pady=10,
        )
        bubble.grid(row=0, column=0, sticky="e" if is_user else "w")

        tk.Label(
            bubble,
            text=sender,
            font=("Segoe UI", 9, "bold"),
            fg=self.colors["brand"] if not is_user else self.colors["brand_dark"],
            bg=bubble["bg"],
            anchor="w",
        ).pack(fill="x", anchor="w")

        tk.Label(
            bubble,
            text=text,
            font=("Segoe UI", 10),
            fg=self.colors["text"],
            bg=bubble["bg"],
            justify="left",
            anchor="w",
            wraplength=620,
        ).pack(fill="x", anchor="w", pady=(4, 0))

        self.root.update_idletasks()
        self.chat_canvas.yview_moveto(1.0)

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self.ask_button.configure(state=tk.DISABLED)
            self.status.configure(text=f"Thinking with {self.settings.model_provider.title()}...")
        else:
            self.ask_button.configure(state=tk.NORMAL)
            self.status.configure(text="Ctrl+Enter to ask")

    def _sync_scroll_region(self, event: object | None = None) -> None:
        self.chat_canvas.configure(scrollregion=self.chat_canvas.bbox("all"))

    def _sync_message_width(self, event: tk.Event) -> None:
        self.chat_canvas.itemconfigure(self.messages_window, width=event.width)

    def _on_mousewheel(self, event: tk.Event) -> None:
        self.chat_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def main() -> None:
    parser = argparse.ArgumentParser(description="Open Local Pilot chat for a selected path.")
    parser.add_argument("path", help="Selected file or folder path")
    args = parser.parse_args()

    LocalPilotPopup(args.path).run()


if __name__ == "__main__":
    main()
