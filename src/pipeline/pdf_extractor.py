from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be opened or parsed."""


@dataclass
class ExtractedPage:
    page_number: int  # 1-indexed
    text: str


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
            pages.append(ExtractedPage(page_number=i, text=text))
    finally:
        doc.close()

    return ExtractedDocument(
        document_id=pdf_path.stem,
        title=pdf_path.stem,
        source_path=str(pdf_path),
        pages=pages,
    )
