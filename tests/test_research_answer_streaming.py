"""Research-backed streaming buffering tests (RQ1-C answer batch).

A research-backed turn buffers the whole candidate until the publication gate
passes; a binding failure therefore emits zero candidate tokens while the
canonical blocked copy is what the learner sees.  Ordinary chat streaming
keeps emitting tokens as they arrive.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from typing import Any, AsyncIterator

from src.api.models.chat import ChatRequest
from src.api.routes.chat_routes import chat_stream_endpoint
from src.application.chat_service import (
    RESEARCH_ANSWER_BLOCKED_COPY,
    ChatDependencies,
    ChatService,
)
from src.context_builder import build_messages
from src.mode_manager import RuntimeModes
from src.router import route_request

EVIDENCE_ID = "evidence_stream_1"


class ConnectedRequest:
    async def is_disconnected(self) -> bool:
        return False


def _row(evidence_id: str = EVIDENCE_ID) -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "title": "Stream release note",
        "url": "https://official.example/stream-release",
        "source_role": "official_statement",
        "source_cluster_id": "cluster_s1",
        "relation": "supports",
        "strength": "strong",
        "locator": "第二段",
        "anchored_spans": ("official confirmation",),
        "caveats": (),
    }


def _payload(claims: list[dict[str, Any]], links: list[dict[str, Any]]) -> str:
    return json.dumps(
        {"refused": False, "claims": claims, "claim_links": links},
        ensure_ascii=False,
    )


def _gate_plan(*, binding_json: str, allowed_attempts: int = 1) -> dict[str, Any]:
    return {
        "evidence_rows": [_row()],
        "allowed_attempts": allowed_attempts,
        "binding_json": binding_json,
    }


def _service(
    runtime_test_context,
    *,
    tokens: tuple[str, ...],
    binding_json: str,
    refuse_binding: bool = False,
    plan: dict[str, Any] | None = None,
    user_input: str = "该版本发布了吗？",
) -> ChatService:
    async def async_tokens(*args: Any, **kwargs: Any) -> AsyncIterator[str]:
        for token in tokens:
            yield token

    effective_plan = plan if plan is not None else _gate_plan(binding_json=binding_json)

    def sync_chat(*args: Any, **kwargs: Any) -> str:
        if kwargs.get("task_name") == "answer_claim_binding":
            if refuse_binding:
                return json.dumps(
                    {"refused": True, "claims": [], "claim_links": []}
                )
            return effective_plan["binding_json"]
        return "".join(tokens)

    service = runtime_test_context.override_chat(
        ChatDependencies(
            load_runtime_modes=lambda: RuntimeModes(performance_mode="fast"),
            read_memory_bundle=lambda context_mode: {},
            build_role_prompt=lambda role, **kwargs: f"role prompt for {role}",
            route_request=route_request,
            retrieve_local_knowledge=lambda *args, **kwargs: _FakeRagResult(),
            build_messages=build_messages,
            chat=sync_chat,
            stream_chat=lambda *args, **kwargs: iter(tokens),
            async_stream_chat=async_tokens,
            chat_max_tokens=lambda performance_mode: 1000,
        )
    )
    original_start_turn = service.start_turn
    plan_marker = dict(effective_plan)

    def gated_start_turn(command: Any) -> Any:
        prepared = original_start_turn(command)
        return replace(
            prepared,
            answer_validation={
                "evidence_rows": plan_marker["evidence_rows"],
                "allowed_attempts": plan_marker["allowed_attempts"],
            },
        )

    service.start_turn = gated_start_turn
    return service


class _FakeRagResult:
    context = ""

    def to_dict(self) -> dict[str, Any]:
        return {"status": "skipped", "context": "", "result_count": 0}


async def _consume(
    service, research_service, session_service, session_id: str, *, user_input: str = "该版本发布了吗？"
) -> str:
    response = await chat_stream_endpoint(
        ChatRequest(user_input=user_input, session_id=session_id),
        ConnectedRequest(),
        service,
        research_service,
        session_service,
    )
    chunks: list[str] = []
    async for chunk in response.body_iterator:
        chunks.append(chunk.decode() if isinstance(chunk, bytes) else chunk)
    return "".join(chunks)


def test_research_stream_passes_binding_and_flushes_once(runtime_test_context) -> None:
    candidate = "该版本已正式发布。"
    service = _service(
        runtime_test_context,
        tokens=("该版本已正式", "发布。"),
        binding_json=_payload(
            [{"id": "c1", "text": candidate, "kind": "factual", "status": "asserted", "source": "provider_structured"}],
            [{"claim_id": "c1", "evidence_id": EVIDENCE_ID, "support_type": "direct_support", "confidence": 0.9}],
        ),
    )
    body = asyncio.run(
        _consume(
            service,
            runtime_test_context.web_lookup_service,
            runtime_test_context.session_service,
            "stream-pass-session",
        )
    )
    # The verified candidate arrives as exactly one token event followed by
    # the done payload; no partial candidate chunk preceded validation.
    assert body.count("event: token") == 1
    assert body.count(candidate) == 2  # one token event + done reply
    assert body.index('event: done') > body.index(candidate)


def test_research_stream_binding_failure_emits_zero_candidate_tokens(
    runtime_test_context,
) -> None:
    candidate = "该版本已正式发布。"
    service = _service(
        runtime_test_context,
        tokens=("该版本已正式", "发布。"),
        binding_json="",
        refuse_binding=True,
    )
    body = asyncio.run(
        _consume(
            service,
            runtime_test_context.web_lookup_service,
            runtime_test_context.session_service,
            "stream-reject-session",
        )
    )
    assert candidate not in body  # zero candidate chunks reached the learner
    assert RESEARCH_ANSWER_BLOCKED_COPY in body
    assert 'event: done' in body


def test_plain_stream_keeps_emitting_tokens_immediately(runtime_test_context) -> None:
    service = runtime_test_context.override_chat(
        ChatDependencies(
            load_runtime_modes=lambda: RuntimeModes(performance_mode="fast"),
            read_memory_bundle=lambda context_mode: {},
            build_role_prompt=lambda role, **kwargs: f"role prompt for {role}",
            route_request=route_request,
            retrieve_local_knowledge=lambda *args, **kwargs: _FakeRagResult(),
            build_messages=build_messages,
            chat=lambda *args, **kwargs: "unused",
            stream_chat=lambda *args, **kwargs: iter(("part", " two")),
            async_stream_chat=lambda *args, **kwargs: _async_iter(("part", " two")),
            chat_max_tokens=lambda performance_mode: 1000,
        )
    )
    body = asyncio.run(
        _consume(
            service,
            runtime_test_context.web_lookup_service,
            runtime_test_context.session_service,
            "plain-stream-session",
        )
    )
    assert 'event: token' in body
    assert "part" in body and " two" in body
    assert 'event: done' in body


async def _async_iter(values: tuple[str, ...]) -> AsyncIterator[str]:
    for value in values:
        yield value
