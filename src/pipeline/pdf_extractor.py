from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened or parsed."""


# Matches a running page header of the form "<Edition> Core <sep> <Title>"
# (e.g. "M1E Core • Snow on a Tombstone") - the pattern Wyrd's Malifaux
# sourcebooks repeat on every page of a given story/chapter. Not tied to a
# specific edition name, so it applies to any similarly-formatted sourcebook,
# not just the two documents this project ships with. The separator is
# restricted to non-word, non-newline, non-period characters (real headers
# use a bullet like "•"): this deliberately does NOT match a table-of-contents
# line like "M1E Core..........................", where the trailing dots are
# just a leader and there's no real title on that line - without this
# restriction, \W+ (which includes \n) would happily consume the leader dots
# and the line break and capture the *next* TOC entry as a bogus "title".
_RUNNING_HEADER_RE = re.compile(r"^\s*\S+\s+Core[^\w\n.]+(.+?)\s*$", re.MULTILINE)

# A genuine running header repeats across every page of a story; a one-off
# coincidental match (e.g. a cover page's "<Edition> Core • <book subtitle>"
# line, which is syntactically identical but never repeats) shouldn't be
# treated as a section - require it to appear on at least this many pages.
_MIN_SECTION_PAGE_COUNT = 2


def _detect_section(text: str) -> str | None:
    """Best-effort detection of which story/chapter a page belongs to, from
    its running header. Returns None if no such header is found (most pages
    of a rules-heavy sourcebook won't have one - that's fine, it just means
    chunking can't use this signal for that page)."""
    match = _RUNNING_HEADER_RE.search(text)
    return match.group(1).strip() if match else None


# A page counts as "image-heavy" (comic panel, illustration-dominated, etc.)
# only if its embedded images cover a large fraction of the page AND it has
# little real extracted text - a prose page with a large decorative
# illustration alongside a full column of text still has real, citable
# content and shouldn't be treated any differently. These are reasoned
# starting defaults, not tuned against real comic-style PDFs (none exist in
# this repo to calibrate against) - verified against synthetic pages only.
IMAGE_COVERAGE_THRESHOLD = 0.4
MAX_TEXT_CHARS_FOR_IMAGE_HEAVY = 200


def _analyze_image_coverage(page: fitz.Page, text: str) -> bool:
    """Deterministic, non-LLM heuristic: does this page's embedded-image
    coverage and text sparsity suggest most of its content is visual rather
    than textual?"""
    page_area = page.rect.width * page.rect.height
    if page_area <= 0:
        return False

    covered_area = 0.0
    for image_info in page.get_image_info():
        bbox = image_info.get("bbox")
        if not bbox:
            continue
        x0, y0, x1, y1 = bbox
        covered_area += max(0.0, x1 - x0) * max(0.0, y1 - y0)

    coverage_ratio = min(1.0, covered_area / page_area)
    return coverage_ratio >= IMAGE_COVERAGE_THRESHOLD and len(text.strip()) <= MAX_TEXT_CHARS_FOR_IMAGE_HEAVY


@dataclass
class ExtractedPage:
    page_number: int  # 1-indexed
    text: str
    section: str | None = None  # best-effort story/chapter title, if detected
    is_image_heavy: bool = False  # little extracted text, large embedded-image coverage
    # "text" (get_text() output, however sparse) or "visual" (a vision model
    # actually replaced this page's text with a description - see
    # image_extractor.py). is_image_heavy only means "flagged as a candidate
    # for vision description" - source_type reflects what the text actually
    # is, which stays "text" if vision description was never run or failed.
    source_type: str = "text"


@dataclass
class ExtractedDocument:
    document_id: str
    title: str
    source_path: str
    pages: list[ExtractedPage]

    @property
    def page_count(self) -> int:
        return len(self.pages)


def extract_pdf(path: str | Path) -> ExtractedDocument:
    """Extract per-page text from a PDF file.

    Args:
        path: Path to the PDF file.

    Returns:
        ExtractedDocument with one ExtractedPage per page (1-indexed).

    Raises:
        PDFExtractionError: if the file doesn't exist or can't be parsed.
    """
    pdf_path = Path(path)
    if not pdf_path.exists():
        raise PDFExtractionError(f"PDF file not found: {pdf_path}")

    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise PDFExtractionError(f"Failed to open PDF '{pdf_path}': {e}") from e

    try:
        pages = []
        for i, page in enumerate(doc, start=1):
            try:
                text = page.get_text()
            except Exception as e:
                raise PDFExtractionError(
                    f"Failed to extract text from page {i} of '{pdf_path}': {e}"
                ) from e
            is_image_heavy = _analyze_image_coverage(page, text)
            pages.append(
                ExtractedPage(
                    page_number=i, text=text, section=_detect_section(text), is_image_heavy=is_image_heavy
                )
            )
    finally:
        doc.close()

    section_counts = Counter(p.section for p in pages if p.section is not None)
    for page in pages:
        if page.section is not None and section_counts[page.section] < _MIN_SECTION_PAGE_COUNT:
            page.section = None

    return ExtractedDocument(
        document_id=pdf_path.stem,
        title=pdf_path.stem,
        source_path=str(pdf_path),
        pages=pages,
    )
