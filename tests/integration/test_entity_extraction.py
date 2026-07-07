from __future__ import annotations

from src.database.entity_store import EntityStore
from src.pipeline import entity_extractor
from src.pipeline.chunker import Chunk
from src.pipeline.entity_extractor import extract_entities_for_document
from src.utils.ollama_client import OllamaError

_MULTI_BATCH_CHUNK_COUNT = entity_extractor.BATCH_SIZE * 2 + 5  # guarantees >=3 batches


class ScriptedOllamaClient:
    """Returns a fixed entity-extraction response for every chat() call."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def chat(self, model, messages, temperature=0.7):
        self.calls += 1
        return self.response

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


class FlakyOllamaClient:
    """Fails on the first call, then returns a fixed response for the rest."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def chat(self, model, messages, temperature=0.7):
        self.calls += 1
        if self.calls == 1:
            raise OllamaError("simulated timeout")
        return self.response

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


def _chunk(chunk_id, text, page):
    return Chunk(chunk_id=chunk_id, document_id="doc1", text=text, page_start=page, page_end=page)


def test_extract_entities_creates_entities_and_mentions(tmp_path):
    chunks = [
        _chunk("c0", "Lady Justice walked into Bree with her revolver drawn.", 30),
        _chunk("c1", "The town of Bree was quiet that evening.", 31),
        _chunk("c2", "No named entities here, just weather.", 32),
    ]
    response = (
        '[{"name": "Lady Justice", "type": "character", "description": "A Guild enforcer."},'
        ' {"name": "Bree", "type": "location", "description": "A frontier town."}]'
    )
    client = ScriptedOllamaClient(response)
    store = EntityStore(str(tmp_path / "entities.db"))

    count = extract_entities_for_document(chunks, "doc1", client, "fake-chat", store)

    assert count == 2
    entities = {e.name: e for e in store.list_by_document("doc1")}
    assert set(entities) == {"Lady Justice", "Bree"}

    lady_justice_mentions = store.get_mentions(entities["Lady Justice"].id)
    assert [m.chunk_id for m in lady_justice_mentions] == ["c0"]

    bree_mentions = store.get_mentions(entities["Bree"].id)
    assert {m.chunk_id for m in bree_mentions} == {"c0", "c1"}


def test_extract_entities_dedupes_across_batches(tmp_path):
    chunks = [
        _chunk(f"c{i}", f"Lady Justice appears again in scene {i}.", i + 1)
        for i in range(_MULTI_BATCH_CHUNK_COUNT)
    ]
    response = '[{"name": "Lady Justice", "type": "character", "description": "desc"}]'
    client = ScriptedOllamaClient(response)
    store = EntityStore(str(tmp_path / "entities.db"))

    count = extract_entities_for_document(chunks, "doc1", client, "fake-chat", store)

    assert count == 1
    assert client.calls > 1  # multiple batches, same entity each time
    entities = store.list_by_document("doc1")
    assert len(entities) == 1


def test_extract_entities_empty_chunks_returns_zero(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))

    count = extract_entities_for_document([], "doc1", ScriptedOllamaClient("[]"), "fake-chat", store)

    assert count == 0


def test_extract_entities_survives_a_failed_batch(tmp_path):
    """A single batch timing out shouldn't lose entities/mentions from the
    other, successful batches (regression test for a real failure hit while
    extracting entities from the full M1E document)."""
    chunks = [
        _chunk(f"c{i}", f"Lady Justice appears again in scene {i}.", i + 1)
        for i in range(_MULTI_BATCH_CHUNK_COUNT)
    ]
    response = '[{"name": "Lady Justice", "type": "character", "description": "desc"}]'
    client = FlakyOllamaClient(response)
    store = EntityStore(str(tmp_path / "entities.db"))

    count = extract_entities_for_document(chunks, "doc1", client, "fake-chat", store)

    assert count == 1  # found in later batches despite the first one failing
    entity = store.list_by_document("doc1")[0]
    mentions = store.get_mentions(entity.id)
    assert len(mentions) == _MULTI_BATCH_CHUNK_COUNT  # mention indexing still ran over ALL chunks
