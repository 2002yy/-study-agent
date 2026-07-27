from __future__ import annotations

import pytest

from src.application.policy_chat_service import (
    PolicyChatCommand,
    _restore_persisted_research_truth,
)
from src.domain.runtime_entities import ChatTurn


def _persisted_turn() -> ChatTurn:
    return ChatTurn(
        id="turn-1",
        thread_id="thread-1",
        status="failed",
        rag_snapshot={
            "web_context": {
                "used": True,
                "run_id": "research-1",
                "source": "research_run",
            },
            "research_sources": {
                "run_id": "research-1",
                "provider_status": "partial",
                "stop_reason": "budget_exhausted",
                "selected_sources": [{"assessment": {"source_id": "source-1"}}],
                "rejected_sources": [],
            },
        },
    )


def test_retry_cannot_switch_research_run_owner():
    command = PolicyChatCommand(
        user_input="retry",
        retry_of_turn_id="turn-1",
        web_context="SECOND SOURCE BLOCK",
        web_context_run_id="research-2",
        research_sources={
            "run_id": "research-2",
            "provider_status": "found",
            "stop_reason": "enough_evidence",
            "selected_sources": [],
            "rejected_sources": [],
        },
    )

    with pytest.raises(ValueError, match="cannot switch ResearchRun evidence"):
        _restore_persisted_research_truth(command, _persisted_turn())


def test_same_run_retry_uses_frozen_sources_instead_of_client_payload():
    command = PolicyChatCommand(
        user_input="retry",
        retry_of_turn_id="turn-1",
        web_context="SOURCE BLOCK",
        web_context_run_id="research-1",
        research_sources={
            "run_id": "research-1",
            "provider_status": "found",
            "stop_reason": "tampered",
            "selected_sources": [],
            "rejected_sources": [],
        },
    )

    restored = _restore_persisted_research_truth(command, _persisted_turn())

    assert restored.research_sources is not None
    assert restored.research_sources["stop_reason"] == "budget_exhausted"
    assert restored.research_sources["selected_sources"] == [
        {"assessment": {"source_id": "source-1"}}
    ]


def test_retry_without_run_does_not_claim_old_research_sources():
    command = PolicyChatCommand(
        user_input="retry without research evidence",
        retry_of_turn_id="turn-1",
    )

    restored = _restore_persisted_research_truth(command, _persisted_turn())

    assert restored.research_sources is None
