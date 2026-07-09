from __future__ import annotations

import json
import pathlib

import fitz

from src.pipeline.chunker import Chunk
from src.pipeline.embeddings import EmbeddedChunk
from tests.conftest import TEST_ADMIN_PASSWORD

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


def test_chat_endpoint_returns_503_when_ollama_unavailable(unhealthy_api_client):
    response = unhealthy_api_client.post(
        "/api/chat", json={"message": "Who is Aragorn?", "conversation_id": "conv-unhealthy"}
    )

    assert response.status_code == 503
    assert "Local LLM service unavailable" in response.json()["detail"]


def test_search_endpoint_returns_503_when_ollama_unavailable(unhealthy_api_client):
    response = unhealthy_api_client.post("/api/search", json={"query": "anything", "limit": 5})

    assert response.status_code == 503
    assert "Local LLM service unavailable" in response.json()["detail"]


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


def test_chat_stream_endpoint_yields_tokens_then_done_with_sources(api_client):
    _seed_document(api_client)

    with api_client.stream(
        "POST", "/api/chat/stream", json={"message": "Who is Aragorn?", "conversation_id": "conv-stream"}
    ) as response:
        assert response.status_code == 200
        events = [
            json.loads(line[len("data: "):])
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    token_events = [e for e in events if e["type"] == "token"]
    done_events = [e for e in events if e["type"] == "done"]
    assert len(token_events) > 1  # actually streamed, not one giant chunk
    assert len(done_events) == 1
    assert done_events[0]["sources"][0]["document_id"] == "fellowship"


def test_chat_stream_endpoint_503_when_ollama_unavailable(unhealthy_api_client):
    with unhealthy_api_client.stream(
        "POST", "/api/chat/stream", json={"message": "Who is Aragorn?", "conversation_id": "conv-stream"}
    ) as response:
        events = [
            json.loads(line[len("data: "):])
            for line in response.iter_lines()
            if line.startswith("data: ")
        ]

    assert len(events) == 1
    assert events[0]["type"] == "error"
    assert "Local LLM service unavailable" in events[0]["detail"]


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


def test_get_document_pdf_serves_the_real_file(api_client, tmp_path):
    doc = fitz.open()
    doc.new_page()
    pdf_path = tmp_path / "fellowship.pdf"
    doc.save(str(pdf_path))
    doc.close()

    api_client.app.state.registry.mark_processed("fellowship", "fellowship", str(pdf_path), 1, 0)

    response = api_client.get("/api/documents/fellowship/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content == pdf_path.read_bytes()
    # Must render inline (in the frontend's iframe viewer), not force a download.
    assert response.headers["content-disposition"].startswith("inline")


def test_get_document_pdf_404_for_unknown_document(api_client):
    response = api_client.get("/api/documents/does-not-exist/pdf")
    assert response.status_code == 404


def test_get_document_pdf_404_when_file_missing_on_disk(api_client):
    api_client.app.state.registry.mark_processed(
        "ghost", "ghost", "path/that/does/not/exist.pdf", 1, 0
    )

    response = api_client.get("/api/documents/ghost/pdf")

    assert response.status_code == 404


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
        data={"admin_password": TEST_ADMIN_PASSWORD},
    )

    assert response.status_code == 202
    document_id = response.json()["document_id"]
    assert document_id == "uploaded_story"

    detail = api_client.get(f"/api/documents/{document_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "processed"


def test_verify_admin_password_succeeds_with_correct_password(api_client):
    response = api_client.post("/api/auth/verify", json={"admin_password": TEST_ADMIN_PASSWORD})

    assert response.status_code == 200
    assert response.json() == {"valid": True}


def test_verify_admin_password_rejects_wrong_password(api_client):
    response = api_client.post("/api/auth/verify", json={"admin_password": "not-the-right-password"})

    assert response.status_code == 401


def test_repeated_wrong_passwords_lock_out_even_the_correct_password(api_client):
    for _ in range(5):
        api_client.post("/api/auth/verify", json={"admin_password": "not-the-right-password"})

    response = api_client.post("/api/auth/verify", json={"admin_password": TEST_ADMIN_PASSWORD})

    assert response.status_code == 401
    assert "Too many failed attempts" in response.json()["detail"]


def test_admin_query_runs_select_with_correct_password(api_client):
    _seed_document(api_client)

    response = api_client.post(
        "/api/admin/query",
        json={"admin_password": TEST_ADMIN_PASSWORD, "sql": "SELECT document_id, status FROM documents"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["columns"] == ["document_id", "status"]
    assert ["fellowship", "processed"] in data["rows"]
    assert data["rows_affected"] is None


def test_admin_query_returns_affected_row_count_for_non_select(api_client):
    _seed_document(api_client)

    response = api_client.post(
        "/api/admin/query",
        json={
            "admin_password": TEST_ADMIN_PASSWORD,
            "sql": "UPDATE documents SET status = 'processed' WHERE document_id = 'fellowship'",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["rows_affected"] == 1
    assert data["columns"] == []
    assert data["rows"] == []


def test_admin_query_rejects_wrong_password(api_client):
    response = api_client.post(
        "/api/admin/query",
        json={"admin_password": "not-the-right-password", "sql": "SELECT 1"},
    )

    assert response.status_code == 401


def test_admin_query_locks_out_after_repeated_wrong_passwords(api_client):
    for _ in range(5):
        api_client.post(
            "/api/admin/query",
            json={"admin_password": "not-the-right-password", "sql": "SELECT 1"},
        )

    response = api_client.post(
        "/api/admin/query",
        json={"admin_password": TEST_ADMIN_PASSWORD, "sql": "SELECT 1"},
    )

    assert response.status_code == 401
    assert "Too many failed attempts" in response.json()["detail"]


def test_admin_query_returns_400_for_invalid_sql(api_client):
    response = api_client.post(
        "/api/admin/query",
        json={"admin_password": TEST_ADMIN_PASSWORD, "sql": "NOT VALID SQL"},
    )

    assert response.status_code == 400


def test_verify_admin_password_rejects_when_none_configured(tmp_path, monkeypatch):
    import src.api.main as main_module
    from fastapi.testclient import TestClient
    from tests.conftest import FakeOllamaClient, write_test_config

    config_path = write_test_config(tmp_path)
    config_file = pathlib.Path(config_path)
    config_file.write_text(
        config_file.read_text(encoding="utf-8").replace(
            f'admin_password: "{TEST_ADMIN_PASSWORD}"', 'admin_password: "changeme"'
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("BUDDHARAUER_CONFIG", config_path)
    monkeypatch.setattr(main_module, "OllamaClient", lambda base_url, timeout=60.0: FakeOllamaClient())

    app = main_module.create_app()
    with TestClient(app) as client:
        response = client.post("/api/auth/verify", json={"admin_password": "changeme"})

    assert response.status_code == 401


def test_upload_document_rejects_wrong_password(api_client):
    pdf_bytes = _make_pdf_bytes(["Aragorn walked into Bree."])

    response = api_client.post(
        "/api/documents/upload",
        files={"file": ("rejected_story.pdf", pdf_bytes, "application/pdf")},
        data={"admin_password": "not-the-right-password"},
    )

    assert response.status_code == 401
    detail = api_client.get("/api/documents/rejected_story")
    assert detail.status_code == 404


def test_upload_document_rejects_missing_password(api_client):
    pdf_bytes = _make_pdf_bytes(["Aragorn walked into Bree."])

    response = api_client.post(
        "/api/documents/upload",
        files={"file": ("no_password_story.pdf", pdf_bytes, "application/pdf")},
    )

    assert response.status_code == 422  # Form(...) is required


def test_upload_document_rejects_when_no_admin_password_configured(tmp_path, monkeypatch):
    import src.api.main as main_module
    from fastapi.testclient import TestClient
    from tests.conftest import FakeOllamaClient, write_test_config

    config_path = write_test_config(tmp_path)
    # Overwrite with an unset admin password (placeholder -> None).
    config_file = pathlib.Path(config_path)
    config_file.write_text(
        config_file.read_text(encoding="utf-8").replace(
            f'admin_password: "{TEST_ADMIN_PASSWORD}"', 'admin_password: "changeme"'
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("BUDDHARAUER_CONFIG", config_path)
    monkeypatch.setattr(main_module, "OllamaClient", lambda base_url, timeout=60.0: FakeOllamaClient())

    app = main_module.create_app()
    with TestClient(app) as client:
        pdf_bytes = _make_pdf_bytes(["text"])
        response = client.post(
            "/api/documents/upload",
            files={"file": ("story.pdf", pdf_bytes, "application/pdf")},
            data={"admin_password": "changeme"},
        )

    assert response.status_code == 401
