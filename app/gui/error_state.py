"""ErrorState widget — replaces ErrorState.tsx.

Shown when a file/directory cannot be loaded or parsed.
"""

from __future__ import annotations

import customtkinter as ctk

from app.gui import theme


class ErrorState(ctk.CTkFrame):
    """Error display card with file path and technical details."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        error: str,
        file_path: str | None = None,
        **kwargs,
    ):
        super().__init__(
            master,
            fg_color=theme.STATUS_OFFLINE_BG,
            corner_radius=theme.CORNER_RADIUS,
            border_width=1,
            border_color=theme.STATUS_OFFLINE_BORDER,
            **kwargs,
        )

        pad = theme.PAD_LG

        # ── Icon ────────────────────────────────────────────────────────
        icon_frame = ctk.CTkFrame(
            self,
            width=48,
            height=48,
            corner_radius=12,
            fg_color="#3a0a18",
            border_width=1,
            border_color=theme.STATUS_OFFLINE_BORDER,
        )
        icon_frame.pack(pady=(pad, 10))
        icon_frame.pack_propagate(False)

        icon = ctk.CTkLabel(
            icon_frame,
            text="⚠",
            font=(theme.FONT_FAMILY[0], 20),
            text_color=theme.STATUS_OFFLINE_TEXT,
        )
        icon.place(relx=0.5, rely=0.5, anchor="center")

        # ── Title ───────────────────────────────────────────────────────
        title = ctk.CTkLabel(
            self,
            text="Unable to load selected file.",
            font=(theme.FONT_FAMILY[0], 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        title.pack()

        desc = ctk.CTkLabel(
            self,
            text="The file could not be accessed or parsed by the Local Pilot service.",
            font=(theme.FONT_FAMILY[0], 11),
            text_color=theme.TEXT_MUTED,
        )
        desc.pack(pady=(2, 12))

        # ── File path ───────────────────────────────────────────────────
        if file_path:
            path_label = ctk.CTkLabel(
                self,
                text="ATTEMPTED FILE PATH",
                font=(theme.FONT_FAMILY[0], 9, "bold"),
                text_color=theme.TEXT_DISABLED,
                anchor="w",
            )
            path_label.pack(fill="x", padx=pad)

            path_value = ctk.CTkLabel(
                self,
                text=file_path,
                font=(theme.FONT_MONO[0], 11),
                text_color=theme.STATUS_OFFLINE_TEXT,
                fg_color="#1a0510",
                corner_radius=theme.CORNER_RADIUS_SM,
                anchor="w",
            )
            path_value.pack(fill="x", padx=pad, pady=(4, 8))

        # ── Technical details ───────────────────────────────────────────
        if error:
            details_label = ctk.CTkLabel(
                self,
                text="TECHNICAL DETAILS",
                font=(theme.FONT_FAMILY[0], 9, "bold"),
                text_color=theme.TEXT_DISABLED,
                anchor="w",
            )
            details_label.pack(fill="x", padx=pad)

            details_box = ctk.CTkTextbox(
                self,
                height=60,
                font=(theme.FONT_MONO[0], 10),
                text_color=theme.TEXT_MUTED,
                fg_color=theme.BG_INPUT,
                border_width=1,
                border_color=theme.BORDER_SUBTLE,
                corner_radius=theme.CORNER_RADIUS_SM,
                wrap="word",
                activate_scrollbars=True,
            )
            details_box.pack(fill="x", padx=pad, pady=(4, 0))
            details_box.insert("1.0", error)
            details_box.configure(state="disabled")

        # ── Help text ───────────────────────────────────────────────────
        help_text = ctk.CTkLabel(
            self,
            text="Please ensure the file exists and that you have appropriate read permissions.",
            font=(theme.FONT_FAMILY[0], 10),
            text_color=theme.TEXT_DISABLED,
        )
        help_text.pack(pady=(10, pad))
