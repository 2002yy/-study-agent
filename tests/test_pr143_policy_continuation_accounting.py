from __future__ import annotations

from typing import Any

from src.application.chat_service import ChatDependencies
from src.application.policy_chat_service import (
    ExternalDataPolicyChatService,
    PolicyChatCommand,
)
from src.context_builder import build_messages
from src.mode_manager import RuntimeModes
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


def _dependencies() -> ChatDependencies:
    return ChatDependencies(
        load_runtime_modes=lambda: RuntimeModes(performance_mode="fast"),
        read_memory_bundle=lambda _context_mode: {},
        build_role_prompt=lambda role, **_kwargs: f"role prompt for {role}",
        route_request=route_request,
        retrieve_local_knowledge=lambda *_args, **_kwargs: _FakeRagResult(),
        build_messages=build_messages,
        chat=lambda *_args, **_kwargs: "unused",
        stream_chat=lambda *_args, **_kwargs: iter(()),
        chat_max_tokens=lambda _performance_mode: 1000,
    )


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
