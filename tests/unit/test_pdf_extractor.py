from __future__ import annotations

import fitz
import pytest

from src.pipeline.pdf_extractor import PDFExtractionError, extract_pdf


def _make_pdf(path, page_texts: list[str]) -> None:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_extract_pdf_returns_page_per_page(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(pdf_path, ["Page one text.", "Page two text."])

    document = extract_pdf(pdf_path)

    assert document.document_id == "sample"
    assert document.page_count == 2
    assert document.pages[0].page_number == 1
    assert "Page one" in document.pages[0].text
    assert document.pages[1].page_number == 2
    assert "Page two" in document.pages[1].text


def test_extract_pdf_missing_file_raises(tmp_path):
    with pytest.raises(PDFExtractionError):
        extract_pdf(tmp_path / "does_not_exist.pdf")


def test_extract_pdf_corrupted_file_raises(tmp_path):
    bad_pdf = tmp_path / "corrupted.pdf"
    bad_pdf.write_bytes(b"not a real pdf file")

    with pytest.raises(PDFExtractionError):
        extract_pdf(bad_pdf)
