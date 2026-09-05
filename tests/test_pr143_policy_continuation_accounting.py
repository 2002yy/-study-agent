from __future__ import annotations

from typing import Any

from src.application.chat_service import ChatDependencies
from src.application.policy_chat_service import (
    ExternalDataPolicyChatService,
    PolicyChatCommand,
)
from src.context_builder import build_messages
from src.mode_manager import RuntimeModes
from src.pedagogy.engine import PedagogyEngine
from src.pedagogy.evaluation import PedagogyEvaluationService
from src.router import route_request


class _FakeRagResult:
    context = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "skipped",
            "context": "",
            "result_count": 0,
            "results": [],
        }


class _PolicyPedagogyEvaluation(PedagogyEvaluationService):
    def evaluate_learner(self, **kwargs: Any) -> Any:
        kwargs.pop("task_contract", None)
        kwargs.pop("semantic_review_allowed", None)
        return super().evaluate_learner(**kwargs)


class _PolicyPedagogyEngine(PedagogyEngine):
    def plan(self, **kwargs: Any) -> Any:
        kwargs.pop("task_contract", None)
        return super().plan(**kwargs)


def _policy_route_request(**kwargs: Any) -> dict[str, Any]:
    kwargs.pop("task_contract", None)
    return route_request(**kwargs)


def _dependencies() -> ChatDependencies:
    return ChatDependencies(
        load_runtime_modes=lambda: RuntimeModes(performance_mode="fast"),
        read_memory_bundle=lambda _context_mode: {},
        build_role_prompt=lambda role, **_kwargs: f"role prompt for {role}",
        route_request=_policy_route_request,
        retrieve_local_knowledge=lambda *_args, **_kwargs: _FakeRagResult(),
        build_messages=build_messages,
        chat=lambda *_args, **_kwargs: "unused",
        stream_chat=lambda *_args, **_kwargs: iter(()),
        chat_max_tokens=lambda _performance_mode: 1000,
        pedagogy_engine=_PolicyPedagogyEngine(),
        pedagogy_evaluation=_PolicyPedagogyEvaluation(),
    )


def _answer_generation_calls(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    policy = snapshot.get("external_data_policy")
    if not isinstance(policy, dict):
        return []
    return [
        item
        for item in policy.get("external_calls", [])
        if isinstance(item, dict) and item.get("purpose") == "answer_generation"
    ]


def _start_policy_turn(runtime_test_context, *, suffix: str):
    service = ExternalDataPolicyChatService(
        runtime_test_context.repository,
        _dependencies(),
    )
    prepared = service.start_turn(
        PolicyChatCommand(
            user_input="继续回答这个问题。",
            thread_id=f"policy-egress-session-{suffix}",
            turn_id=f"policy-egress-turn-{suffix}",
            web_policy="off",
            memory_policy="off",
        )
    )
    return service, prepared


def test_policy_generation_egress_commits_with_start_reservation(
    runtime_test_context,
) -> None:
    service, prepared = _start_policy_turn(runtime_test_context, suffix="commit")

    service._record_answer_call(prepared, "attempted")
    before = runtime_test_context.repository.get_chat_turn(prepared.turn.id)
    assert before is not None
    assert before.route_snapshot["answer_generation_calls"] == 0
    assert _answer_generation_calls(before.route_snapshot) == []
    assert _answer_generation_calls(before.rag_snapshot) == []

    assert service._begin_generation_call(prepared) is True

    durable = runtime_test_context.repository.get_chat_turn(prepared.turn.id)
    assert durable is not None
    assert durable.route_snapshot["answer_generation_calls"] == 1
    route_calls = _answer_generation_calls(durable.route_snapshot)
    rag_calls = _answer_generation_calls(durable.rag_snapshot)
    assert len(route_calls) == 1
    assert len(rag_calls) == 1
    assert route_calls[0]["status"] == "attempted"
    assert rag_calls[0]["status"] == "attempted"


def test_policy_cancel_before_generation_reservation_records_no_egress(
    runtime_test_context,
) -> None:
    service, prepared = _start_policy_turn(runtime_test_context, suffix="cancel")

    service._record_answer_call(prepared, "attempted")
    outcome, _turn = runtime_test_context.repository.request_turn_cancel(
        prepared.turn.id,
        expected_operation_id=prepared.turn.operation_id or "",
    )
    assert outcome == "accepted"

    assert service._begin_generation_call(prepared) is False

    durable = runtime_test_context.repository.get_chat_turn(prepared.turn.id)
    assert durable is not None
    assert durable.route_snapshot["answer_generation_calls"] == 0
    assert _answer_generation_calls(durable.route_snapshot) == []
    assert _answer_generation_calls(durable.rag_snapshot) == []


def test_policy_continuation_carries_prior_generation_calls(runtime_test_context) -> None:
    service = ExternalDataPolicyChatService(
        runtime_test_context.repository,
        _dependencies(),
    )
    thread_id = "policy-continuation-count-session"
    turn_id = "policy-continuation-count-turn"

    first = service.start_turn(
        PolicyChatCommand(
            user_input="继续回答这个问题。",
            thread_id=thread_id,
            turn_id=turn_id,
            web_policy="off",
            memory_policy="off",
        )
    )
    assert first.route["answer_generation_calls"] == 0
    assert service._begin_generation_call(first) is True
    interrupted = service.interrupt_turn(first, "第一段")
    assert interrupted.route_snapshot["answer_generation_calls"] == 1

    continued = service.start_turn(
        PolicyChatCommand(
            user_input="ignored on continuation",
            thread_id=thread_id,
            continuation_of_turn_id=turn_id,
            partial_reply="第一段",
            web_policy="off",
            memory_policy="off",
        )
    )

    assert continued.is_continuation is True
    assert continued.route["answer_generation_calls"] == 1
    assert continued.turn.route_snapshot["answer_generation_calls"] == 1
    assert service._begin_generation_call(continued) is True
    assert continued.route["answer_generation_calls"] == 2

    durable = runtime_test_context.repository.get_chat_turn(turn_id)
    assert durable is not None
    assert durable.route_snapshot["answer_generation_calls"] == 2
