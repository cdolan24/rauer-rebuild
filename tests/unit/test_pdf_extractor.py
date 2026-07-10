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


def _make_image_bytes() -> bytes:
    src = fitz.open()
    src.new_page()
    pix = src[0].get_pixmap()
    data = pix.tobytes("png")
    src.close()
    return data


def _make_pdf_with_image_page(path, *, image_rect_fraction: float, text: str = "") -> None:
    """A single-page PDF with a real embedded image covering roughly
    `image_rect_fraction` of the page area, plus optional text."""
    doc = fitz.open()
    page = doc.new_page()
    if text:
        # insert_textbox wraps within the given rect, unlike insert_text
        # (which draws a single unwrapped line and clips at the page edge).
        page.insert_textbox(fitz.Rect(50, 50, page.rect.width - 50, page.rect.height - 50), text)
    width, height = page.rect.width, page.rect.height
    side_fraction = image_rect_fraction**0.5
    w, h = width * side_fraction, height * side_fraction
    rect = fitz.Rect(0, 0, w, h)
    page.insert_image(rect, stream=_make_image_bytes())
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


def test_extract_pdf_flags_a_large_image_with_no_text_as_image_heavy(tmp_path):
    pdf_path = tmp_path / "comic.pdf"
    _make_pdf_with_image_page(pdf_path, image_rect_fraction=0.9)

    document = extract_pdf(pdf_path)

    assert document.pages[0].is_image_heavy is True


def test_extract_pdf_does_not_flag_a_normal_prose_page(tmp_path):
    pdf_path = tmp_path / "prose.pdf"
    _make_pdf(pdf_path, ["A perfectly ordinary paragraph of story text, nothing visual about it."])

    document = extract_pdf(pdf_path)

    assert document.pages[0].is_image_heavy is False


def test_extract_pdf_does_not_flag_a_page_with_a_large_image_and_substantial_text(tmp_path):
    # A large decorative illustration alongside real prose still has real,
    # citable content - shouldn't be treated as image-heavy just because it
    # also has a big picture on it.
    pdf_path = tmp_path / "illustrated.pdf"
    long_text = " ".join(f"Sentence number {i} of real story prose." for i in range(30))
    _make_pdf_with_image_page(pdf_path, image_rect_fraction=0.9, text=long_text)

    document = extract_pdf(pdf_path)

    assert document.pages[0].is_image_heavy is False


def test_extract_pdf_does_not_flag_a_small_incidental_image(tmp_path):
    pdf_path = tmp_path / "small_image.pdf"
    _make_pdf_with_image_page(pdf_path, image_rect_fraction=0.05)

    document = extract_pdf(pdf_path)

    assert document.pages[0].is_image_heavy is False
