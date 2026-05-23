from pathlib import Path
from .config import get_settings
from .extractors import extract_text
from .folder_scanner import scan_folder


def collect_context(raw_path: str) -> dict:
    selected = Path(raw_path).expanduser().resolve()
    if not selected.exists():
        raise FileNotFoundError(f"Path does not exist: {selected}")

    if selected.is_dir():
        return _collect_folder_context(selected)

    return _collect_file_context(selected)


def _collect_file_context(path: Path) -> dict:
    settings = get_settings()
    text = extract_text(path, max_chars=settings.max_file_chars)
    preview = text[:4_000] if text else ""

    return {
        "path": str(path),
        "kind": "file",
        "name": path.name,
        "summary": f"File: {path.name} ({path.suffix or 'no extension'})",
        "sources": [str(path)],
        "text": text,
        "text_preview": preview,
    }


def _collect_folder_context(path: Path) -> dict:
    settings = get_settings()
    files = scan_folder(path, max_files=settings.max_folder_files)
    structure = "\n".join(item["relative_path"] for item in files)

    return {
        "path": str(path),
        "kind": "folder",
        "name": path.name,
        "summary": f"Folder: {path.name} with {len(files)} scanned files",
        "sources": [str(path / item["relative_path"]) for item in files[:25]],
        "text": structure,
        "text_preview": structure[:4_000],
        "files": files,
    }

