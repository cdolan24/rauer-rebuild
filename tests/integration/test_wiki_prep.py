from __future__ import annotations

from src.database.entity_store import EntityStore
from src.pipeline.ingest import _prepare_wiki_data
from src.utils.ollama_client import OllamaError


class FakeVectorStore:
    """No chunks stored - fine here since these tests' entities have no
    mentions, so gather_mention_context never actually calls this."""

    def get_chunks_by_document(self, document_id):
        return []


class ScriptedPrepClient:
    """Returns a canned summary/relationship response for any call - dedup
    confirmation prompts are never sent since _prepare_wiki_data no longer
    runs automatic deduplication (see ingest.py's docstring)."""

    def __init__(self, summary_text: str = "A generated summary."):
        self.summary_text = summary_text
        self.summary_calls = 0
        self.summarized_names: list[str] = []

    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        system = messages[0]["content"]
        if "relationships between" in system:
            return "[]"  # no relationships found - not the focus of these tests
        # A summary-generation call.
        self.summary_calls += 1
        name_line = next(line for line in messages[-1]["content"].split("\n") if line.startswith("Name:"))
        self.summarized_names.append(name_line.removeprefix("Name:").strip())
        return self.summary_text


class FailingClient:
    def chat(self, model, messages, temperature=0.7, num_predict=None, keep_alive=None):
        raise OllamaError("simulated failure")


def test_prepare_wiki_data_does_not_automatically_deduplicate(tmp_path):
    """Regression test: automatic dedup was removed from _prepare_wiki_data
    after it merged 91 unreviewed (and unauditable) groups during a real M2E
    ingestion, on top of a ~40% false-positive rate already found against
    M1E's data. Deduplication is now a deliberate, separate, manually-reviewed
    step (scripts/dedupe_entities.py --dry-run)."""
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Samael Hopkins", "character", "A longer, more complete description.")
    store.add_entity("doc2", "Samael", "character", "")  # an obvious name-variant duplicate
    client = ScriptedPrepClient()

    _prepare_wiki_data(store, FakeVectorStore(), client, "fake-chat")

    assert len(store.list_all()) == 2  # neither entity was merged away


def test_prepare_wiki_data_generates_summaries_for_entities_missing_one(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    client = ScriptedPrepClient()

    _prepare_wiki_data(store, FakeVectorStore(), client, "fake-chat")

    entity = store.list_all()[0]
    assert entity.summary == "A generated summary."
    assert client.summary_calls == 1


def test_prepare_wiki_data_skips_entities_that_already_have_a_summary(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    entity_id = store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    store.set_summary(entity_id, "Already summarized.")
    client = ScriptedPrepClient()

    _prepare_wiki_data(store, FakeVectorStore(), client, "fake-chat")

    assert client.summary_calls == 0
    assert store.get(entity_id).summary == "Already summarized."


def test_prepare_wiki_data_does_not_raise_when_ollama_is_unreachable(tmp_path):
    store = EntityStore(str(tmp_path / "entities.db"))
    store.add_entity("doc1", "Lady Justice", "character", "A Guild enforcer.")
    client = FailingClient()

    # Exercises the summary-generation and relationship-extraction failure
    # paths - both already tolerate OllamaError internally.
    _prepare_wiki_data(store, FakeVectorStore(), client, "fake-chat")  # should not raise

    assert store.list_all()[0].summary is None
