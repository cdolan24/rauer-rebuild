from __future__ import annotations

from src.database.entity_store import Entity
from src.pipeline.entity_deduper import _candidate_pairs, _is_candidate_pair, _normalize


def _entity(id_, name, type_="character", description="desc"):
    return Entity(id=id_, document_id="doc1", name=name, type=type_, description=description)


def test_normalize_strips_case_and_punctuation():
    assert _normalize("Dr. Douglas McMourning!") == "dr douglas mcmourning"


def test_is_candidate_pair_exact_name_match():
    assert _is_candidate_pair("Perdita", "Perdita") is True


def test_is_candidate_pair_substring_match():
    assert _is_candidate_pair("Samael", "Samael Hopkins") is True
    assert _is_candidate_pair("Molly Squidpiddge", "Molly Squidpiddge (again)") is True


def test_is_candidate_pair_high_similarity_ratio():
    assert _is_candidate_pair("Francis", "Francisco") is True


def test_is_candidate_pair_rejects_unrelated_names():
    assert _is_candidate_pair("Seamus", "Sebastian") is False
    assert _is_candidate_pair("Viktoria", "Zoraida") is False


def test_candidate_pairs_only_within_same_type():
    entities = [
        _entity(1, "Bree", type_="location"),
        _entity(2, "Bree", type_="character"),  # same name, different type - not a candidate
    ]

    pairs = _candidate_pairs(entities)

    assert pairs == []


def test_candidate_pairs_finds_similar_names_within_a_type():
    entities = [
        _entity(1, "Samael Hopkins"),
        _entity(2, "Samael"),
        _entity(3, "Bree", type_="location"),
    ]

    pairs = _candidate_pairs(entities)

    assert len(pairs) == 1
    ids = {pairs[0][0].id, pairs[0][1].id}
    assert ids == {1, 2}
