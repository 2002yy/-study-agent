"""Server-owned trigger audit tests (RQ1-C pre-push P0-1).

The research answer-validation plan may only be constructed from a real
ResearchRun resolved server-side.  Client requests cannot carry
``research_sources``/``answer_validation`` at all; plain web-context chat and
tool-loop runs must never be mistaken for research provenance; and a
legitimate old/gated ResearchRun (provenance present, zero eligible binding
rows) must still trigger the gate and fail closed instead of bypassing it.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from src.api.models.chat import ChatRequest
from src.api.routes.chat_routes import _chat_command
from src.application.chat_service import (
    ChatDependencies,
    ChatService,
)
from src.application.policy_chat_service import PolicyChatCommand
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.mode_manager import RuntimeModes
from src.pedagogy.evaluation import PedagogyEvaluationService
from src.repositories.runtime_repository import RuntimeRepository
from src.tools.web_agent import WebToolTrace

SOURCE_BLOCK = "研究证据块。"
QUESTION = "该版本发布了吗？"


def _research_run(*, brief_rows: list[dict[str, Any]] | None = None, context: dict | None = None) -> SimpleNamespace:
    research_context: dict[str, Any] = {
        "run_kind": "standalone",
        "research_mode": "deep",
        "candidate_items": [],
    }
    if context is not None:
        research_context.update(context)
    if brief_rows is not None:
        research_context["claim_engine_evidence_brief"] = {
            "schema_version": "research-evidence-brief-v1",
            "gate_status": "pass",
            "eligible_evidence": brief_rows,
        }
    return SimpleNamespace(
        id="run_research_1",
        status="completed",
        source_block=SOURCE_BLOCK,
        research_context=research_context,
    )


class _FakeResearchService:
    """Duck-typed research service returning one prebuilt run."""

    def __init__(self, run: Any) -> None:
        self.run = run

    def get(self, run_id: str) -> Any:  # type: ignore[no-untyped-def]
        return self.run


def _plain_run() -> SimpleNamespace:
    return SimpleNamespace(
        id="run_tool_1",
        status="completed",
        source_block=SOURCE_BLOCK,
        research_context={
            "run_kind": "chat_tool_loop",
            "research_mode": "standard",
            "candidate_items": [],
            "read_summary": {"attempted": 0},
        },
    )


def _request() -> ChatRequest:
    return ChatRequest(
        user_input=QUESTION,
        web_context=SOURCE_BLOCK,
        web_context_run_id="run_research_1",
    )


def _chat_command_for(service: Any) -> Any:
    from typing import cast

    from src.application.web_lookup_service import WebLookupService

    return _chat_command(_request(), cast(WebLookupService, service))


def test_chat_request_cannot_carry_research_fields() -> None:
    """The HTTP surface has no spoofable research/validation fields."""
    assert "research_sources" not in ChatRequest.model_fields
    assert "answer_validation" not in ChatRequest.model_fields
    assert "evidence_rows" not in ChatRequest.model_fields


def test_research_run_with_rows_builds_full_plan() -> None:
    service = _FakeResearchService(
        _research_run(
            brief_rows=[
                {
                    "evidence_id": "evidence_a1",
                    "title": "Official release",
                    "url": "https://official.example/release",
                    "relation": "supports",
                    "strength": "strong",
                }
            ]
        )
    )
    command = _chat_command_for(service)
    assert command.research_sources is not None
    plan = command.answer_validation
    assert plan is not None and plan["allowed_attempts"] == 1
    assert [row["evidence_id"] for row in plan["evidence_rows"]] == ["evidence_a1"]


def test_old_research_run_without_rows_still_triggers_the_gate() -> None:
    """P0-1.4: provenance without binding rows must not bypass validation."""
    service = _FakeResearchService(
        _research_run(
            context={"claim_engine_metrics": {"candidate_count": 3}}
        )
    )
    command = _chat_command_for(service)
    assert command.research_sources is not None
    plan = command.answer_validation
    assert plan is not None
    assert plan["evidence_rows"] == []  # gate will fail closed


def test_gated_research_run_with_empty_brief_still_triggers_the_gate() -> None:
    service = _FakeResearchService(_research_run(brief_rows=[]))
    command = _chat_command_for(service)
    plan = command.answer_validation
    assert plan is not None and plan["evidence_rows"] == []


def test_plain_tool_loop_run_never_gets_a_validation_plan() -> None:
    """Ordinary web-context chat (tool loop) is not research provenance."""
    service = _FakeResearchService(_plain_run())
    command = _chat_command_for(service)
    assert command.research_sources is not None  # sources remain for UI truth
    assert command.answer_validation is None  # but no research gate


def test_request_without_run_id_has_no_plan() -> None:
    request = ChatRequest(user_input=QUESTION, web_context=SOURCE_BLOCK)
    command = _chat_command(request, None)
    assert command.answer_validation is None
    assert command.research_sources is None


def test_mismatched_source_block_is_rejected_before_planning() -> None:
    from typing import cast

    from src.application.web_lookup_service import WebLookupService

    service = _FakeResearchService(_research_run(brief_rows=[]))
    request = ChatRequest(
        user_input=QUESTION,
        web_context="tampered block",
        web_context_run_id="run_research_1",
    )
    try:
        _chat_command(request, cast(WebLookupService, service))
    except ValueError as exc:
        assert "does not match" in str(exc)
    else:
        raise AssertionError("tampered source block must be rejected")


def test_spoofed_research_sources_field_on_command_never_gates(tmp_path) -> None:
    """A client-shaped command carrying look-alike fields does not gate.

    The service treats ``answer_validation`` as the only plan carrier; a fake
    ``research_sources`` dictionary alone changes nothing (no audit, candidate
    published as an ordinary chat reply).
    """
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    calls = {"count": 0}

    def chat_fn(*args: Any, **kwargs: Any) -> str:
        calls["count"] += 1
        return "ordinary reply"

    dependencies = ChatDependencies(
        load_runtime_modes=lambda: RuntimeModes(
            memory_mode="preview", performance_mode="standard"
        ),
        read_memory_bundle=lambda context_mode: {},
        build_role_prompt=lambda role, **kwargs: f"role:{role}",
        route_request=lambda **kwargs: {
            "role": "nahida",
            "mode": "普通",
            "model_profile": "flash",
            "reason": "test",
        },
        retrieve_local_knowledge=lambda *args, **kwargs: _RagStub(),
        build_messages=lambda **kwargs: [
            {"role": "system", "content": kwargs["role_prompt"]},
            {"role": "user", "content": kwargs["user_input"]},
        ],
        chat=chat_fn,
        stream_chat=lambda *args, **kwargs: iter(["ordinary reply"]),
        chat_max_tokens=lambda performance_mode: 1000,
        resolve_web_tools=lambda *args, **kwargs: WebToolTrace(enabled=False),
        pedagogy_evaluation=PedagogyEvaluationService(),
    )
    service = ChatService(repository, dependencies)
    spoofed = PolicyChatCommand(
        user_input=QUESTION,
        research_sources={  # look-alike: not a real plan carrier
            "run_id": "run_research_1",
            "provider_status": "completed",
            "selected_sources": [],
        },
        answer_validation=None,
    )
    prepared = service.start_turn(spoofed)
    reply = service.generate(prepared)
    assert reply == "ordinary reply"
    assert calls["count"] == 1  # no binder provider call
    turn = repository.get_chat_turn(prepared.turn.id)
    if turn is None:
        raise AssertionError("turn not found")
    assert (turn.rag_snapshot or {}).get("answer_validation_audit") is None


class _RagStub:
    context = ""

    def to_dict(self) -> dict[str, Any]:
        return {"status": "skipped", "context": "", "result_count": 0}
