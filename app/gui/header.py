"""Header widget — replaces Header.tsx.

Shows the Local Pilot logo, title, stage badge, and connection status pill.
Supports dynamic status updates for Ollama connection state.
"""

from __future__ import annotations

import customtkinter as ctk

from app.gui import theme


class Header(ctk.CTkFrame):
    """Top header bar with branding and status indicator."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs):
        super().__init__(
            master,
            fg_color="transparent",
            **kwargs,
        )

        # ── Left: Logo + Title ──────────────────────────────────────────
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        # Logo icon (gradient-like colored square)
        logo_frame = ctk.CTkFrame(
            left,
            width=36,
            height=36,
            corner_radius=10,
            fg_color=theme.ACCENT_INDIGO,
        )
        logo_frame.pack(side="left", padx=(0, 12))
        logo_frame.pack_propagate(False)

        logo_label = ctk.CTkLabel(
            logo_frame,
            text="✦",
            font=(theme.FONT_FAMILY[0], 16, "bold"),
            text_color="#ffffff",
        )
        logo_label.place(relx=0.5, rely=0.5, anchor="center")

        # Title area
        title_area = ctk.CTkFrame(left, fg_color="transparent")
        title_area.pack(side="left", fill="y")

        # Title row with badge
        title_row = ctk.CTkFrame(title_area, fg_color="transparent")
        title_row.pack(anchor="w")

        title = ctk.CTkLabel(
            title_row,
            text="Local Pilot",
            font=(theme.FONT_FAMILY[0], 24, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        title.pack(side="left")

        badge = ctk.CTkLabel(
            title_row,
            text=" STAGE 2 ",
            font=(theme.FONT_FAMILY[0], 9, "bold"),
            text_color=theme.ACCENT_INDIGO_HOVER,
            fg_color=theme.ACCENT_INDIGO_BG,
            corner_radius=4,
        )
        badge.pack(side="left", padx=(8, 0))

        subtitle = ctk.CTkLabel(
            title_area,
            text="Your AI-powered local companion",
            font=(theme.FONT_FAMILY[0], 14),
            text_color=theme.TEXT_SECONDARY,
        )
        subtitle.pack(anchor="w")

        # ── Right: Status pill + Quit button ────────────────────────────
        right_area = ctk.CTkFrame(self, fg_color="transparent")
        right_area.pack(side="right")

        self._status_pill = ctk.CTkFrame(
            right_area,
            fg_color=theme.BG_SURFACE,
            corner_radius=20,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
        )
        self._status_pill.pack(side="left", padx=(0, 10))

        self._dot = ctk.CTkLabel(
            self._status_pill,
            text="●",
            font=(theme.FONT_FAMILY[0], 8),
            text_color=theme.STATUS_WARNING_TEXT,
            width=10,
        )
        self._dot.pack(side="left", padx=(10, 4), pady=6)

        self._status_text = ctk.CTkLabel(
            self._status_pill,
            text="Connecting...",
            font=(theme.FONT_FAMILY[0], 12, "bold"),
            text_color=theme.STATUS_WARNING_TEXT,
        )
        self._status_text.pack(side="left", padx=(0, 12), pady=6)

        self._quit_btn = ctk.CTkButton(
            right_area,
            text="Quit",
            width=50,
            height=28,
            font=(theme.FONT_FAMILY[0], 11, "bold"),
            fg_color="transparent",
            hover_color=theme.BG_HOVER,
            text_color=theme.TEXT_MUTED,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
            corner_radius=6,
            command=self._handle_quit,
        )
        self._quit_btn.pack(side="left")

    def _handle_quit(self):
        """Fully destroy the application (shutdown daemon)."""
        self.winfo_toplevel().destroy()

    def set_status(self, text: str, color: str = theme.STATUS_CONNECTED):
        """Update the status pill text and dot color."""
        self._dot.configure(text_color=color)
        self._status_text.configure(text=text)
