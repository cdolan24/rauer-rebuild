from __future__ import annotations

import fitz

from src.pipeline.image_extractor import describe_image_heavy_pages
from src.pipeline.pdf_extractor import extract_pdf
from src.utils.ollama_client import OllamaError


class ScriptedVisionClient:
    def __init__(self, description: str = "A description of the page.") -> None:
        self.description = description
        self.calls = 0
        self.received_images: list[list[str]] = []

    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        self.calls += 1
        self.received_images.append(messages[-1].get("images", []))
        return self.description


class FailingVisionClient:
    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        raise OllamaError("simulated vision failure")


def _make_image_bytes() -> bytes:
    src = fitz.open()
    src.new_page()
    data = src[0].get_pixmap().tobytes("png")
    src.close()
    return data


def _make_pdf_with_image_heavy_page(path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_image(fitz.Rect(0, 0, page.rect.width, page.rect.height * 0.9), stream=_make_image_bytes())
    doc.save(str(path))
    doc.close()


def _make_prose_pdf(path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 545, 792), "A perfectly ordinary paragraph of story text.")
    doc.save(str(path))
    doc.close()


def test_describe_image_heavy_pages_replaces_text_for_flagged_pages(tmp_path):
    pdf_path = tmp_path / "comic.pdf"
    _make_pdf_with_image_heavy_page(pdf_path)
    document = extract_pdf(pdf_path)
    assert document.pages[0].is_image_heavy is True
    client = ScriptedVisionClient("A knight stands before a castle.")

    result = describe_image_heavy_pages(str(pdf_path), document, client, "fake-vision")

    assert result.pages[0].text == "A knight stands before a castle."
    assert result.pages[0].source_type == "visual"
    assert client.calls == 1
    assert client.received_images[0]  # a base64 image was actually sent


def test_describe_image_heavy_pages_leaves_prose_pages_untouched(tmp_path):
    pdf_path = tmp_path / "prose.pdf"
    _make_prose_pdf(pdf_path)
    document = extract_pdf(pdf_path)
    assert document.pages[0].is_image_heavy is False
    original_text = document.pages[0].text
    client = ScriptedVisionClient()

    result = describe_image_heavy_pages(str(pdf_path), document, client, "fake-vision")

    assert result.pages[0].text == original_text
    assert result.pages[0].source_type == "text"
    assert client.calls == 0  # never sent to the vision model at all


def test_describe_image_heavy_pages_keeps_original_text_on_failure(tmp_path):
    pdf_path = tmp_path / "comic.pdf"
    _make_pdf_with_image_heavy_page(pdf_path)
    document = extract_pdf(pdf_path)
    original_text = document.pages[0].text
    client = FailingVisionClient()

    result = describe_image_heavy_pages(str(pdf_path), document, client, "fake-vision")

    assert result.pages[0].text == original_text  # unchanged, not an empty/error string
    assert result.pages[0].source_type == "text"  # never marked visual since it was never described
