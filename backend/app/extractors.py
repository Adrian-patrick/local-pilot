from pathlib import Path


TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".css",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".csv",
}


def extract_text(path: Path, max_chars: int = 120_000) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(path, max_chars)

    if suffix in TEXT_EXTENSIONS:
        return _read_text(path, max_chars)

    return f"[Unsupported file type for text extraction: {suffix or 'unknown'}]"


def _read_text(path: Path, max_chars: int) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1252"):
        try:
            return path.read_text(encoding=encoding, errors="replace")[:max_chars]
        except UnicodeDecodeError:
            continue
    return path.read_text(errors="replace")[:max_chars]


def _extract_pdf(path: Path, max_chars: int) -> str:
    try:
        import fitz
    except ImportError:
        return "[PDF extraction requires PyMuPDF. Install requirements.txt first.]"

    chunks: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            chunks.append(page.get_text())
            if sum(len(chunk) for chunk in chunks) >= max_chars:
                break
    return "\n".join(chunks)[:max_chars]

