from __future__ import annotations

import threading

from src.database.entity_store import Entity
from src.pipeline.entity_deduper import find_duplicate_groups
from src.utils.ollama_client import OllamaError


class ScriptedConfirmClient:
    """Confirms/denies a pair based on whether either entity's name appears
    in a caller-supplied set of names that should be judged as duplicates -
    keyed by name so it's independent of concurrent call ordering."""

    def __init__(self, same_pairs: set[frozenset[str]]) -> None:
        self.same_pairs = same_pairs
        self.calls = 0
        self._lock = threading.Lock()

    def chat(self, model, messages, temperature=0.7):
        with self._lock:
            self.calls += 1
        content = messages[-1]["content"]
        # Extract the two entity names from the prompt content.
        names = [line.split('name="')[1].split('"')[0] for line in content.split("\n") if 'name="' in line]
        pair = frozenset(names)
        same = pair in self.same_pairs
        return f'{{"same": {"true" if same else "false"}}}'

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


class FailingConfirmClient:
    def chat(self, model, messages, temperature=0.7):
        raise OllamaError("simulated failure")

    def embed(self, model, text):
        raise NotImplementedError

    def is_healthy(self):
        return True, ["fake"]


def _entity(id_, name, type_="character", description="desc"):
    return Entity(id=id_, document_id="doc1", name=name, type=type_, description=description)


def test_find_duplicate_groups_merges_confirmed_pair():
    entities = [
        _entity(1, "Samael Hopkins", description="A longer, more complete description."),
        _entity(2, "Samael", description=""),
    ]
    client = ScriptedConfirmClient({frozenset({"Samael Hopkins", "Samael"})})

    groups = find_duplicate_groups(entities, client, "fake-chat")

    assert len(groups) == 1
    assert groups[0].keep_id == 1  # the one with the longer description
    assert groups[0].merge_ids == [2]


def test_find_duplicate_groups_exact_name_match_needs_no_llm_call():
    entities = [
        _entity(1, "Perdita", description="short"),
        _entity(2, "Perdita", description="a much longer and more complete description"),
    ]
    client = ScriptedConfirmClient(set())  # would deny if asked - but it's never asked

    groups = find_duplicate_groups(entities, client, "fake-chat")

    assert client.calls == 0
    assert len(groups) == 1
    assert groups[0].keep_id == 2
    assert groups[0].merge_ids == [1]


def test_find_duplicate_groups_denied_pair_is_not_merged():
    entities = [_entity(1, "Seamus"), _entity(2, "Sebastian")]
    # These names aren't similar enough to even become a candidate pair -
    # confirm no groups come back and no call was made.
    client = ScriptedConfirmClient(set())

    groups = find_duplicate_groups(entities, client, "fake-chat")

    assert groups == []
    assert client.calls == 0


def test_find_duplicate_groups_transitively_unions_a_chain():
    entities = [
        _entity(1, "McMourning", description="d1"),
        _entity(2, "Douglas McMourning", description="d2"),
        _entity(3, "Dr. Douglas McMourning", description="the longest and most complete one"),
    ]
    client = ScriptedConfirmClient(
        {
            frozenset({"McMourning", "Douglas McMourning"}),
            frozenset({"Douglas McMourning", "Dr. Douglas McMourning"}),
        }
    )

    groups = find_duplicate_groups(entities, client, "fake-chat")

    assert len(groups) == 1
    assert groups[0].keep_id == 3
    assert set(groups[0].merge_ids) == {1, 2}


def test_find_duplicate_groups_skips_pair_on_ollama_error():
    entities = [_entity(1, "Samael Hopkins"), _entity(2, "Samael")]
    client = FailingConfirmClient()

    groups = find_duplicate_groups(entities, client, "fake-chat")

    assert groups == []
