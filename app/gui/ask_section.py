"""AskSection widget — the chat/prompt interface.

Replaces AskSection.tsx from the React app.
Provides a text input, model selector, and scrollable response area
with real-time streaming display of LLM responses.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import tkinter as tk

import customtkinter as ctk

from app.gui import theme

log = logging.getLogger(__name__)


class AskSection(ctk.CTkFrame):
    """Chat interface with prompt input and streaming response display."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        models: list[str] | None = None,
        selected_model: str | None = None,
        on_submit: "callable[[str, str], None] | None" = None,
        **kwargs,
    ):
        """
        Args:
            master: Parent widget.
            models: List of available model names.
            selected_model: Currently selected model name.
            on_submit: Callback(model, user_query) triggered on send.
        """
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=theme.CORNER_RADIUS,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
            **kwargs,
        )

        self._on_submit = on_submit
        self._is_generating = False
        self._token_buffer = []
        self._flush_lock = threading.Lock()
        self._flush_pending = False

        pad = theme.PAD_MD

        # ── Header row: "Ask" title + model selector ─────────────────────
        header_row = ctk.CTkFrame(self, fg_color="transparent")
        header_row.pack(fill="x", padx=pad, pady=(pad, 0))

        ask_icon = ctk.CTkLabel(
            header_row,
            text="💬",
            font=(theme.FONT_FAMILY[0], 16),
        )
        ask_icon.pack(side="left", padx=(0, 6))

        ask_title = ctk.CTkLabel(
            header_row,
            text="Ask Local Pilot",
            font=(theme.FONT_FAMILY[0], 15, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        ask_title.pack(side="left")

        # Model selector
        model_values = models or ["No models"]
        default_model = selected_model or (model_values[0] if model_values else "")

        self._model_var = ctk.StringVar(value=default_model)
        self._model_dropdown = ctk.CTkOptionMenu(
            header_row,
            variable=self._model_var,
            values=model_values,
            width=200,
            height=32,
            font=(theme.FONT_FAMILY[0], 12),
            dropdown_font=(theme.FONT_FAMILY[0], 12),
            fg_color=theme.BG_INPUT,
            button_color=theme.BG_HOVER,
            button_hover_color=theme.ACCENT_INDIGO_DIM,
            dropdown_fg_color=theme.BG_SURFACE,
            dropdown_hover_color=theme.BG_HOVER,
            text_color=theme.TEXT_SECONDARY,
            corner_radius=theme.CORNER_RADIUS_XS,
        )
        self._model_dropdown.pack(side="right")

        # ── Response display area ────────────────────────────────────────
        self._response_box = ctk.CTkTextbox(
            self,
            font=(theme.FONT_MONO[0], 12),
            text_color=theme.TEXT_SECONDARY,
            fg_color=theme.BG_INPUT,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
            corner_radius=theme.CORNER_RADIUS_SM,
            wrap="word",
            activate_scrollbars=True,
        )
        
        # Configure Markdown tags
        tb = self._response_box._textbox
        tb.tag_config("bold", font=(theme.FONT_FAMILY[0], 12, "bold"), foreground=theme.TEXT_PRIMARY)
        tb.tag_config("code", font=(theme.FONT_MONO[0], 12), foreground=theme.ACCENT_INDIGO_HOVER, background=theme.BG_SURFACE)
        tb.tag_config("header", font=(theme.FONT_FAMILY[0], 14, "bold"), foreground=theme.ACCENT_INDIGO)
        tb.tag_config("hidden", elide=True)
        tb.tag_config("user_msg", font=(theme.FONT_FAMILY[0], 13, "bold"), foreground=theme.ACCENT_INDIGO)
        tb.tag_config("ai_msg", font=(theme.FONT_FAMILY[0], 13, "bold"), foreground=theme.STATUS_CONNECTED)

        self._response_box.insert("1.0", "Responses will appear here...\n")
        self._response_box.configure(state="disabled")

        # ── Input row: text entry + send button ──────────────────────────
        input_row = ctk.CTkFrame(self, fg_color="transparent")

        self._input_entry = ctk.CTkEntry(
            input_row,
            placeholder_text="Ask anything about the loaded file...",
            font=(theme.FONT_FAMILY[0], 14),
            text_color=theme.TEXT_PRIMARY,
            fg_color=theme.BG_INPUT,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
            corner_radius=theme.CORNER_RADIUS_SM,
            height=44,
        )
        self._input_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self._input_entry.bind("<Return>", self._handle_enter)

        self._agent_mode_switch = ctk.CTkSwitch(
            input_row,
            text="Agent Mode",
            font=(theme.FONT_FAMILY[0], 12, "bold"),
            text_color=theme.ACCENT_INDIGO,
            progress_color=theme.ACCENT_INDIGO
        )
        self._agent_mode_switch.pack(side="right", padx=(0, 10))

        self._send_btn = ctk.CTkButton(
            input_row,
            text="Send ▸",
            width=90,
            height=44,
            font=(theme.FONT_FAMILY[0], 14, "bold"),
            fg_color=theme.ACCENT_INDIGO,
            hover_color=theme.ACCENT_INDIGO_HOVER,
            text_color="#ffffff",
            corner_radius=theme.CORNER_RADIUS_SM,
            command=self._handle_send,
        )
        self._send_btn.pack(side="right")

        # ── Status bar & Rate Limit Bar ─────────────────────────────────
        self._status_row = ctk.CTkFrame(self, fg_color="transparent")
        
        self._status_label = ctk.CTkLabel(
            self._status_row,
            text="",
            font=(theme.FONT_FAMILY[0], 11),
            text_color=theme.TEXT_MUTED,
            height=18,
        )
        self._status_label.pack(side="left")
        
        self._rate_limit_bar = ctk.CTkProgressBar(
            self._status_row,
            width=100,
            height=6,
            fg_color=theme.BG_INPUT,
            progress_color=theme.STATUS_CONNECTED
        )
        self._rate_limit_bar.set(0)
        self._rate_limit_bar.pack(side="right", pady=6)
        self._rate_limit_bar.pack_forget() # Hide by default
        
        self._rate_limit_text = ctk.CTkLabel(
            self._status_row,
            text="",
            font=(theme.FONT_FAMILY[0], 10),
            text_color=theme.TEXT_MUTED
        )
        self._rate_limit_text.pack(side="right", padx=8)
        
        # State tracking for the timer
        self._rate_reset_time: float = 0.0
        self._check_rate_limit_reset()
        
        # ── Packing order (bottom up) ────────────────────────────────────
        self._status_row.pack(side="bottom", fill="x", padx=pad, pady=(0, 6))
        input_row.pack(side="bottom", fill="x", padx=pad, pady=(8, pad))
        self._response_box.pack(side="top", fill="both", expand=True, padx=pad, pady=(10, 0))

    # ── Public API ────────────────────────────────────────────────────────

    def update_models(self, models: list[str], selected: str | None = None):
        """Update the model dropdown with new values."""
        if not models:
            models = ["No models"]
        self._model_dropdown.configure(values=models)
        if selected and selected in models:
            self._model_var.set(selected)
        elif models:
            self._model_var.set(models[0])

    def get_selected_model(self) -> str:
        """Return the currently selected model name."""
        return self._model_var.get()

    def is_agent_mode(self) -> bool:
        """Return True if Agent Mode is enabled."""
        return self._agent_mode_switch.get() == 1

    def set_status(self, text: str):
        """Update the status bar text."""
        self._status_label.configure(text=text)

    def set_response(self, text: str):
        """Replace the entire response area with new text."""
        self._response_box.configure(state="normal")
        self._response_box.delete("1.0", "end")
        self._response_box.insert("1.0", text)
        self._response_box.configure(state="disabled")

    def append_user_message(self, text: str):
        """Append the user's query and a placeholder for the AI response to create a chat history."""
        self._response_box.configure(state="normal")
        if self._response_box.get("1.0", "end").strip() == "Responses will appear here...":
            self._response_box.delete("1.0", "end")
        
        if self._response_box.get("end-2c", "end-1c") != "\n":
            self._response_box.insert("end", "\n")
            
        self._response_box.insert("end", "You\n", "user_msg")
        self._response_box.insert("end", f"{text}\n\n")
        self._response_box.insert("end", "Local Pilot\n", "ai_msg")
        
        self._response_box.see("end")
        self._response_box.configure(state="disabled")

    def append_response(self, token: str):
        """Buffer a token for rendering. Thread-safe."""
        with self._flush_lock:
            self._token_buffer.append(token)
            if not self._flush_pending:
                self._flush_pending = True
                self.after(10, self._flush_tokens)

    def _flush_tokens(self):
        """Flush buffered tokens to the UI."""
        with self._flush_lock:
            if not self._token_buffer:
                self._flush_pending = False
                return
            text_to_insert = "".join(self._token_buffer)
            self._token_buffer.clear()
            self._flush_pending = False

        self._response_box.configure(state="normal")
        self._response_box.insert("end", text_to_insert)
        self._apply_markdown()
        self._response_box.see("end")
        self._response_box.configure(state="disabled")

    def _apply_markdown(self):
        """Parse the entire text box and apply basic markdown tags."""
        tb = self._response_box._textbox
        content = tb.get("1.0", "end")

        for tag in ["bold", "code", "header", "hidden"]:
            tb.tag_remove(tag, "1.0", "end")

        # Code blocks (```code```)
        for match in re.finditer(r'```(.*?)```', content, flags=re.DOTALL):
            start = f"1.0+{match.start()}c"
            inner_start = f"1.0+{match.start(1)}c"
            inner_end = f"1.0+{match.end(1)}c"
            end = f"1.0+{match.end()}c"
            tb.tag_add("hidden", start, inner_start)
            tb.tag_add("hidden", inner_end, end)
            tb.tag_add("code", inner_start, inner_end)

        # Inline code (`code`)
        for match in re.finditer(r'`(.*?)`', content):
            start = f"1.0+{match.start()}c"
            inner_start = f"1.0+{match.start(1)}c"
            inner_end = f"1.0+{match.end(1)}c"
            end = f"1.0+{match.end()}c"
            tb.tag_add("hidden", start, inner_start)
            tb.tag_add("hidden", inner_end, end)
            tb.tag_add("code", inner_start, inner_end)

        # Bold (**text**)
        for match in re.finditer(r'\*\*(.*?)\*\*', content):
            start = f"1.0+{match.start()}c"
            inner_start = f"1.0+{match.start(1)}c"
            inner_end = f"1.0+{match.end(1)}c"
            end = f"1.0+{match.end()}c"
            tb.tag_add("hidden", start, inner_start)
            tb.tag_add("hidden", inner_end, end)
            tb.tag_add("bold", inner_start, inner_end)

        # Headers (### Header)
        for match in re.finditer(r'^(#{1,6})\s+(.*?)$', content, flags=re.MULTILINE):
            start = f"1.0+{match.start()}c"
            inner_start = f"1.0+{match.start(2)}c"
            end = f"1.0+{match.end()}c"
            tb.tag_add("hidden", start, inner_start)
            tb.tag_add("header", inner_start, end)

    def update_rate_limit(self, limits: dict):
        """Update the visual progress bar based on rate limit headers."""
        try:
            remain = float(limits.get("tok_remain", 1))
            total = float(limits.get("tok_limit", 1))
            self._rate_reset_time = limits.get("tok_reset_ts", 0)
            
            # Progress is how much we HAVE used
            used_ratio = max(0.0, min(1.0, 1.0 - (remain / total)))
            
            self._rate_limit_bar.set(used_ratio)
            self._rate_limit_bar.pack(side="right", pady=6)
            
            # Change color if getting close to limit
            if used_ratio > 0.9:
                self._rate_limit_bar.configure(progress_color="#ef4444") # Red
            elif used_ratio > 0.75:
                self._rate_limit_bar.configure(progress_color="#eab308") # Yellow
            else:
                self._rate_limit_bar.configure(progress_color=theme.STATUS_CONNECTED) # Green
                
            self._rate_limit_text.configure(text=f"Tokens: {int(remain)}/{int(total)}")
        except Exception as e:
            log.warning("Failed to update rate limit visual: %s", e)

    def _check_rate_limit_reset(self):
        """Timer loop that clears the rate limit bar once the reset time is passed."""
        if self._rate_reset_time > 0 and time.time() >= self._rate_reset_time:
            self._rate_limit_bar.set(0)
            self._rate_limit_bar.configure(progress_color=theme.STATUS_CONNECTED)
            self._rate_limit_text.configure(text="Limits Reset")
            self._rate_reset_time = 0.0
            
        self.after(1000, self._check_rate_limit_reset)

    def clear_response(self):
        """Clear the response area."""
        self._response_box.configure(state="normal")
        self._response_box.delete("1.0", "end")
        self._response_box.configure(state="disabled")

    def set_generating(self, is_generating: bool):
        """Toggle the generating state (disables/enables input)."""
        self._is_generating = is_generating
        if is_generating:
            self._send_btn.configure(
                text="Stop ■",
                fg_color=theme.STATUS_OFFLINE_TEXT,
                hover_color="#e11d48",
            )
            self._input_entry.configure(state="disabled")
        else:
            self._send_btn.configure(
                text="Send ▸",
                fg_color=theme.ACCENT_INDIGO,
                hover_color=theme.ACCENT_INDIGO_HOVER,
            )
            self._input_entry.configure(state="normal")

    # ── Event handlers ────────────────────────────────────────────────────

    def _handle_enter(self, _event=None):
        """Handle Enter key press."""
        if not self._is_generating:
            self._handle_send()

    def _handle_send(self):
        """Handle send button click."""
        if self._is_generating:
            # TODO: implement cancellation via a threading event
            return

        query = self._input_entry.get().strip()
        if not query:
            return

        model = self._model_var.get()
        if model == "No models":
            self.set_status("⚠ No models available. Please install a model first.")
            return

        self._input_entry.delete(0, "end")

        if self._on_submit:
            self._on_submit(model, query)
