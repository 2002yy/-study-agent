from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from src.api.models.chat import ChatRequest
from src.api.routes.chat_routes import _chat_command
from src.application.chat_service import ChatDependencies
from src.application.policy_chat_service import (
    ExternalDataPolicyChatService,
    PolicyChatCommand,
)
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.runtime_repository import RuntimeRepository
from src.task_contract import (
    TaskAwarePedagogyEngine,
    TaskAwarePedagogyEvaluationService,
    route_request_with_task_contract,
)
from src.tools.web_agent import WebToolTrace


@dataclass
class _RagResult:
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "disabled",
            "query": "",
            "retrieval_mode": "hybrid",
            "reason": "disabled",
            "context": "",
            "sources": "",
            "result_count": 0,
            "results": [],
            "debug": {},
            "attempts": [],
            "rewritten_query": "",
        }


class _FailingSemanticEvaluator:
    def evaluate(self, **_kwargs):
        raise AssertionError("semantic evaluation must not run for quick answers")


class _ResearchService:
    def __init__(self, run: Any):
        self.run = run

    def get(self, run_id: str):
        if run_id != self.run.id:
            raise ValueError(f"ResearchRun not found: {run_id}")
        return self.run


def _source_records() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = [
        {
            "item": {
                "title": "Official guide",
                "url": "https://example.com/guide",
                "published_at": "2026-07-01",
                "snippet": "must not enter ChatTurn truth",
                "content": "full article must not enter ChatTurn truth",
            },
            "assessment": {
                "source_id": "web_source_1",
                "title": "Official guide",
                "url": "https://example.com/guide",
                "domain": "example.com",
                "source_type": "web",
                "relevance": 0.95,
                "directness": "direct_title",
                "freshness": "reported",
                "selected": True,
                "worth_reading": True,
            },
        }
    ]
    rejected = [
        {
            "item": {
                "title": "Duplicate guide",
                "url": "https://example.com/duplicate",
                "description": "must not enter ChatTurn truth",
            },
            "assessment": {
                "source_id": "web_source_2",
                "title": "Duplicate guide",
                "url": "https://example.com/duplicate",
                "domain": "example.com",
                "source_type": "web",
                "relevance": 0.4,
                "directness": "weak",
                "freshness": "unknown",
                "selected": False,
                "rejection_reason": "duplicate",
                "duplicate_of": "web_source_1",
                "worth_reading": False,
            },
        }
    ]
    return selected, rejected


def _run(*, status: str = "completed", source_block: str = "SOURCE BLOCK"):
    selected, rejected = _source_records()
    return SimpleNamespace(
        id="research-1",
        status=status,
        source_block=source_block,
        provider_status="partial",
        stop_reason="budget_exhausted",
        selected_sources=selected,
        rejected_sources=rejected,
        query_attempts=[{"query": "private query"}],
    )


def _service(tmp_path: Path) -> ExternalDataPolicyChatService:
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    dependencies = ChatDependencies(
        route_request=route_request_with_task_contract,
        read_memory_bundle=lambda _mode: {},
        retrieve_local_knowledge=lambda _query, **_kwargs: _RagResult(),
        resolve_web_tools=lambda _query, **_kwargs: WebToolTrace(),
        build_messages=lambda **kwargs: [
            {"role": "system", "content": kwargs["rag_context"]},
            {"role": "user", "content": kwargs["user_input"]},
        ],
        pedagogy_engine=TaskAwarePedagogyEngine(),
        pedagogy_evaluation=TaskAwarePedagogyEvaluationService(
            _FailingSemanticEvaluator()
        ),
        build_role_prompt=lambda *_args, **_kwargs: "ROLE",
    )
    return ExternalDataPolicyChatService(repository, dependencies)


def test_chat_command_copies_only_sanitized_research_source_truth():
    run = _run()
    command = _chat_command(
        ChatRequest(
            user_input="Use the recovered research",
            task_intent="quick_answer",
            web_context=run.source_block,
            web_context_run_id=run.id,
            web_policy="auto",
        ),
        _ResearchService(run),
    )

    assert command.research_sources is not None
    assert command.research_sources["run_id"] == "research-1"
    assert command.research_sources["provider_status"] == "partial"
    assert command.research_sources["stop_reason"] == "budget_exhausted"
    serialized = repr(command.research_sources)
    assert "snippet" not in serialized
    assert "content" not in serialized
    assert "private query" not in serialized


def test_chat_command_rejects_unusable_or_mismatched_research_run():
    with pytest.raises(ValueError, match="not usable"):
        _chat_command(
            ChatRequest(
                user_input="Use it",
                web_context="SOURCE BLOCK",
                web_context_run_id="research-1",
            ),
            _ResearchService(_run(status="failed")),
        )

    with pytest.raises(ValueError, match="does not match"):
        _chat_command(
            ChatRequest(
                user_input="Use it",
                web_context="TAMPERED SOURCE BLOCK",
                web_context_run_id="research-1",
            ),
            _ResearchService(_run()),
        )


def test_policy_service_persists_research_lifecycle_truth_for_live_and_restore(
    tmp_path: Path,
):
    run = _run()
    command = _chat_command(
        ChatRequest(
            user_input="Use the recovered research",
            session_id="chat-research-truth",
            task_intent="quick_answer",
            web_context=run.source_block,
            web_context_run_id=run.id,
            web_policy="auto",
            cloud_context_policy="allow_local_evidence",
        ),
        _ResearchService(run),
    )
    service = _service(tmp_path)

    prepared = service.start_turn(command)
    stored = service.repository.get_chat_turn(prepared.turn.id)

    assert stored is not None
    assert prepared.rag["research_sources"] == stored.rag_snapshot["research_sources"]
    assert prepared.rag["evidence_snapshot"] == stored.evidence_snapshot
    refs = prepared.rag["evidence_snapshot"]["refs"]
    assert [ref["lifecycle_status"] for ref in refs] == ["selected", "rejected"]
    assert refs[0]["selection_reason"] == "research_run:research-1"
    assert refs[0]["provider_status"] == "partial"
    assert refs[1]["rejection_reason"] == "duplicate"
    assert prepared.rag["research_sources"]["stop_reason"] == "budget_exhausted"


def test_web_policy_block_does_not_persist_research_source_details(tmp_path: Path):
    run = _run()
    command = _chat_command(
        ChatRequest(
            user_input="Use the recovered research",
            session_id="chat-research-blocked",
            task_intent="quick_answer",
            web_context=run.source_block,
            web_context_run_id=run.id,
            web_policy="off",
        ),
        _ResearchService(run),
    )
    service = _service(tmp_path)

    prepared = service.start_turn(command)
    stored = service.repository.get_chat_turn(prepared.turn.id)

    assert "research_sources" not in prepared.rag
    assert stored is not None
    assert "research_sources" not in stored.rag_snapshot
    assert stored.evidence_snapshot["refs"] == []
