from pathlib import Path
import re
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

    if suffix == ".xlsx":
        return _extract_xlsx(path, max_chars)

    if suffix == ".rtf":
        return _extract_rtf(path, max_chars)

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


def _extract_xlsx(path: Path, max_chars: int) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            shared_strings = _xlsx_shared_strings(archive)
            sheet_names = sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")
            )
            sheets = []
            for index, name in enumerate(sheet_names, start=1):
                text = _xlsx_sheet_text(archive.read(name), shared_strings)
                if text:
                    sheets.append(f"Sheet {index}:\n{text}")
                if sum(len(sheet) for sheet in sheets) >= max_chars:
                    break
    except (zipfile.BadZipFile, OSError):
        return "[Could not extract text from this XLSX file.]"

    return "\n\n".join(sheets)[:max_chars]


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        xml = archive.read("xl/sharedStrings.xml")
    except KeyError:
        return []

    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    values = []
    for item in root:
        parts = [node.text or "" for node in item.iter() if node.text]
        values.append(" ".join(part.strip() for part in parts if part.strip()))
    return values


def _xlsx_sheet_text(xml_bytes: bytes, shared_strings: list[str]) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""

    rows = []
    for row in root.iter():
        if not row.tag.endswith("row"):
            continue
        cells = []
        for cell in row:
            if not cell.tag.endswith("c"):
                continue
            cell_type = cell.attrib.get("t")
            value_node = next((child for child in cell if child.tag.endswith("v")), None)
            if value_node is None or value_node.text is None:
                continue
            value = value_node.text.strip()
            if cell_type == "s" and value.isdigit():
                index = int(value)
                value = shared_strings[index] if index < len(shared_strings) else value
            if value:
                cells.append(value)
        if cells:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _extract_rtf(path: Path, max_chars: int) -> str:
    text = _read_text(path, max_chars * 2)
    text = re.sub(r"\\'[0-9a-fA-F]{2}", " ", text)
    text = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def _xml_text(xml_bytes: bytes) -> str:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return ""

    parts = [node.text.strip() for node in root.iter() if node.text and node.text.strip()]
    return "\n".join(parts)
