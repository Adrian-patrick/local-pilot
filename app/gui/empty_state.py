"""EmptyState widget — replaces EmptyState.tsx.

Shown when the app is opened directly without a file context argument.
Displays a usage guide with numbered steps.
"""

from __future__ import annotations

import customtkinter as ctk

from app.gui import theme


class EmptyState(ctk.CTkFrame):
    """Guide card shown when no file path was provided."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs):
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=theme.CORNER_RADIUS,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
            **kwargs,
        )

        pad = theme.PAD_LG

        # ── Icon ────────────────────────────────────────────────────────
        icon_frame = ctk.CTkFrame(
            self,
            width=52,
            height=52,
            corner_radius=14,
            fg_color=theme.ACCENT_INDIGO_BG,
            border_width=1,
            border_color=theme.ACCENT_INDIGO_DIM,
        )
        icon_frame.pack(pady=(pad, 12))
        icon_frame.pack_propagate(False)

        icon = ctk.CTkLabel(
            icon_frame,
            text="🎯",
            font=(theme.FONT_FAMILY[0], 22),
        )
        icon.place(relx=0.5, rely=0.5, anchor="center")

        # ── Title ───────────────────────────────────────────────────────
        title = ctk.CTkLabel(
            self,
            text="Ready for File Context",
            font=(theme.FONT_FAMILY[0], 15, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        title.pack()

        desc = ctk.CTkLabel(
            self,
            text=(
                'Local Pilot runs as an OS-native contextual workspace.\n'
                'To load a file, right-click any file in your Explorer\n'
                'and choose "Ask Local Pilot".'
            ),
            font=(theme.FONT_FAMILY[0], 11),
            text_color=theme.TEXT_MUTED,
            justify="center",
        )
        desc.pack(pady=(4, 16))

        # ── Step-by-step guide ──────────────────────────────────────────
        guide = ctk.CTkFrame(
            self,
            fg_color=theme.BG_INPUT,
            corner_radius=theme.CORNER_RADIUS_SM,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
        )
        guide.pack(fill="x", padx=pad, pady=(0, 4))

        guide_title = ctk.CTkLabel(
            guide,
            text="HOW TO USE IN STAGE 2",
            font=(theme.FONT_FAMILY[0], 9, "bold"),
            text_color=theme.ACCENT_INDIGO_HOVER,
        )
        guide_title.pack(anchor="w", padx=14, pady=(12, 8))

        steps = [
            ("1", "Open Windows Explorer."),
            ("2", 'Right-click any file and select "Ask Local Pilot".'),
            ("3", "The Local Pilot app opens with file metadata displayed."),
        ]

        for num, text in steps:
            step_row = ctk.CTkFrame(guide, fg_color="transparent")
            step_row.pack(fill="x", padx=14, pady=(0, 8))

            is_last = num == "3"
            dot_color = theme.ACCENT_INDIGO_BG if is_last else theme.BG_SURFACE
            dot_text_color = theme.ACCENT_INDIGO_HOVER if is_last else theme.TEXT_MUTED

            dot = ctk.CTkLabel(
                step_row,
                text=num,
                width=22,
                height=22,
                corner_radius=11,
                fg_color=dot_color,
                font=(theme.FONT_FAMILY[0], 10, "bold"),
                text_color=dot_text_color,
            )
            dot.pack(side="left", padx=(0, 10))

            step_text = ctk.CTkLabel(
                step_row,
                text=text,
                font=(theme.FONT_FAMILY[0], 11),
                text_color=theme.TEXT_SECONDARY,
                anchor="w",
            )
            step_text.pack(side="left", fill="x", expand=True)

        # ── Bottom badge ────────────────────────────────────────────────
        bottom_badge = ctk.CTkLabel(
            self,
            text=" Windows Context Menu is integrated and fully functional! ",
            font=(theme.FONT_FAMILY[0], 9, "bold"),
            text_color=theme.ACCENT_INDIGO_DIM,
            fg_color=theme.BG_SURFACE,
            corner_radius=12,
        )
        bottom_badge.pack(pady=(8, pad))
