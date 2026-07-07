from __future__ import annotations

from src.pipeline.entity_extractor import _batch_chunks, _parse_entities


def _fake_chunks(n):
    from src.pipeline.chunker import Chunk

    return [Chunk(chunk_id=f"c{i}", document_id="doc1", text=f"text {i}", page_start=1, page_end=1) for i in range(n)]


def test_batch_chunks_splits_evenly():
    chunks = _fake_chunks(24)

    batches = _batch_chunks(chunks, batch_size=12)

    assert len(batches) == 2
    assert len(batches[0]) == 12
    assert len(batches[1]) == 12


def test_batch_chunks_handles_remainder():
    chunks = _fake_chunks(25)

    batches = _batch_chunks(chunks, batch_size=12)

    assert len(batches) == 3
    assert len(batches[2]) == 1


def test_parse_entities_valid_json():
    response = '[{"name": "Lady Justice", "type": "character", "description": "A Guild enforcer."}]'

    entities = _parse_entities(response)

    assert len(entities) == 1
    assert entities[0].name == "Lady Justice"
    assert entities[0].type == "character"


def test_parse_entities_tolerates_surrounding_prose():
    response = 'Here is the list:\n[{"name": "Bree", "type": "location", "description": "A town."}]\nThanks!'

    entities = _parse_entities(response)

    assert len(entities) == 1
    assert entities[0].name == "Bree"


def test_parse_entities_empty_array():
    assert _parse_entities("[]") == []


def test_parse_entities_invalid_json_returns_empty():
    assert _parse_entities("not json at all") == []


def test_parse_entities_filters_missing_fields():
    response = '[{"name": "X"}, {"type": "character"}, {"name": "Y", "type": "item", "description": "d"}]'

    entities = _parse_entities(response)

    assert len(entities) == 1
    assert entities[0].name == "Y"


def test_parse_entities_filters_unknown_type():
    response = '[{"name": "X", "type": "not-a-real-type", "description": "d"}]'

    entities = _parse_entities(response)

    assert entities == []
