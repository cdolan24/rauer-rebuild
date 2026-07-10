from __future__ import annotations

import base64
from dataclasses import replace

import fitz

from src.pipeline.pdf_extractor import ExtractedDocument
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaClient, OllamaError

logger = get_logger(__name__)

_VISION_SYSTEM_PROMPT = (
    "You are describing a page from a comic-style or heavily-illustrated document "
    "for someone who cannot see it. Describe the scene, characters, and setting "
    "shown, and transcribe any legible dialogue, captions, or text. If some text "
    "isn't clearly legible, say so rather than guessing at it."
)


def describe_image_heavy_pages(
    pdf_path: str, document: ExtractedDocument, ollama_client: OllamaClient, vision_model: str
) -> ExtractedDocument:
    """Return a new document where every page flagged `is_image_heavy` has its
    (likely near-empty) extracted text replaced with a vision model's
    description of that page - only those pages are ever sent to the vision
    model; pages with substantial extracted text are left untouched.

    Never raises OllamaError - a page that fails to describe just keeps its
    original extracted text, same as if this function were never called."""
    flagged_numbers = {p.page_number for p in document.pages if p.is_image_heavy}
    if not flagged_numbers:
        return document

    doc = fitz.open(pdf_path)
    try:
        descriptions: dict[int, str] = {}
        for page_number in sorted(flagged_numbers):
            page = doc[page_number - 1]
            image_b64 = base64.b64encode(page.get_pixmap().tobytes("png")).decode()
            messages = [
                {"role": "system", "content": _VISION_SYSTEM_PROMPT},
                {"role": "user", "content": "Describe this page.", "images": [image_b64]},
            ]
            try:
                descriptions[page_number] = ollama_client.chat(vision_model, messages)
            except OllamaError as e:
                logger.warning(
                    "Vision description failed for page %d of %s, keeping extracted text: %s",
                    page_number, pdf_path, e,
                )
    finally:
        doc.close()

    if not descriptions:
        return document

    new_pages = [
        replace(page, text=descriptions[page.page_number], source_type="visual")
        if page.page_number in descriptions
        else page
        for page in document.pages
    ]
    logger.info("Described %d image-heavy page(s) for %s", len(descriptions), pdf_path)
    return replace(document, pages=new_pages)
