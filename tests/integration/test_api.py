from __future__ import annotations

import fitz

from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddedChunk

# api_client / unhealthy_api_client fixtures come from tests/conftest.py


def test_health_endpoint_healthy(api_client):
    response = api_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["ollama"] == "connected"


def test_health_endpoint_ollama_unreachable(unhealthy_api_client):
    response = unhealthy_api_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["ollama"] == "unreachable"


def test_list_documents_empty(api_client):
    response = api_client.get("/api/documents")

    assert response.status_code == 200
    assert response.json() == {"documents": []}


def _seed_document(client, document_id="fellowship"):
    fake_client = client.app.state.ollama_client
    chunk = Chunk(
        chunk_id="c0",
        document_id=document_id,
        text="Aragorn is a ranger who protects travelers near Bree.",
        page_start=3,
        page_end=3,
    )
    embedded = EmbeddedChunk(chunk=chunk, embedding=fake_client.embed("fake-embed", chunk.text))
    client.app.state.vector_store.add_chunks([embedded])
    client.app.state.registry.mark_processed(document_id, document_id, f"{document_id}.pdf", 5, 1)

    processed_dir = client.app.state.config.paths.processed_dir
    from pathlib import Path

    Path(processed_dir).mkdir(parents=True, exist_ok=True)
    (Path(processed_dir) / f"{document_id}.txt").write_text("--- page 3 ---\nAragorn text.\n")


def test_chat_endpoint_returns_grounded_answer_with_sources(api_client):
    _seed_document(api_client)

    response = api_client.post(
        "/api/chat", json={"message": "Who is Aragorn?", "conversation_id": "conv-1"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["conversation_id"] == "conv-1"
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_id"] == "fellowship"


def test_conversation_history_roundtrip(api_client):
    _seed_document(api_client)
    api_client.post("/api/chat", json={"message": "Who is Aragorn?", "conversation_id": "conv-2"})

    history = api_client.get("/api/conversations/conv-2")
    assert history.status_code == 200
    assert len(history.json()["messages"]) == 2  # user + assistant

    cleared = api_client.delete("/api/conversations/conv-2")
    assert cleared.status_code == 200

    history_after = api_client.get("/api/conversations/conv-2")
    assert history_after.json()["messages"] == []


def test_search_endpoint(api_client):
    _seed_document(api_client)

    response = api_client.post("/api/search", json={"query": "Who is Aragorn?", "limit": 5})

    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["document_id"] == "fellowship"


def test_get_document_and_content(api_client):
    _seed_document(api_client)

    detail = api_client.get("/api/documents/fellowship")
    assert detail.status_code == 200
    assert detail.json()["status"] == "processed"

    content = api_client.get("/api/documents/fellowship/content")
    assert content.status_code == 200
    assert "Aragorn text" in content.json()["content"]


def test_get_document_not_found(api_client):
    response = api_client.get("/api/documents/does-not-exist")
    assert response.status_code == 404


def test_get_document_content_not_found_when_not_ingested(api_client):
    response = api_client.get("/api/documents/does-not-exist/content")
    assert response.status_code == 404


def test_get_document_content_not_found_when_processed_file_missing(api_client):
    # Registered as processed, but no processed/<id>.txt was ever written.
    api_client.app.state.registry.mark_processed("ghost", "ghost", "ghost.pdf", 1, 1)

    response = api_client.get("/api/documents/ghost/content")

    assert response.status_code == 404


def test_unhandled_exception_returns_500(api_client, monkeypatch):
    from fastapi.testclient import TestClient

    def _boom(self, conversation_id, message):
        raise RuntimeError("boom")

    monkeypatch.setattr(type(api_client.app.state.chat_engine), "ask", _boom)

    # Default TestClient re-raises server exceptions (for debuggability);
    # disable that to exercise our actual exception handler.
    non_raising_client = TestClient(api_client.app, raise_server_exceptions=False)
    response = non_raising_client.post(
        "/api/chat", json={"message": "hello", "conversation_id": "conv-err"}
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}


def _make_pdf_bytes(page_texts: list[str]) -> bytes:
    doc = fitz.open()
    for text in page_texts:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    data = doc.tobytes()
    doc.close()
    return data


def test_upload_document_ingests_via_background_task(api_client):
    pdf_bytes = _make_pdf_bytes(["Aragorn walked into Bree."])

    response = api_client.post(
        "/api/documents/upload",
        files={"file": ("uploaded_story.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 202
    document_id = response.json()["document_id"]
    assert document_id == "uploaded_story"

    detail = api_client.get(f"/api/documents/{document_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "processed"
