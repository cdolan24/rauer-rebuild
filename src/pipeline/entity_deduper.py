from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from difflib import SequenceMatcher

from src.database.entity_store import Entity
from src.utils.logging import get_logger
from src.utils.ollama_client import OllamaClient, OllamaError

logger = get_logger(__name__)

# See entity_extractor.py's MAX_WORKERS comment: a wide worker count just
# queues requests behind each other once Ollama is serializing inference
# anyway, and each queued request's timeout clock runs the whole time it waits.
MAX_WORKERS = 3

# A candidate pair needs at least this much name similarity to be worth
# asking the model about at all - keeps the LLM from being asked about
# wildly unrelated entities that just happen to share a few letters.
SIMILARITY_THRESHOLD = 0.7

_CONFIRM_SYSTEM_PROMPT = (
    "You are given two named entities of the same type from a Malifaux story document, "
    "each with a name and description. Decide whether they refer to the SAME underlying "
    "person/place/thing, just recorded under a different name variant (a nickname, partial "
    'name, title, alternate spelling, or a note like "(again)"). They are NOT the same if '
    "they are merely similar-sounding but distinct (e.g. two different people, or a specific "
    'named character versus a generic title/role). Respond ONLY with {"same": true} or '
    '{"same": false}.'
)

_BOOL_RE = re.compile(r'"same"\s*:\s*(true|false)', re.IGNORECASE)


@dataclass
class MergeGroup:
    keep_id: int
    merge_ids: list[int]


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


def _is_candidate_pair(name_a: str, name_b: str) -> bool:
    a, b = _normalize(name_a), _normalize(name_b)
    if not a or not b:
        return False
    if a == b:
        return True
    if a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= SIMILARITY_THRESHOLD


def _candidate_pairs(entities: list[Entity]) -> list[tuple[Entity, Entity]]:
    """All same-type pairs whose names are similar enough to be worth asking
    the model about - a cheap, high-recall pre-filter that keeps the actual
    LLM confirmation step narrow and precise instead of open-ended
    whole-list clustering (which produced only false positives in practice)."""
    by_type: dict[str, list[Entity]] = {}
    for entity in entities:
        by_type.setdefault(entity.type, []).append(entity)

    pairs: list[tuple[Entity, Entity]] = []
    for group in by_type.values():
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if _is_candidate_pair(group[i].name, group[j].name):
                    pairs.append((group[i], group[j]))
    return pairs


def _confirm_pair(
    pair: tuple[Entity, Entity], ollama_client: OllamaClient, chat_model: str
) -> bool:
    entity_a, entity_b = pair
    if _normalize(entity_a.name) == _normalize(entity_b.name):
        # Exact-name duplicates (case/punctuation aside) need no LLM
        # judgment call at all - there's no real ambiguity to resolve.
        return True
    messages = [
        {"role": "system", "content": _CONFIRM_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f'Entity 1: name="{entity_a.name}", description="{entity_a.description}"\n'
                f'Entity 2: name="{entity_b.name}", description="{entity_b.description}"\n\n'
                "JSON:"
            ),
        },
    ]
    try:
        response = ollama_client.chat(chat_model, messages, temperature=0.0)
    except OllamaError as e:
        logger.warning(
            "Duplicate-pair confirmation failed for '%s' / '%s', skipping: %s",
            entity_a.name, entity_b.name, e,
        )
        return False
    match = _BOOL_RE.search(response)
    return bool(match) and match.group(1).lower() == "true"


class _UnionFind:
    def __init__(self) -> None:
        self._parent: dict[int, int] = {}

    def find(self, x: int) -> int:
        self._parent.setdefault(x, x)
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[ra] = rb


def find_duplicate_groups(
    entities: list[Entity],
    ollama_client: OllamaClient,
    chat_model: str,
    max_workers: int = MAX_WORKERS,
) -> list[MergeGroup]:
    """Find same-type entities that are likely the same underlying entity
    under different name variants, from stored name/description alone - no
    source document re-reading.

    A cheap string-similarity pre-filter generates candidate pairs (exact
    whole-list clustering was tried first and produced nothing but
    confidently-wrong merges - e.g. grouping two different real-world
    credited authors together - so this narrows the LLM's job to
    confirming or denying one specific pair at a time, then unions
    transitively-confirmed pairs into groups.
    """
    by_id = {e.id: e for e in entities}
    pairs = _candidate_pairs(entities)
    if not pairs:
        return []

    def _check(pair: tuple[Entity, Entity]) -> tuple[int, int, bool]:
        confirmed = _confirm_pair(pair, ollama_client, chat_model)
        return pair[0].id, pair[1].id, confirmed

    with ThreadPoolExecutor(max_workers=min(max_workers, len(pairs))) as executor:
        results = list(executor.map(_check, pairs))

    uf = _UnionFind()
    involved_ids: set[int] = set()
    for id_a, id_b, confirmed in results:
        if confirmed:
            uf.union(id_a, id_b)
            involved_ids.add(id_a)
            involved_ids.add(id_b)

    clusters: dict[int, list[int]] = {}
    for entity_id in involved_ids:
        clusters.setdefault(uf.find(entity_id), []).append(entity_id)

    groups: list[MergeGroup] = []
    for member_ids in clusters.values():
        if len(member_ids) < 2:
            continue
        # Keep whichever entity has the most complete/informative description.
        keep_id = max(member_ids, key=lambda i: len(by_id[i].description))
        merge_ids = [i for i in member_ids if i != keep_id]
        groups.append(MergeGroup(keep_id=keep_id, merge_ids=merge_ids))

    return groups
