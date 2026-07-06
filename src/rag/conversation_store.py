from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConversationTurn:
    question: str
    answer: str


class ConversationStore:
    """In-memory multi-turn conversation history, keyed by conversation id.

    In-memory is sufficient for a single-process MVP; history is not
    expected to survive a server restart.
    """

    def __init__(self, max_history: int = 10) -> None:
        self._max_history = max_history
        self._conversations: dict[str, list[ConversationTurn]] = {}

    def get_history(self, conversation_id: str) -> list[ConversationTurn]:
        return list(self._conversations.get(conversation_id, []))

    def add_turn(self, conversation_id: str, question: str, answer: str) -> None:
        history = self._conversations.setdefault(conversation_id, [])
        history.append(ConversationTurn(question=question, answer=answer))
        if len(history) > self._max_history:
            del history[: len(history) - self._max_history]

    def clear(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)
