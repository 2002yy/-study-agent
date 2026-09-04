"""Server-owned trigger audit tests (RQ1-C pre-push P0-1).

The research answer-validation plan may only be constructed from a real
ResearchRun resolved server-side. Client requests cannot carry
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
from src.application.chat_service import ChatDependencies, ChatService
from src.application.policy_chat_service import PolicyChatCommand
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.mode_manager import RuntimeModes
from src.pedagogy.evaluation import PedagogyEvaluationService
from src.repositories.runtime_repository import RuntimeRepository
from src.tools.web_agent import WebToolTrace

SOURCE_BLOCK = "研究证据块。"
QUESTION = "该版本发布了吗？"
RESEARCH_CLAIM_ID = "research_claim_1"


def _research_run(
    *,
    brief_rows: list[dict[str, Any]] | None = None,
    context: dict | None = None,
) -> SimpleNamespace:
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
            "conditional_wording_required": False,
            "unresolved_conflicts": [],
            "open_critical_claim_ids": [],
            "open_gap_ids": [],
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
                    "claim_id": RESEARCH_CLAIM_ID,
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
    assert [row["claim_id"] for row in plan["evidence_rows"]] == [RESEARCH_CLAIM_ID]


def test_old_research_run_without_rows_still_triggers_the_gate() -> None:
    """P0-1.4: provenance without binding rows must not bypass validation."""
    service = _FakeResearchService(
        _research_run(context={"claim_engine_metrics": {"candidate_count": 3}})
    )
    command = _chat_command_for(service)
    assert command.research_sources is not None
    plan = command.answer_validation
    assert plan is not None
    assert plan["evidence_rows"] == []


def test_gated_research_run_with_empty_brief_still_triggers_the_gate() -> None:
    service = _FakeResearchService(_research_run(brief_rows=[]))
    command = _chat_command_for(service)
    plan = command.answer_validation
    assert plan is not None and plan["evidence_rows"] == []


def test_plain_tool_loop_run_never_gets_a_validation_plan() -> None:
    """Ordinary web-context chat (tool loop) is not research provenance."""
    service = _FakeResearchService(_plain_run())
    command = _chat_command_for(service)
    assert command.research_sources is not None
    assert command.answer_validation is None


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


def test_plain_chat_service_spoofed_validation_still_needs_server_owned_rows(
    tmp_path,
) -> None:
    """Direct service callers cannot turn empty/spoofed rows into validation."""
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    dependencies = ChatDependencies(
        load_runtime_modes=lambda: RuntimeModes(performance_mode="standard"),
        read_memory_bundle=lambda _mode: {},
        build_role_prompt=lambda _role, **_kwargs: "role",
        route_request=lambda **_kwargs: {
            "role": "nahida",
            "mode": "普通",
            "model_profile": "flash",
            "reason": "test",
        },
        retrieve_local_knowledge=lambda *_args, **_kwargs: SimpleNamespace(
            context="", to_dict=lambda: {"status": "skipped", "results": []}
        ),
        build_messages=lambda **kwargs: [
            {"role": "user", "content": kwargs["user_input"]}
        ],
        chat=lambda *_args, **_kwargs: "reply",
        stream_chat=lambda *_args, **_kwargs: iter(["reply"]),
        chat_max_tokens=lambda _mode: 1000,
        resolve_web_tools=lambda *_args, **_kwargs: WebToolTrace(enabled=False),
        pedagogy_evaluation=PedagogyEvaluationService(),
    )
    service = ChatService(repository, dependencies)
    command = PolicyChatCommand(
        user_input=QUESTION,
        answer_validation={"evidence_rows": [], "allowed_attempts": 1},
    )
    prepared = service.start_turn(command)
    reply = service.generate(prepared)
    assert reply != "reply"
