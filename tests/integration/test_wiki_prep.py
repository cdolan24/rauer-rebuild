from __future__ import annotations

from src.database.entity_store import EntityStore
from src.pipeline.ingest import _prepare_wiki_data
from src.utils.ollama_client import OllamaError


class ScriptedPrepClient:
    """Handles both dedup-confirmation prompts ({"same": ...}) and
    summary-generation prompts with canned, distinguishable behavior."""

    def __init__(self, same_pairs: set[frozenset[str]] = frozenset(), summary_text: str = "A generated summary."):
        self.same_pairs = same_pairs
        self.summary_text = summary_text
        self.summary_calls = 0
        self.summarized_names: list[str] = []

    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        system = messages[0]["content"]
        if "SAME underlying" in system:
            content = messages[-1]["content"]
            names = [
                line.split('name="')[1].split('"')[0] for line in content.split("\n") if 'name="' in line
            ]
            pair = frozenset(names)
            same = pair in self.same_pairs
            return f'{{"same": {"true" if same else "false"}}}'
        # A summary-generation call.
        self.summary_calls += 1
        name_line = next(line for line in messages[-1]["content"].split("\n") if line.startswith("Name:"))
        self.summarized_names.append(name_line.removeprefix("Name:").strip())
        return self.summary_text


class FailingClient:
    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        raise OllamaError("simulated failure")


def test_prepare_wiki_data_dedupes_across_the_whole_store(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    id_a = store.add_entity("doc1", "Samael Hopkins", "character", "A longer, more complete description.")
    id_b = store.add_entity("doc2", "Samael", "character", "")  # from a *different* document
    client = ScriptedPrepClient(same_pairs={frozenset({"Samael Hopkins", "Samael"})})

    _prepare_wiki_data(store, client, "fake-chat")

    remaining = store.list_all()
    assert len(remaining) == 1
    assert remaining[0].id == id_a  # kept the more complete one
    assert store.get(id_b) is None


def test_prepare_wiki_data_generates_summaries_for_entities_missing_one(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    client = ScriptedPrepClient()

    _prepare_wiki_data(store, client, "fake-chat")

    entity = store.list_all()[0]
    assert entity.summary == "A generated summary."
    assert client.summary_calls == 1


def test_prepare_wiki_data_skips_entities_that_already_have_a_summary(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.set_summary(entity_id, "Already summarized.")
    client = ScriptedPrepClient()

    _prepare_wiki_data(store, client, "fake-chat")

    assert client.summary_calls == 0
    assert store.get(entity_id).summary == "Already summarized."


def test_prepare_wiki_data_summarizes_after_merging_not_before(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    id_a = store.add_entity("doc1", "Samael Hopkins", "character", "A longer, more complete description.")
    store.add_entity("doc2", "Samael", "character", "")
    client = ScriptedPrepClient(same_pairs={frozenset({"Samael Hopkins", "Samael"})})

    _prepare_wiki_data(store, client, "fake-chat")

    # Only one entity remains after the merge, so only one summary call
    # should have happened - never one for the entity that got merged away.
    assert client.summary_calls == 1
    assert client.summarized_names == ["Samael Hopkins"]
    assert store.get(id_a).summary == "A generated summary."


def test_prepare_wiki_data_does_not_raise_when_ollama_is_unreachable(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    client = FailingClient()

    # find_duplicate_groups already tolerates per-pair failures internally,
    # but with only one entity there are no candidate pairs at all - this
    # mainly exercises the summary-generation failure path.
    _prepare_wiki_data(store, client, "fake-chat")  # should not raise

    assert store.list_all()[0].summary is None
