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


def test_merge_entities_reassigns_relationships_and_drops_self_loops(tmp_path):
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
