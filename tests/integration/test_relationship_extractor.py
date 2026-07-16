from __future__ import annotations

from src.database.entity_store import EntityMention, EntityStore
from src.pipeline.chunker import Chunk
from src.pipeline.relationship_extractor import (
    MAX_CANDIDATES,
    _filter_candidates_by_context,
    extract_relationships_for_document,
    extract_relationships_for_entity,
)
from src.utils.ollama_client import OllamaError


class ScriptedRelationshipClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0

    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        self.calls += 1
        return self.response

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


class FailingClient:
    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        raise OllamaError("simulated failure")

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


class FakeVectorStore:
    def __init__(self, chunks_by_document: dict[str, list[Chunk]]) -> None:
        self._chunks_by_document = chunks_by_document

    def get_chunks_by_document(self, document_id):
        return self._chunks_by_document.get(document_id, [])


def _entity(store, name, type_="character", description="desc"):
    entity_id = store.add_entity("doc1", name, type_, description)
    return store.get(entity_id)


def test_extract_relationships_for_entity_matches_candidate_by_name():
    justice = _entity_no_store("Lady Justice", 1)
    guild = _entity_no_store("The Guild", 2, type_="faction")
    client = ScriptedRelationshipClient('[{"name": "The Guild", "description": "member of"}]')

    results = extract_relationships_for_entity(
        justice, "Lady Justice serves the Guild.", [guild], client, "fake-chat"
    )

    assert results == [(2, "member of")]


def test_extract_relationships_for_entity_ignores_unknown_candidate_name():
    justice = _entity_no_store("Lady Justice", 1)
    guild = _entity_no_store("The Guild", 2, type_="faction")
    client = ScriptedRelationshipClient('[{"name": "Some Other Entity", "description": "ally of"}]')

    results = extract_relationships_for_entity(
        justice, "passage", [guild], client, "fake-chat"
    )

    assert results == []


def test_extract_relationships_for_entity_returns_empty_on_no_relationships_found():
    justice = _entity_no_store("Lady Justice", 1)
    guild = _entity_no_store("The Guild", 2, type_="faction")
    client = ScriptedRelationshipClient("[]")

    results = extract_relationships_for_entity(
        justice, "passage", [guild], client, "fake-chat"
    )

    assert results == []


def test_extract_relationships_for_entity_survives_ollama_failure():
    justice = _entity_no_store("Lady Justice", 1)
    guild = _entity_no_store("The Guild", 2, type_="faction")
    client = FailingClient()

    results = extract_relationships_for_entity(
        justice, "passage", [guild], client, "fake-chat"
    )

    assert results == []


def test_extract_relationships_for_entity_skips_call_with_no_candidates_or_context():
    justice = _entity_no_store("Lady Justice", 1)
    client = ScriptedRelationshipClient('[{"name": "X", "description": "y"}]')

    assert extract_relationships_for_entity(justice, "passage", [], client, "fake-chat") == []
    assert client.calls == 0

    guild = _entity_no_store("The Guild", 2, type_="faction")
    assert extract_relationships_for_entity(justice, "", [guild], client, "fake-chat") == []
    assert client.calls == 0


def _entity_no_store(name, id_, type_="character", description="desc"):
    from src.database.entity_store import Entity

    return Entity(id=id_, document_id="doc1", name=name, type=type_, description=description)


def test_extract_relationships_for_document_stores_relationships(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    justice_id = store.add_entity("doc1", "Lady Justice", "character", "desc")
    guild_id = store.add_entity("doc1", "The Guild", "faction", "desc")
    store.add_mentions(
        [EntityMention(entity_id=justice_id, chunk_id="c0", document_id="doc1", page_start=1, page_end=1)]
    )
    vector_store = FakeVectorStore({"doc1": [Chunk(chunk_id="c0", document_id="doc1", text="Lady Justice serves the Guild.", page_start=1, page_end=1)]})
    justice = store.get(justice_id)
    guild = store.get(guild_id)
    client = ScriptedRelationshipClient('[{"name": "The Guild", "description": "member of"}]')

    count = extract_relationships_for_document(
        [justice], store, vector_store, client, "fake-chat"
    )

    assert count == 1
    relationships = store.get_relationships(justice_id)
    assert len(relationships) == 1
    assert relationships[0].related_entity_id == guild_id
    assert relationships[0].description == "member of"


def test_extract_relationships_for_document_one_entity_failure_does_not_block_others(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    a_id = store.add_entity("doc1", "A", "character", "desc")
    b_id = store.add_entity("doc1", "B", "character", "desc")
    store.add_mentions(
        [
            EntityMention(entity_id=a_id, chunk_id="c0", document_id="doc1", page_start=1, page_end=1),
            EntityMention(entity_id=b_id, chunk_id="c1", document_id="doc1", page_start=2, page_end=2),
        ]
    )
    vector_store = FakeVectorStore(
        {
            "doc1": [
                Chunk(chunk_id="c0", document_id="doc1", text="A meets B.", page_start=1, page_end=1),
                Chunk(chunk_id="c1", document_id="doc1", text="B meets A.", page_start=2, page_end=2),
            ]
        }
    )
    client = FailingClient()  # every call fails - both entities should just get zero relationships

    count = extract_relationships_for_document(
        [store.get(a_id), store.get(b_id)], store, vector_store, client, "fake-chat"
    )

    assert count == 0
    assert store.get_relationships(a_id) == []
    assert store.get_relationships(b_id) == []


def test_filter_candidates_by_context_keeps_only_named_candidates():
    guild = _entity_no_store("The Guild", 1, type_="faction")
    unrelated = _entity_no_store("Some Other Entity", 2, type_="character")

    filtered = _filter_candidates_by_context([guild, unrelated], "Lady Justice serves the Guild.")

    assert filtered == [guild]


def test_filter_candidates_by_context_caps_at_max_candidates():
    candidates = [_entity_no_store(f"Bree{i}", i, type_="location") for i in range(MAX_CANDIDATES + 10)]
    context = " ".join(c.name for c in candidates)  # every candidate's name appears

    filtered = _filter_candidates_by_context(candidates, context)

    assert len(filtered) == MAX_CANDIDATES


def test_extract_relationships_for_document_empty_entities_returns_zero(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    vector_store = FakeVectorStore({})
    client = ScriptedRelationshipClient("[]")

    assert extract_relationships_for_document([], store, vector_store, client, "fake-chat") == 0
