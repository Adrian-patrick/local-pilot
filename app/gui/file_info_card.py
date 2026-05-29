"""FileInfoCard widget — replaces FileInfoCard.tsx.

Displays parsed file/directory metadata in a premium dark card.
"""

from __future__ import annotations

import customtkinter as ctk

from app.file_service import FileMetadata
from app.gui import theme


def _format_size(size_bytes: int) -> str:
    """Format bytes to human-readable form (matching the React helper)."""
    if size_bytes == 0:
        return "0 Bytes"
    units = ["Bytes", "KB", "MB", "GB"]
    k = 1024
    i = 0
    val = float(size_bytes)
    while val >= k and i < len(units) - 1:
        val /= k
        i += 1
    return f"{val:.1f} {units[i]}" if i > 0 else f"{int(val)} {units[i]}"


class FileInfoCard(ctk.CTkFrame):
    """Card showing active file/directory metadata."""

    def __init__(self, master: ctk.CTkBaseClass, metadata: FileMetadata, **kwargs):
        super().__init__(
            master,
            fg_color=theme.BG_CARD,
            corner_radius=theme.CORNER_RADIUS,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
            **kwargs,
        )

        self._metadata = metadata
        self._build()

    def _build(self):
        md = self._metadata
        pad = theme.PAD_MD

        # ── Top row: icon + name | extension badge ──────────────────────
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=pad, pady=(pad, 0))

        # Left: icon + titles
        left = ctk.CTkFrame(top_row, fg_color="transparent")
        left.pack(side="left", fill="x", expand=True)

        # Icon
        icon_color = theme.EXT_YELLOW if md.is_dir else theme.ACCENT_INDIGO_HOVER
        icon_bg = theme.EXT_YELLOW_BG if md.is_dir else theme.ACCENT_INDIGO_BG
        icon_text = "📁" if md.is_dir else "📄"

        icon_frame = ctk.CTkFrame(
            left,
            width=42,
            height=42,
            corner_radius=10,
            fg_color=icon_bg,
            border_width=1,
            border_color=theme.BORDER_SUBTLE,
        )
        icon_frame.pack(side="left", padx=(0, 12))
        icon_frame.pack_propagate(False)

        icon_label = ctk.CTkLabel(
            icon_frame,
            text=icon_text,
            font=(theme.FONT_FAMILY[0], 18),
        )
        icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Title stack
        title_stack = ctk.CTkFrame(left, fg_color="transparent")
        title_stack.pack(side="left", fill="y")

        context_label = ctk.CTkLabel(
            title_stack,
            text="Active Directory" if md.is_dir else "Active Context",
            font=(theme.FONT_FAMILY[0], 10, "bold"),
            text_color=icon_color,
        )
        context_label.pack(anchor="w")

        name_label = ctk.CTkLabel(
            title_stack,
            text=md.file_name,
            font=(theme.FONT_FAMILY[0], 14, "bold"),
            text_color=theme.TEXT_PRIMARY,
        )
        name_label.pack(anchor="w")

        # Extension badge (right)
        ext_text_color, ext_bg_color = theme.get_ext_colors(md.extension)
        badge = ctk.CTkLabel(
            top_row,
            text=f" {md.extension or 'FILE'} ",
            font=(theme.FONT_FAMILY[0], 11, "bold"),
            text_color=ext_text_color,
            fg_color=ext_bg_color,
            corner_radius=12,
        )
        badge.pack(side="right")

        # ── Details grid ────────────────────────────────────────────────
        details = ctk.CTkFrame(self, fg_color="transparent")
        details.pack(fill="x", padx=pad, pady=(0, pad))

        # Full path
        self._add_detail_row(
            details,
            "Full Directory Path" if md.is_dir else "Full File Path",
            md.full_path,
            mono=True,
            full_width=True,
        )

        # Bottom row: size + last modified
        bottom_row = ctk.CTkFrame(details, fg_color="transparent")
        bottom_row.pack(fill="x", pady=(10, 0))

        # Size / Type
        size_frame = ctk.CTkFrame(bottom_row, fg_color="transparent")
        size_frame.pack(side="left", fill="x", expand=True)

        size_label_title = ctk.CTkLabel(
            size_frame,
            text="TYPE" if md.is_dir else "FILE SIZE",
            font=(theme.FONT_FAMILY[0], 9, "bold"),
            text_color=theme.TEXT_DISABLED,
        )
        size_label_title.pack(anchor="w")

        size_value = ctk.CTkLabel(
            size_frame,
            text="Directory Folder" if md.is_dir else _format_size(md.file_size),
            font=(theme.FONT_FAMILY[0], 13),
            text_color=theme.TEXT_PRIMARY,
        )
        size_value.pack(anchor="w")

        # Last modified
        mod_frame = ctk.CTkFrame(bottom_row, fg_color="transparent")
        mod_frame.pack(side="left", fill="x", expand=True)

        mod_label_title = ctk.CTkLabel(
            mod_frame,
            text="LAST MODIFIED",
            font=(theme.FONT_FAMILY[0], 9, "bold"),
            text_color=theme.TEXT_DISABLED,
        )
        mod_label_title.pack(anchor="w")

        mod_value = ctk.CTkLabel(
            mod_frame,
            text=md.last_modified,
            font=(theme.FONT_FAMILY[0], 13),
            text_color=theme.TEXT_PRIMARY,
        )
        mod_value.pack(anchor="w")

    def _add_detail_row(
        self,
        parent: ctk.CTkFrame,
        label: str,
        value: str,
        *,
        mono: bool = False,
        full_width: bool = False,
    ):
        """Add a label+value detail row."""
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x" if full_width else "none", anchor="w", pady=(2, 0))

        title = ctk.CTkLabel(
            row,
            text=label.upper(),
            font=(theme.FONT_FAMILY[0], 9, "bold"),
            text_color=theme.TEXT_DISABLED,
        )
        title.pack(anchor="w")

        font = (theme.FONT_MONO[0], 11) if mono else (theme.FONT_FAMILY[0], 13)

        val = ctk.CTkLabel(
            row,
            text=value,
            font=font,
            text_color=theme.TEXT_SECONDARY if mono else theme.TEXT_PRIMARY,
            anchor="w",
        )
        val.pack(anchor="w")
