"""Cooperative retrieval cancellation for G12 chat pre-answer RAG.

The chat service owns the durable cancellation truth (ChatTurn). Retrieval
layers only receive a lightweight ``should_cancel`` callable; when it reports
an accepted cancellation they raise :class:`RetrievalCancelled` so the request
abandons cleanly instead of returning partial results that would be discarded.
"""

from __future__ import annotations


class RetrievalCancelled(Exception):
    """Raised at a retrieval checkpoint when the owning turn was cancelled."""

    def __init__(self, *, stage: str) -> None:
        super().__init__(f"Retrieval cancelled at checkpoint '{stage}'")
        self.stage = stage
