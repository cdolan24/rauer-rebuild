from __future__ import annotations

import fitz

from tests.conftest import TEST_ADMIN_PASSWORD


def _make_pdf_bytes(page_texts: list[str]) -> bytes:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_upload_then_chat_yields_cited_answer(api_client):
    """Full user-facing flow: upload a PDF, then ask a question about it and
    get back an answer grounded in, and cited to, that document."""
    pdf_bytes = _make_pdf_bytes(
        [
            "Aragorn is a ranger who protects travelers on the road near Bree.",
            "Bree is a small town where many travelers stop to rest.",
        ]
    )

    upload_response = api_client.post(
        "/api/documents/upload",
        files={"file": ("story.pdf", pdf_bytes, "application/pdf")},
        data={"admin_password": TEST_ADMIN_PASSWORD},
    )
    assert upload_response.status_code == 202
    document_id = upload_response.json()["document_id"]

    # Background ingestion runs synchronously under TestClient, so by the
    # time upload responds the document should already be processed.
    detail = api_client.get(f"/api/documents/{document_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "processed"

    chat_response = api_client.post(
        "/api/chat", json={"message": "Who is Aragorn?", "conversation_id": "e2e-conv"}
    )
    assert chat_response.status_code == 200
    data = chat_response.json()

    assert data["response"]
    assert len(data["sources"]) > 0
    assert all(s["document_id"] == document_id for s in data["sources"])

    # The document viewer's content endpoint should serve back what was ingested.
    content_response = api_client.get(f"/api/documents/{document_id}/content")
    assert content_response.status_code == 200
    assert "Aragorn" in content_response.json()["content"]


def test_question_with_no_ingested_documents_falls_back_gracefully(api_client):
    response = api_client.post(
        "/api/chat", json={"message": "Who is Aragorn?", "conversation_id": "e2e-empty"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["sources"] == []
    assert "don't have information" in data["response"]
