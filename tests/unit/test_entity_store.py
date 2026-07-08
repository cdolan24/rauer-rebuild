from __future__ import annotations

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


def test_merge_entities_reassigns_mentions_and_deletes_duplicates(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    keep_id = store.add_entity("doc1", "Molly Squidpiddge", "character", "An undead woman.")
    dup_id = store.add_entity("doc1", "Molly-girl", "character", "")
    store.add_mentions(
        [EntityMention(entity_id=dup_id, chunk_id="c0", document_id="doc1", page_start=5, page_end=5)]
    )
    store.set_summary(keep_id, "stale cached summary")

    store.merge_entities(keep_id, [dup_id])

    assert store.get(dup_id) is None
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
