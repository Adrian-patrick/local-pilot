"""Centralized theme constants for the Local Pilot GUI.

Mirrors the dark glassmorphic design from the React/TailwindCSS UI:
  - Background: #0c0c0e with radial gradient overlay
  - Surface cards: subtle white-on-dark transparency
  - Accent: Indigo (#6366f1) with violet/emerald highlights
"""

# ── Core backgrounds ──────────────────────────────────────────────────────
BG_PRIMARY = "#000000"
BG_SURFACE = "#0A0A0A"
BG_CARD = "#121212"
BG_INPUT = "#1A1A1A"
BG_HOVER = "#27272A"

# ── Borders ───────────────────────────────────────────────────────────────
BORDER_SUBTLE = "#27272A"
BORDER_MUTED = "#3F3F46"

# ── Text ──────────────────────────────────────────────────────────────────
TEXT_PRIMARY = "#FAFAFA"
TEXT_SECONDARY = "#A1A1AA"
TEXT_MUTED = "#71717A"
TEXT_DISABLED = "#52525B"

# ── Accents ───────────────────────────────────────────────────────────────
ACCENT_INDIGO = "#6366f1"
ACCENT_INDIGO_HOVER = "#818cf8"
ACCENT_INDIGO_DIM = "#312e81"
ACCENT_INDIGO_BG = "#1e1b4b"

ACCENT_VIOLET = "#8b5cf6"
ACCENT_EMERALD = "#34d399"
ACCENT_EMERALD_DIM = "#064e3b"

# ── Status colors ─────────────────────────────────────────────────────────
STATUS_CONNECTED = "#34d399"
STATUS_OFFLINE_TEXT = "#fb7185"
STATUS_OFFLINE_BG = "#2a0a14"
STATUS_OFFLINE_BORDER = "#4c1324"
STATUS_WARNING_TEXT = "#fbbf24"
STATUS_WARNING_BG = "#1a1400"
STATUS_WARNING_BORDER = "#4c3a00"

# ── Extension badge colors ────────────────────────────────────────────────
EXT_BLUE = "#93c5fd"
EXT_BLUE_BG = "#172554"
EXT_GREEN = "#6ee7b7"
EXT_GREEN_BG = "#052e16"
EXT_PURPLE = "#c4b5fd"
EXT_PURPLE_BG = "#2e1065"
EXT_AMBER = "#fcd34d"
EXT_AMBER_BG = "#451a03"
EXT_YELLOW = "#fde047"
EXT_YELLOW_BG = "#422006"
EXT_DEFAULT = "#d4d4d8"
EXT_DEFAULT_BG = "#27272a"

# ── Fonts ─────────────────────────────────────────────────────────────────
# CustomTkinter will fall back through this tuple
FONT_FAMILY = ("Segoe UI Variable Display", "Inter", "Segoe UI", "sans-serif")
FONT_MONO = ("Cascadia Code", "JetBrains Mono", "Consolas", "monospace")

# ── Sizing ────────────────────────────────────────────────────────────────
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 650
CORNER_RADIUS = 12
CORNER_RADIUS_SM = 8
CORNER_RADIUS_XS = 6
PAD_LG = 24
PAD_MD = 16
PAD_SM = 10
PAD_XS = 6


def get_ext_colors(ext: str) -> tuple[str, str]:
    """Return (text_color, bg_color) for a file extension badge."""
    ext = ext.upper()

    if ext == "FOLDER":
        return EXT_YELLOW, EXT_YELLOW_BG

    blue_types = {"PDF", "DOC", "DOCX"}
    green_types = {"XLS", "XLSX", "CSV"}
    purple_types = {"PNG", "JPG", "JPEG", "SVG", "GIF"}
    code_types = {
        "PY", "JS", "TS", "TSX", "JSX", "HTML", "CSS",
        "JSON", "RS", "GO", "CPP", "C", "CS", "SH",
    }

    if ext in blue_types:
        return EXT_BLUE, EXT_BLUE_BG
    if ext in green_types:
        return EXT_GREEN, EXT_GREEN_BG
    if ext in purple_types:
        return EXT_PURPLE, EXT_PURPLE_BG
    if ext in code_types:
        return EXT_AMBER, EXT_AMBER_BG

    return EXT_DEFAULT, EXT_DEFAULT_BG
