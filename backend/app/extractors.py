from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET


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
    ".log",
    ".xml",
    ".sql",
    ".java",
    ".c",
    ".cpp",
    ".cs",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".sh",
    ".bat",
    ".ps1",
}


def extract_text(path: Path, max_chars: int = 120_000) -> str:
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(path, max_chars)

    if suffix == ".docx":
        return _extract_docx(path, max_chars)

    if suffix == ".pptx":
        return _extract_pptx(path, max_chars)

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


def _extract_docx(path: Path, max_chars: int) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile, OSError):
        return "[Could not extract text from this DOCX file.]"

    return _xml_text(xml)[:max_chars]


def _extract_pptx(path: Path, max_chars: int) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            slide_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
            )
            slides = []
            for index, name in enumerate(slide_names, start=1):
                text = _xml_text(archive.read(name))
                if text:
                    slides.append(f"Slide {index}:\n{text}")
                if sum(len(slide) for slide in slides) >= max_chars:
                    break
    except (zipfile.BadZipFile, OSError):
        return "[Could not extract text from this PPTX file.]"

    return "\n\n".join(slides)[:max_chars]


def _xml_text(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""

    parts = [node.text.strip() for node in root.iter() if node.text and node.text.strip()]
    return "\n".join(parts)
