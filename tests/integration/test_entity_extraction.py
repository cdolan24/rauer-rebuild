from __future__ import annotations

import threading

from src.database.entity_store import EntityStore
from src.pipeline import entity_extractor
from src.pipeline.chunker import Chunk
from src.pipeline.entity_extractor import extract_entities_for_document, reclassify_entities
from src.utils.ollama_client import OllamaError

_MULTI_BATCH_CHUNK_COUNT = entity_extractor.BATCH_SIZE * 2 + 5  # guarantees >=3 batches


class ScriptedOllamaClient:
    """Returns a fixed entity-extraction response for every chat() call.

    Extraction now dispatches batches concurrently, so the call counter is
    lock-protected to stay accurate under real threading.
    """

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0
        self._lock = threading.Lock()

    def chat(self, model, messages, temperature=0.7):
        with self._lock:
            self.calls += 1
        return self.response

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


class FlakyOllamaClient:
    """Fails on exactly the first call to complete, then returns a fixed
    response for the rest - lock-protected so concurrent dispatch can't race
    multiple threads into all seeing "the first" call."""

    def __init__(self, response: str) -> None:
        self.response = response
        self.calls = 0
        self._lock = threading.Lock()

    def chat(self, model, messages, temperature=0.7):
        with self._lock:
            self.calls += 1
            should_fail = self.calls == 1
        if should_fail:
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

    result = extract_entities_for_document(chunks, "doc1", client, "fake-chat", store)

    assert result.entity_count == 2
    assert result.uncovered_chunk_ids == []
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

    result = extract_entities_for_document(chunks, "doc1", client, "fake-chat", store)

    assert result.entity_count == 1
    assert client.calls > 1  # multiple batches, same entity each time
    entities = store.list_by_document("doc1")
    assert len(entities) == 1


def test_extract_entities_survives_a_failed_batch(tmp_path):
    """A single batch timing out shouldn't lose entities/mentions from the
    other, successful batches (regression test for a real failure hit while
    extracting entities from the full M1E document). With retry-once, a
    single transient failure is also recovered rather than left uncovered."""
    chunks = [
        _chunk(f"c{i}", f"Lady Justice appears again in scene {i}.", i + 1)
        for i in range(_MULTI_BATCH_CHUNK_COUNT)
    ]
    response = '[{"name": "Lady Justice", "type": "character", "description": "desc"}]'
    client = FlakyOllamaClient(response)
    store = EntityStore(str(tmp_path / "entities.db"))

    result = extract_entities_for_document(chunks, "doc1", client, "fake-chat", store)

    assert result.entity_count == 1  # found in later batches despite the first one failing
    assert result.uncovered_chunk_ids == []  # retried and recovered, nothing lost
    entity = store.list_by_document("doc1")[0]
    mentions = store.get_mentions(entity.id)
    assert len(mentions) == _MULTI_BATCH_CHUNK_COUNT  # mention indexing still ran over ALL chunks


class PermanentlyFailingOllamaClient:
    """Fails every call whose message content contains `fail_marker`, and
    returns a fixed response otherwise - lets a test target one specific
    batch for permanent failure regardless of concurrent dispatch order."""

    def __init__(self, response: str, fail_marker: str) -> None:
        self.response = response
        self.fail_marker = fail_marker

    def chat(self, model, messages, temperature=0.7):
        if self.fail_marker in messages[-1]["content"]:
            raise OllamaError("simulated permanent failure")
        return self.response

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


def test_extract_entities_reports_uncovered_chunks_after_permanent_batch_failure(tmp_path):
    """A batch that fails on both its original attempt and its retry loses
    coverage entirely - the chunks it covered should be reported, not
    silently dropped."""
    good_chunks = [
        _chunk(f"c{i}", f"Lady Justice appears again in scene {i}.", i + 1)
        for i in range(entity_extractor.BATCH_SIZE)
    ]
    bad_chunks = [
        _chunk(f"bad{i}", f"UNRECOVERABLE marker text {i}.", 100 + i)
        for i in range(entity_extractor.BATCH_SIZE)
    ]
    chunks = good_chunks + bad_chunks
    response = '[{"name": "Lady Justice", "type": "character", "description": "desc"}]'
    client = PermanentlyFailingOllamaClient(response, fail_marker="UNRECOVERABLE")
    store = EntityStore(str(tmp_path / "entities.db"))

    result = extract_entities_for_document(chunks, "doc1", client, "fake-chat", store)

    assert result.entity_count == 1
    assert set(result.uncovered_chunk_ids) == {c.chunk_id for c in bad_chunks}


class ByNameOllamaClient:
    """Returns a scripted type per entity, keyed by the entity's name found
    in the outgoing message content - deterministic regardless of the
    concurrent dispatch order reclassify_entities uses."""

    def __init__(self, type_by_name: dict[str, str]) -> None:
        self.type_by_name = type_by_name
        self.calls = 0
        self._lock = threading.Lock()

    def chat(self, model, messages, temperature=0.7):
        with self._lock:
            self.calls += 1
        content = messages[-1]["content"]
        for name, type_ in self.type_by_name.items():
            if f"Name: {name}" in content:
                return f'{{"type": "{type_}"}}'
        return '{"type": "character"}'

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


def _entity(store, name, type_="character", description="desc"):
    entity_id = store.add_entity("doc1", name, type_, description)
    return store.get(entity_id)


def test_reclassify_entities_moves_real_person_out_of_character(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    author = _entity(store, "Nathan Caroland", description="Author of the M1E Core")
    character = _entity(store, "Seamus", description="A wealthy and charismatic individual")
    client = ByNameOllamaClient({"Nathan Caroland": "real-person", "Seamus": "character"})

    updates = reclassify_entities([author, character], client, "fake-chat")

    assert updates == {author.id: "real-person"}  # Seamus unchanged, not included


def test_reclassify_entities_discards_novel_tag_below_threshold(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    e1 = _entity(store, "E1")
    e2 = _entity(store, "E2")
    client = ByNameOllamaClient({"E1": "ghost", "E2": "ghost"})  # only 2, below DYNAMIC_TAG_MIN_COUNT=3

    updates = reclassify_entities([e1, e2], client, "fake-chat")

    assert updates == {}  # novel tag didn't reach the threshold, both revert to original type


def test_reclassify_entities_keeps_novel_tag_at_threshold(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entities = [_entity(store, f"E{i}") for i in range(3)]
    client = ByNameOllamaClient({e.name: "ghost" for e in entities})  # 3 meets DYNAMIC_TAG_MIN_COUNT

    updates = reclassify_entities(entities, client, "fake-chat")

    assert updates == {e.id: "ghost" for e in entities}


def test_reclassify_entities_keeps_original_type_on_ollama_error(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity = _entity(store, "Nathan Caroland", type_="character")
    client = FlakyOllamaClient('{"type": "real-person"}')

    updates = reclassify_entities([entity], client, "fake-chat")

    assert updates == {}  # the one call fails (FlakyOllamaClient fails call #1), type unchanged


def test_reclassify_entities_skips_blank_description_without_calling_ollama(tmp_path):
    """Empirically, given no description, the model defaults to 'sounds like
    a real name' and mistypes every blank-description entity as real-person -
    cheaper and more accurate to just skip the call entirely."""
    store = EntityStore(str(tmp_path / "entities.db"))
    entity = _entity(store, "Philip", type_="character", description="")
    client = ByNameOllamaClient({"Philip": "real-person"})

    updates = reclassify_entities([entity], client, "fake-chat")

    assert updates == {}
    assert client.calls == 0
