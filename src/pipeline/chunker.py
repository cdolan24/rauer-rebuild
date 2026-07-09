from __future__ import annotations

import re
from dataclasses import dataclass

from src.pipeline.pdf_extractor import ExtractedDocument

_PARAGRAPH_RE = re.compile(r"\n\s*\n")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    page_start: int
    page_end: int


@dataclass
class _Unit:
    page_number: int
    text: str
    section: str | None = None


def _split_page_into_units(
    page_number: int, text: str, max_unit_size: int, section: str | None = None
) -> list[_Unit]:
    """Split a page's text into paragraph- or sentence-level units."""
    units: list[_Unit] = []
    for para in _PARAGRAPH_RE.split(text):
        para = para.strip()
        if not para:
            continue
        if len(para) <= max_unit_size:
            units.append(_Unit(page_number, para, section))
            continue
        for sentence in _SENTENCE_RE.split(para):
            sentence = sentence.strip()
            if sentence:
                units.append(_Unit(page_number, sentence, section))
    return units


def chunk_document(
    document: ExtractedDocument,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
) -> list[Chunk]:
    """Split an extracted document into overlapping chunks with page metadata.

    Chunks are built by greedily combining paragraph/sentence-level units
    (in document order) up to ``chunk_size`` characters, carrying the
    trailing ``chunk_overlap`` characters of units forward into the next
    chunk so context isn't lost at chunk boundaries. Each chunk's
    ``page_start``/``page_end`` span the pages its constituent units came from.

    When a page's detected ``section`` (e.g. a story/chapter title, from a
    running page header - see pdf_extractor.py) differs from the previous
    page's, that's treated as a hard break: the in-progress chunk is flushed
    without carrying overlap forward, so a chunk never blends the tail of one
    story with the start of the next. Pages with no detected section (most of
    a rules-heavy sourcebook) don't trigger this - chunking falls back to
    size-based splitting exactly as before for that content.
    """
    all_units: list[_Unit] = []
    for page in document.pages:
        all_units.extend(
            _split_page_into_units(page.page_number, page.text, chunk_size, page.section)
        )

    if not all_units:
        return []

    chunks: list[Chunk] = []
    current: list[_Unit] = []
    current_len = 0

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        text = " ".join(u.text for u in current)
        page_start = min(u.page_number for u in current)
        page_end = max(u.page_number for u in current)
        chunk_id = f"{document.document_id}_chunk_{len(chunks):04d}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=document.document_id,
                text=text,
                page_start=page_start,
                page_end=page_end,
            )
        )

    current_section: str | None = None

    for unit in all_units:
        unit_len = len(unit.text) + 1
        crosses_section = (
            current
            and current_section is not None
            and unit.section is not None
            and unit.section != current_section
        )
        if crosses_section:
            # A detected story/chapter boundary - flush without carrying
            # overlap forward, so the new chunk doesn't open with trailing
            # text from the story that just ended.
            flush()
            current = []
            current_len = 0
        elif current and current_len + unit_len > chunk_size:
            flush()
            # Carry trailing units forward as overlap context.
            overlap_units: list[_Unit] = []
            overlap_len = 0
            for u in reversed(current):
                extra = len(u.text) + 1
                if overlap_len + extra > chunk_overlap:
                    break
                overlap_units.insert(0, u)
                overlap_len += extra
            current = overlap_units
            current_len = overlap_len

        current.append(unit)
        current_len += unit_len
        if unit.section is not None:
            current_section = unit.section

    flush()
    return chunks
