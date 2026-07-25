from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest

from src.database.entity_store import EntityMention, EntityStore


def test_add_and_get_entity(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))

    entity_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")

    entity = store.get(entity_id)
    assert entity is not None
    assert entity.name == "Lady Justice"
    assert entity.type == "character"
    assert entity.summary is None


def test_list_by_document(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Lady Justice", "character", "desc")
    store.add_entity("doc1", "Bree", "location", "desc")
    store.add_entity("doc2", "Perdita", "character", "desc")

    doc1_entities = store.list_by_document("doc1")

    assert {e.name for e in doc1_entities} == {"Lady Justice", "Bree"}


def test_list_by_type(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Lady Justice", "character", "desc")
    store.add_entity("doc1", "Bree", "location", "desc")
    store.add_entity("doc2", "Perdita", "character", "desc")

    characters = store.list_by_type("character")

    assert {e.name for e in characters} == {"Lady Justice", "Perdita"}


def test_add_and_get_mentions(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "desc")

    store.add_mentions(
        [
            EntityMention(entity_id=entity_id, chunk_id="c0", document_id="doc1", page_start=30, page_end=30),
            EntityMention(entity_id=entity_id, chunk_id="c1", document_id="doc1", page_start=68, page_end=68),
        ]
    )

    mentions = store.get_mentions(entity_id)

    assert [m.chunk_id for m in mentions] == ["c0", "c1"]


def test_set_summary(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "desc")

    store.set_summary(entity_id, "A generated wiki-style summary.")

    entity = store.get(entity_id)
    assert entity.summary == "A generated wiki-style summary."


def test_set_type(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Nathan Caroland", "character", "Author of the M1E Core")

    store.set_type(entity_id, "real-person")

    entity = store.get(entity_id)
    assert entity.type == "real-person"


def test_merge_entities_reassigns_mentions_and_soft_deletes_duplicates(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Molly Squidpiddge", "character", "An undead woman.")
    dup_id = store.add_entity("doc1", "Molly-girl", "character", "")
    store.add_mentions(
        [EntityMention(entity_id=dup_id, chunk_id="c0", document_id="doc1", page_start=5, page_end=5)]
    )
    store.set_summary(keep_id, "stale cached summary")

    store.merge_entities(keep_id, [dup_id])

    merged_away = store.get(dup_id)
    assert merged_away is not None  # soft-deleted, not dropped - needed for undo
    assert merged_away.merged_into_id == keep_id
    assert dup_id not in {e.id for e in store.list_all()}  # excluded from normal listings
    kept = store.get(keep_id)
    assert kept.summary is None  # cleared so it regenerates against the new mention set
    mentions = store.get_mentions(keep_id)
    assert [m.chunk_id for m in mentions] == ["c0"]


def test_merge_entities_no_op_with_empty_list(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Lady Justice", "character", "desc")

    store.merge_entities(keep_id, [])

    assert store.get(keep_id) is not None


def test_list_all_orders_by_type_then_name(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Bree", "location", "desc")
    store.add_entity("doc1", "Lady Justice", "character", "desc")

    all_entities = store.list_all()

    assert [e.name for e in all_entities] == ["Lady Justice", "Bree"]


def test_add_and_get_relationship_from_either_side(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    justice_id = store.add_entity("doc1", "Lady Justice", "character", "desc")
    guild_id = store.add_entity("doc1", "The Guild", "faction", "desc")

    store.add_relationship(justice_id, guild_id, "member of")

    from_justice = store.get_relationships(justice_id)
    assert len(from_justice) == 1
    assert from_justice[0].entity_id == justice_id
    assert from_justice[0].related_entity_id == guild_id
    assert from_justice[0].description == "member of"

    from_guild = store.get_relationships(guild_id)
    assert len(from_guild) == 1
    assert from_guild[0].entity_id == guild_id  # normalized to the queried side
    assert from_guild[0].related_entity_id == justice_id


def test_get_relationships_empty_for_entity_with_none(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "desc")

    assert store.get_relationships(entity_id) == []


def test_list_all_relationships(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    a = store.add_entity("doc1", "A", "character", "desc")
    b = store.add_entity("doc1", "B", "character", "desc")
    store.add_relationship(a, b, "rival of")

    all_relationships = store.list_all_relationships()

    assert len(all_relationships) == 1
    assert all_relationships[0].description == "rival of"


def test_merge_entities_reassigns_relationships_and_suppresses_self_loops(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Molly Squidpiddge", "character", "desc")
    dup_id = store.add_entity("doc1", "Molly-girl", "character", "")
    guild_id = store.add_entity("doc1", "The Guild", "faction", "desc")
    store.add_relationship(dup_id, guild_id, "member of")
    store.add_relationship(keep_id, dup_id, "same person as")  # becomes a self-loop after merge

    store.merge_entities(keep_id, [dup_id])

    relationships = store.get_relationships(keep_id)
    assert len(relationships) == 1
    assert relationships[0].related_entity_id == guild_id
    assert relationships[0].description == "member of"


def test_list_merged_away(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Lady Justice", "character", "desc")
    dup_id = store.add_entity("doc1", "Lady-J", "character", "desc")
    other_id = store.add_entity("doc1", "Perdita", "character", "desc")

    store.merge_entities(keep_id, [dup_id])

    merged_away = store.list_merged_away()
    assert [e.id for e in merged_away] == [dup_id]
    assert other_id not in {e.id for e in merged_away}


def test_can_undo_merge_true_right_after_merging(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Molly Squidpiddge", "character", "desc")
    dup_id = store.add_entity("doc1", "Molly-girl", "character", "")

    store.merge_entities(keep_id, [dup_id])

    assert store.can_undo_merge(dup_id) is True


def test_can_undo_merge_false_for_never_merged_entity(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "desc")

    assert store.can_undo_merge(entity_id) is False


def test_can_undo_merge_false_once_keeper_is_merged_again(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    a = store.add_entity("doc1", "A", "character", "desc")
    b = store.add_entity("doc1", "B", "character", "desc")
    c = store.add_entity("doc1", "C", "character", "desc")
    store.merge_entities(b, [a])  # a -> b
    store.merge_entities(c, [b])  # b -> c, making a's merge into b ambiguous now

    assert store.can_undo_merge(a) is False
    assert store.can_undo_merge(b) is True  # b's own merge into c is still cleanly undoable


def test_undo_merge_restores_entity_mentions_and_relationships(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Molly Squidpiddge", "character", "An undead woman.")
    dup_id = store.add_entity("doc1", "Molly-girl", "character", "A young girl.")
    guild_id = store.add_entity("doc1", "The Guild", "faction", "desc")
    store.add_mentions(
        [EntityMention(entity_id=dup_id, chunk_id="c0", document_id="doc1", page_start=5, page_end=5)]
    )
    store.add_relationship(dup_id, guild_id, "member of")
    store.set_summary(keep_id, "a summary generated after the merge")

    store.merge_entities(keep_id, [dup_id])
    store.undo_merge(dup_id)

    restored = store.get(dup_id)
    assert restored.merged_into_id is None
    assert restored.name == "Molly-girl"
    assert restored.description == "A young girl."
    assert [m.chunk_id for m in store.get_mentions(dup_id)] == ["c0"]
    assert store.get_mentions(keep_id) == []
    relationships = store.get_relationships(dup_id)
    assert len(relationships) == 1
    assert relationships[0].related_entity_id == guild_id
    assert store.get_relationships(keep_id) == []
    assert store.get(keep_id).summary is None  # cleared again since its mentions just changed


def test_undo_merge_restores_a_self_loop_only_once_both_sides_are_split(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Keep", "character", "desc")
    a = store.add_entity("doc1", "A", "character", "desc")
    b = store.add_entity("doc1", "B", "character", "desc")
    store.add_relationship(a, b, "sibling of")  # becomes a self-loop once both merge onto keep_id

    store.merge_entities(keep_id, [a, b])
    assert store.get_relationships(keep_id) == []  # suppressed

    store.undo_merge(a)
    assert store.get_relationships(keep_id) == []  # still suppressed - b not split back yet
    assert store.get_relationships(a) == []

    store.undo_merge(b)
    relationships = store.get_relationships(a)
    assert len(relationships) == 1
    assert relationships[0].related_entity_id == b
    assert relationships[0].description == "sibling of"


def test_undo_merge_raises_when_not_eligible(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "desc")

    with pytest.raises(ValueError):
        store.undo_merge(entity_id)


def test_merge_of_a_merge_preserves_true_original_entity_id(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    a = store.add_entity("doc1", "A", "character", "desc")
    b = store.add_entity("doc1", "B", "character", "desc")
    c = store.add_entity("doc1", "C", "character", "desc")
    store.add_mentions(
        [EntityMention(entity_id=a, chunk_id="c0", document_id="doc1", page_start=1, page_end=1)]
    )

    store.merge_entities(b, [a])  # a's mention now lives under b, original_entity_id=a
    store.merge_entities(c, [b])  # b (carrying a's mention) merges into c

    with closing(sqlite3.connect(str(tmp_path / "entities.db"))) as conn:
        row = conn.execute(
            "SELECT original_entity_id FROM entity_mentions WHERE chunk_id = 'c0'"
        ).fetchone()
    assert row[0] == a  # still points at the true original, not the intermediate b


def test_save_and_list_candidates(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "A", "character", "desc")
    dup_id = store.add_entity("doc1", "A-variant", "character", "desc")

    store.save_candidates([(keep_id, [dup_id])])

    candidates = store.list_candidates(status="pending")
    assert len(candidates) == 1
    assert candidates[0].keep_id == keep_id
    assert candidates[0].merge_ids == [dup_id]


def test_rescanning_replaces_stale_pending_candidates_but_keeps_reviewed_ones(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "A", "character", "desc")
    dup_id = store.add_entity("doc1", "A-variant", "character", "desc")

    store.save_candidates([(keep_id, [dup_id])])
    reviewed_id = store.list_candidates()[0].id
    store.update_candidate_status(reviewed_id, "approved")

    store.save_candidates([(keep_id, [dup_id])])  # a fresh scan

    all_candidates = store.list_candidates()
    assert len(all_candidates) == 2  # the approved one persists, plus one new pending
    statuses = sorted(c.status for c in all_candidates)
    assert statuses == ["approved", "pending"]
