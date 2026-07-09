from __future__ import annotations

import fitz
import pytest

from src.pipeline.pdf_extractor import PDFExtractionError, _detect_section, extract_pdf


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


def test_detect_section_finds_running_header():
    assert _detect_section("M1E Core • Snow on a Tombstone\nSome story text.") == (
        "Snow on a Tombstone"
    )


def test_detect_section_returns_none_without_a_header():
    assert _detect_section("Just some regular rules text with no running header.") is None


def test_detect_section_ignores_a_table_of_contents_dot_leader_line():
    # Regression test: a TOC entry like "M1E Core.................." (dots as
    # a leader, no bullet, nothing meaningful after it) previously matched
    # because \W+ includes newlines - it would consume the leader dots AND
    # the line break, capturing the *next*, unrelated TOC line as a bogus
    # title.
    toc_text = "M1E Core...........................................\nThe Breach, \n\t A History of Malifaux....................."
    assert _detect_section(toc_text) is None


def test_extract_pdf_populates_section_from_a_repeated_running_header(tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(
        pdf_path,
        [
            "M1E Core • Snow on a Tombstone\nPage one of the story.",
            "M1E Core • Snow on a Tombstone\nPage two of the story.",
            "Plain rules text.",
        ],
    )

    document = extract_pdf(pdf_path)

    assert document.pages[0].section == "Snow on a Tombstone"
    assert document.pages[1].section == "Snow on a Tombstone"
    assert document.pages[2].section is None


def test_extract_pdf_ignores_a_one_off_header_like_match(tmp_path):
    # A cover page's "<Edition> Core • <book subtitle>" line is
    # syntactically identical to a real running header but never repeats -
    # shouldn't be treated as a section.
    pdf_path = tmp_path / "sample.pdf"
    _make_pdf(
        pdf_path,
        ["M1E Core • Rising Powers, Twisting Fates\nCover page.", "Plain rules text."],
    )

    document = extract_pdf(pdf_path)

    assert document.pages[0].section is None
