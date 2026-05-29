"""File metadata extraction, content parsing, and directory tree utilities.

Replaces the Rust backend functions from src-tauri/src/lib.rs:
  - get_file_metadata()
  - read_file_content()
  - build_dir_tree()
  - extract_docx()
  - extract_printable_strings()
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class FileMetadata:
    """Mirror of the Rust/TypeScript FileMetadata struct."""

    file_name: str
    full_path: str
    extension: str
    file_size: int
    last_modified: str
    is_dir: bool


def get_file_metadata(file_path: str) -> FileMetadata:
    """Extract metadata for a file or directory.

    Raises:
        FileNotFoundError: If the path does not exist.
        PermissionError: If we cannot stat the path.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {file_path}")

    stat = path.stat()
    is_dir = path.is_dir()

    file_name = path.name or str(path)
    full_path = str(path.resolve())
    extension = "FOLDER" if is_dir else (path.suffix.lstrip(".").upper() or "")
    file_size = 0 if is_dir else stat.st_size

    try:
        mtime = datetime.fromtimestamp(stat.st_mtime)
        last_modified = mtime.strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, ValueError):
        last_modified = "Unknown"

    return FileMetadata(
        file_name=file_name,
        full_path=full_path,
        extension=extension,
        file_size=file_size,
        last_modified=last_modified,
        is_dir=is_dir,
    )


# ---------------------------------------------------------------------------
# Directory tree builder (matches Rust build_dir_tree logic)
# ---------------------------------------------------------------------------

def _build_dir_tree(
    directory: Path,
    depth: int,
    max_depth: int,
    count: list[int],
    max_items: int,
) -> str:
    """Recursively build a textual directory tree.

    Uses a mutable list ``count`` as a counter so recursion can share state
    (mirrors the ``&mut usize`` in the Rust version).
    """
    if depth > max_depth or count[0] >= max_items:
        return ""

    tree = ""
    indent = "  " * depth

    try:
        entries = sorted(directory.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return f"{indent}[Permission denied]\n"

    for entry in entries:
        if count[0] >= max_items:
            tree += f"{indent}... (tree truncated, max {max_items} items reached)\n"
            break

        count[0] += 1
        name = entry.name

        if entry.is_dir():
            tree += f"{indent}- {name}/\n"
            tree += _build_dir_tree(entry, depth + 1, max_depth, count, max_items)
        else:
            tree += f"{indent}- {name}\n"

    return tree


# ---------------------------------------------------------------------------
# File content readers
# ---------------------------------------------------------------------------

def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        return "[PyMuPDF not installed — cannot parse PDF]"

    try:
        doc = fitz.open(str(path))
        text_parts: list[str] = []
        for page in doc:
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)
    except Exception as exc:
        return f"[Failed to parse PDF: {exc}]"


def _extract_docx_text(path: Path) -> str:
    """Extract text from a DOCX file using python-docx."""
    try:
        from docx import Document
    except ImportError:
        return "[python-docx not installed — cannot parse DOCX]"

    try:
        doc = Document(str(path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        return f"[Failed to parse DOCX: {exc}]"


def _extract_printable_strings(data: bytes, min_length: int = 4) -> str:
    """Extract runs of printable ASCII characters from binary data.

    Matches the Rust extract_printable_strings logic: characters 32–126,
    minimum run length of 4.
    """
    result: list[str] = []
    current: list[str] = []

    for byte in data:
        if 32 <= byte <= 126:
            current.append(chr(byte))
        else:
            if len(current) >= min_length:
                result.append("".join(current))
            current.clear()

    # Flush remaining
    if len(current) >= min_length:
        result.append("".join(current))

    return "\n".join(result)


def read_file_content(file_path: str) -> str:
    """Read and return the textual content of a file or directory tree.

    Handles:
      - Directories → tree structure
      - PDF → pymupdf extraction
      - DOCX → python-docx extraction
      - Text/code → raw read up to 100 KB
      - Binary → printable ASCII string extraction
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {file_path}")

    # --- Directories ---
    if path.is_dir():
        count = [0]
        tree = _build_dir_tree(path, depth=0, max_depth=3, count=count, max_items=100)
        return f"Directory Structure:\n{tree}"

    # --- PDF ---
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_text(path)

    # --- DOCX ---
    if ext == ".docx":
        return _extract_docx_text(path)

    # --- Generic files (text / binary) ---
    max_read = 12 * 1024  # 12 KB (~3-4k tokens) to ensure lightning fast responses

    try:
        with open(path, "rb") as f:
            data = f.read(max_read + 1)
    except PermissionError:
        return f"[Permission denied: {file_path}]"
    except OSError as exc:
        return f"[Failed to read file: {exc}]"

    if not data:
        return ""

    # Try UTF-8 decode
    try:
        text = data.decode("utf-8")
        if len(data) > max_read:
            # Truncate to max_read at a safe boundary
            truncated = text[:max_read]
            return (
                f"{truncated}\n\n"
                "[WARNING: File contents truncated to 12KB to ensure lightning-fast generation]"
            )
        return text
    except UnicodeDecodeError:
        # Binary file — extract printable strings
        strings = _extract_printable_strings(data)
        return f"[Binary file detected. Extracted readable strings:]\n{strings}"
