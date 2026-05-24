from __future__ import annotations

import re


DEFAULT_CHUNK_SIZE = 1_400
DEFAULT_OVERLAP = 180


def chunk_text(
    text: str,
    *,
    source: str,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> list[dict]:
    clean = _normalize_text(text)
    if not clean:
        return []

    chunks: list[dict] = []
    for section_title, section_text in _split_sections(clean):
        chunks.extend(
            _chunk_section(
                section_text,
                source=source,
                section_title=section_title,
                chunk_start_index=len(chunks),
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )
    return chunks


def _chunk_section(
    text: str,
    *,
    source: str,
    section_title: str | None,
    chunk_start_index: int,
    chunk_size: int,
    overlap: int,
) -> list[dict]:
    chunks: list[dict] = []
    start = 0
    chunk_index = chunk_start_index

    while start < len(text):
        end = min(start + chunk_size, len(text))
        if end < len(text):
            paragraph_break = text.rfind("\n\n", start, end)
            sentence_break = text.rfind(". ", start, end)
            best_break = max(paragraph_break, sentence_break)
            if best_break > start + int(chunk_size * 0.55):
                end = best_break + 1

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(
                {
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                    "source": source,
                    "metadata": {"section": section_title} if section_title else {},
                }
            )
            chunk_index += 1

        if end >= len(text):
            break
        start = max(0, end - overlap)

    return chunks


def _split_sections(text: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    current_title: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        title = _section_title(line)
        if title and current_lines:
            sections.append((current_title, "\n".join(current_lines).strip()))
            current_lines = [line]
            current_title = title
        else:
            if title:
                current_title = title
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return [(title, body) for title, body in sections if body]


def _section_title(line: str) -> str | None:
    clean = line.strip()
    if not clean:
        return None
    if clean.startswith("FILE: "):
        return clean
    if clean.startswith("#"):
        return clean.lstrip("#").strip() or None
    if len(clean) <= 80 and re.match(r"^[A-Z][A-Za-z0-9 &/().:_-]+$", clean):
        return clean
    return None


def _normalize_text(text: str) -> str:
    return re.sub(r"\n{3,}", "\n\n", text.strip())
