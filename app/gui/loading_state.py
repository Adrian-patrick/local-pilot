"""LoadingState widget — replaces LoadingState.tsx.

Skeleton placeholder card shown while file metadata is being loaded.
"""

from __future__ import annotations

import customtkinter as ctk

from app.gui import theme


class LoadingState(ctk.CTkFrame):
    """Animated skeleton loading placeholder."""

    def __init__(self, master: ctk.CTkBaseClass, **kwargs):
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=theme.CORNER_RADIUS,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
            **kwargs,
        )

        pad = theme.PAD_MD

        # Top row skeleton
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=pad, pady=(pad, 0))

        icon_skel = ctk.CTkFrame(
            top, width=42, height=42, corner_radius=10, fg_color=theme.BG_SURFACE
        )
        icon_skel.pack(side="left", padx=(0, 12))
        icon_skel.pack_propagate(False)

        title_skel_area = ctk.CTkFrame(top, fg_color="transparent")
        title_skel_area.pack(side="left", fill="y")

        ctk.CTkFrame(
            title_skel_area, width=80, height=10, corner_radius=4, fg_color=theme.BG_SURFACE
        ).pack(anchor="w", pady=(0, 6))
        ctk.CTkFrame(
            title_skel_area, width=180, height=14, corner_radius=4, fg_color=theme.BG_HOVER
        ).pack(anchor="w")

        badge_skel = ctk.CTkFrame(
            top, width=56, height=20, corner_radius=10, fg_color=theme.BG_SURFACE
        )
        badge_skel.pack(side="right")
        badge_skel.pack_propagate(False)

        # Separator
        sep = ctk.CTkFrame(self, height=1, fg_color=theme.BORDER_SUBTLE)
        sep.pack(fill="x", padx=pad, pady=pad)

        # Path skeleton
        ctk.CTkFrame(
            self, width=96, height=8, corner_radius=4, fg_color=theme.BG_SURFACE
        ).pack(anchor="w", padx=pad)
        ctk.CTkFrame(
            self, height=32, corner_radius=theme.CORNER_RADIUS_SM, fg_color=theme.BG_SURFACE
        ).pack(fill="x", padx=pad, pady=(6, 0))

        # Bottom row
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=pad, pady=pad)

        for w in [80, 112]:
            col = ctk.CTkFrame(bottom, fg_color="transparent")
            col.pack(side="left", fill="x", expand=True)
            ctk.CTkFrame(
                col, width=64, height=8, corner_radius=4, fg_color=theme.BG_SURFACE
            ).pack(anchor="w", pady=(0, 6))
            ctk.CTkFrame(
                col, width=w, height=14, corner_radius=4, fg_color=theme.BG_HOVER
            ).pack(anchor="w")

        # Pulse animation label
        self._loading_label = ctk.CTkLabel(
            self,
            text="Loading file metadata…",
            font=(theme.FONT_FAMILY[0], 11),
            text_color=theme.TEXT_MUTED,
        )
        self._loading_label.pack(pady=(0, pad))
