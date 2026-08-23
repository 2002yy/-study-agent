"""G16 per-session memory-ask tests.

Contract: docs/PROJECT_STATUS.md section 13 (decisions 1-14, gates v2).
Covers the three-policy gate, session-grant CAS persistence, fail-closed
CAS semantics, audit field, and revocation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.external_data_policy import decide_external_data, normalize_memory_policy
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.runtime_repository import RuntimeRepository


# ---------------------------------------------------------------------------
# Policy gate unit tests (decisions 1, 8, 9; gates 1/2/5)


def _decide(memory_policy: str | None, *, consent: bool = False, context: str = "allow_local_evidence"):
    return decide_external_data(
        web_policy="off",
        web_consent=False,
        cloud_context_policy=context,
        task_source_policy="local_and_web",
        memory_policy=memory_policy,
        memory_consent=consent,
    )


def test_default_memory_policy_is_auto_and_preserves_legacy_behavior():
    # No memory_policy argument at all == legacy callers keep old behavior.
    legacy = decide_external_data(
        web_policy="auto",
        web_consent=True,
        cloud_context_policy="allow_local_evidence",
        task_source_policy="local_and_web",
    )
    assert legacy.memory_allowed is True
    assert normalize_memory_policy(None) == "auto"
    assert normalize_memory_policy("bogus") == "auto"


def test_off_blocks_memory_even_in_allow_context():
    assert _decide("off").memory_allowed is False
    assert _decide("off", consent=True).memory_allowed is False


def test_ask_requires_session_grant():
    assert _decide("ask", consent=False).memory_allowed is False
    assert _decide("ask", consent=True).memory_allowed is True


def test_and_gate_context_policy_blocks_memory_regardless():
    for policy in ("off", "ask", "auto"):
        decision = _decide(policy, consent=True, context="recent_chat")
        assert decision.memory_allowed is False


# ---------------------------------------------------------------------------
# Repository CAS tests (decisions 6/11; gates 3/8)


def test_grant_and_revoke_mutate_only_consent_keys(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    thread = repository.ensure_chat_thread("chat_mc")
    # Seed an unrelated key the way the turn flow would.
    repository.update_chat_thread_settings(
        thread.id, {"conversationInstruction": "keep me"}
    )

    granted = repository.grant_session_memory_consent(thread.id)
    snapshot = granted.settings_snapshot or {}
    assert snapshot["memory_consent_granted"] is True
    assert snapshot["memory_consent_granted_at"]
    assert snapshot["conversationInstruction"] == "keep me"

    revoked = repository.revoke_session_memory_consent(thread.id)
    snapshot = revoked.settings_snapshot or {}
    assert snapshot["memory_consent_granted"] is False
    assert snapshot["memory_consent_revoked_at"]
    assert snapshot["memory_consent_granted_at"]  # history preserved
    assert snapshot["conversationInstruction"] == "keep me"


# ---------------------------------------------------------------------------
# Chat integration (decisions 2/6/7/10; gates 3/4/6)


class _FailingEvaluator:
    def evaluate(self, **kwargs):
        raise AssertionError("semantic evaluation must not run here")


@dataclass
class _LocalRag:
    enabled: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "skipped" if self.enabled else "disabled",
            "query": "",
            "retrieval_mode": "hybrid",
            "reason": "test",
            "context": "",
            "sources": "",
            "result_count": 0,
            "results": [],
            "debug": {},
            "attempts": [],
            "rewritten_query": "",
        }


def _policy_service(tmp_path):
    from src.application.chat_service import ChatDependencies
    from src.application.policy_chat_service import ExternalDataPolicyChatService
    from src.task_contract import (
        TaskAwarePedagogyEngine,
        TaskAwarePedagogyEvaluationService,
        route_request_with_task_contract,
    )
    from src.tools.web_agent import WebToolTrace

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "chat.db"))
    dependencies = ChatDependencies(
        route_request=route_request_with_task_contract,
        retrieve_local_knowledge=lambda query, **kwargs: _LocalRag(
            enabled=bool(kwargs["enabled"])
        ),
        read_memory_bundle=lambda mode: {"learner_profile.md": "PROFILE"},
        resolve_web_tools=lambda *args, **kwargs: WebToolTrace(enabled=False),
        build_messages=lambda **kwargs: [
            {"role": "system", "content": kwargs["role_prompt"]},
            {"role": "user", "content": kwargs["user_input"]},
        ],
        pedagogy_engine=TaskAwarePedagogyEngine(),
        pedagogy_evaluation=TaskAwarePedagogyEvaluationService(
            _FailingEvaluator()
        ),
        build_role_prompt=lambda role, **kwargs: "ROLE",
        stream_chat=lambda *args, **kwargs: iter(("ok",)),
    )
    return ExternalDataPolicyChatService(repository, dependencies), repository


def test_ask_with_consent_persists_grant_for_later_turns(tmp_path, monkeypatch):
    from src.application.policy_chat_service import PolicyChatCommand

    chat, repository = _policy_service(tmp_path)

    prepared = chat.start_turn(
        PolicyChatCommand(
            user_input="问题一",
            thread_id="chat_ask",
            rag_enabled=True,
            memory_policy="ask",
            memory_consent=True,
            operation_id="op_mc1",
        )
    )
    assert prepared.turn.route_snapshot["external_data_policy"]["memory_allowed"] is True
    # Release the reservation so the next turn can acquire it (start_turn
    # only prepares; completion normally releases in the full lifecycle).
    repository.release_chat_operation("chat_ask", "op_mc1")

    # The grant must be durable in the thread snapshot.
    thread = repository.get_chat_thread("chat_ask")
    assert thread is not None
    assert thread.settings_snapshot.get("memory_consent_granted") is True

    # A second turn WITHOUT the consent flag still uses memory.
    prepared2 = chat.start_turn(
        PolicyChatCommand(
            user_input="问题二",
            thread_id="chat_ask",
            rag_enabled=True,
            memory_policy="ask",
            operation_id="op_mc2",
        )
    )
    assert prepared2.turn.route_snapshot["external_data_policy"]["memory_allowed"] is True


def test_ask_without_consent_declines_and_audits(tmp_path):
    from src.application.policy_chat_service import PolicyChatCommand

    chat, _ = _policy_service(tmp_path)
    prepared = chat.start_turn(
        PolicyChatCommand(
            user_input="问题",
            thread_id="chat_deny",
            rag_enabled=True,
            memory_policy="ask",
            memory_consent=False,
        )
    )
    execution = prepared.turn.route_snapshot["external_data_policy"]
    assert execution["memory_allowed"] is False
    assert execution["memory_consent"] == "declined"


def test_auto_keeps_legacy_audit_not_required_when_blocked_by_context(tmp_path):
    from src.application.policy_chat_service import PolicyChatCommand

    chat, _ = _policy_service(tmp_path)
    prepared = chat.start_turn(
        PolicyChatCommand(
            user_input="问题",
            thread_id="chat_auto",
            rag_enabled=True,
            memory_policy="auto",
            cloud_context_policy="question_only",
        )
    )
    execution = prepared.turn.route_snapshot["external_data_policy"]
    assert execution["memory_allowed"] is False
    assert execution["memory_consent"] == "not_required"


def test_revoke_endpoint_clears_grant(tmp_path):
    from src.application.session_service import SessionService

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "s.db"))
    repository.ensure_chat_thread("chat_rev")
    repository.grant_session_memory_consent("chat_rev")

    service = SessionService(
        repository,
        current_dir=tmp_path / "current",
        archive_dir=tmp_path / "archive",
    )
    result = service.revoke_memory_consent("chat_rev")

    assert result["memory_consent_granted"] is False
    thread = repository.get_chat_thread("chat_rev")
    assert thread is not None
    assert thread.settings_snapshot.get("memory_consent_granted") is False
