"""Deterministic FastAPI entrypoint for real-stack browser gates.

This module keeps the production HTTP routes, application services and SQLite
repositories intact while replacing only external model, memory and retrieval
gateways. It must never be used as the normal application entrypoint.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from dataclasses import asdict
from functools import lru_cache
from pathlib import Path
from typing import Any, AsyncIterator, Iterator

ROOT = Path(__file__).resolve().parents[1]
E2E_ROOT = Path(
    os.getenv(
        "STUDY_AGENT_E2E_ROOT",
        str(ROOT / "frontend" / "test-results" / "real-stack-runtime"),
    )
).resolve()

if os.getenv("STUDY_AGENT_E2E_RESET", "").strip() == "1":
    shutil.rmtree(E2E_ROOT, ignore_errors=True)
E2E_ROOT.mkdir(parents=True, exist_ok=True)

# These values must be fixed before importing the application assembly point.
os.environ["STUDY_AGENT_API_TOKEN"] = ""
os.environ.setdefault("STUDY_AGENT_RUNTIME_DB", str(E2E_ROOT / "runtime.db"))
os.environ.setdefault(
    "STUDY_AGENT_CURRENT_EXPORT_DIR", str(E2E_ROOT / "current")
)
os.environ.setdefault(
    "STUDY_AGENT_ARCHIVE_EXPORT_DIR", str(E2E_ROOT / "archive")
)

from fastapi import HTTPException

from src.api.app import app
from src.application.chat_service import ChatDependencies
from src.application.policy_chat_service import ExternalDataPolicyChatService
from src.application.runtime_repository import (
    get_chat_service,
    get_runtime_repository,
    runtime_database_path,
)
from src.context_builder import build_messages
from src.mode_manager import RuntimeModes
from src.pedagogy.evaluation import SemanticEvaluation
from src.task_contract import (
    TaskAwarePedagogyEngine,
    TaskAwarePedagogyEvaluationService,
    route_request_with_task_contract,
)
from src.tools.web_agent import WebToolTrace

FIRST_REPLY = (
    "我们先建立目标：理解为什么二分查找是 O(log n)。"
    "请说明每一轮会怎样改变候选区间？"
)
BARE_REPLY = "只说“懂了”还不足以确认掌握。请用因果关系解释候选区间怎样变化？"
CORRECT_REPLY = "这段解释已经通过理解验证；下一步把减半过程迁移到查找次数估算。"


class EmptyRagResult:
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "skipped",
            "query": "",
            "retrieval_mode": "",
            "reason": "real_stack_deterministic_gateway",
            "context": "",
            "sources": "",
            "result_count": 0,
            "results": [],
            "debug": {},
            "attempts": [],
            "rewritten_query": "",
        }


class DeterministicSemanticEvaluator:
    """Accept only the explicit reasoned binary-search explanation used by E2E."""

    def evaluate(
        self,
        *,
        learner_input: str,
        objective: str,
        protocol: str,
        expected_concepts: tuple[str, ...],
        evidence: tuple[str, ...],
    ) -> SemanticEvaluation:
        del objective, protocol, expected_concepts, evidence
        compact = learner_input.lower().replace(" ", "")
        accepted = (
            "每轮" in learner_input
            and ("减半" in learner_input or "一半" in learner_input)
            and ("对数" in learner_input or "o(logn)" in compact)
        )
        if accepted:
            return SemanticEvaluation(
                claims=("候选区间每轮减半", "查找次数是对数级"),
                correct_points=("每次将剩余问题规模缩小为原来的一半",),
                reasoning_complete=True,
                transfer_ready=True,
                confidence=0.96,
            )
        return SemanticEvaluation(
            claims=(learner_input.strip(),) if learner_input.strip() else (),
            gaps=("需要说明区间缩小与复杂度之间的因果关系",),
            reasoning_complete=False,
            transfer_ready=False,
            confidence=0.35,
        )


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content", ""))
    return ""


def _reply_for(messages: list[dict[str, Any]]) -> str:
    user_input = _last_user_message(messages).strip()
    if user_input.rstrip("。！？.! ") == "懂了":
        return BARE_REPLY
    compact = user_input.lower().replace(" ", "")
    if (
        "每轮" in user_input
        and ("减半" in user_input or "一半" in user_input)
        and ("对数" in user_input or "o(logn)" in compact)
    ):
        return CORRECT_REPLY
    return FIRST_REPLY


def _chunks(text: str, size: int = 12) -> tuple[str, ...]:
    return tuple(text[index : index + size] for index in range(0, len(text), size))


def _chat(messages: list[dict[str, Any]], **_kwargs: Any) -> str:
    return _reply_for(messages)


def _stream_chat(
    messages: list[dict[str, Any]], **_kwargs: Any
) -> Iterator[str]:
    yield from _chunks(_reply_for(messages))


async def _async_stream_chat(
    messages: list[dict[str, Any]], **_kwargs: Any
) -> AsyncIterator[str]:
    for chunk in _chunks(_reply_for(messages)):
        await asyncio.sleep(0.003)
        yield chunk


@lru_cache(maxsize=1)
def _real_stack_chat_service() -> ExternalDataPolicyChatService:
    dependencies = ChatDependencies(
        load_runtime_modes=lambda: RuntimeModes(
            performance_mode="fast",
            entry_mode="single",
        ),
        read_memory_bundle=lambda _context_mode: {},
        build_role_prompt=lambda role, **_kwargs: f"role:{role}",
        route_request=route_request_with_task_contract,
        retrieve_local_knowledge=lambda *_args, **_kwargs: EmptyRagResult(),
        build_messages=build_messages,
        chat=_chat,
        stream_chat=_stream_chat,
        async_stream_chat=_async_stream_chat,
        chat_max_tokens=lambda _performance_mode: 1000,
        pedagogy_engine=TaskAwarePedagogyEngine(),
        pedagogy_evaluation=TaskAwarePedagogyEvaluationService(
            DeterministicSemanticEvaluator()
        ),
        resolve_web_tools=lambda *_args, **_kwargs: WebToolTrace(enabled=False),
    )
    return ExternalDataPolicyChatService(get_runtime_repository(), dependencies)


app.dependency_overrides[get_chat_service] = _real_stack_chat_service


@app.get("/__e2e__/state/{session_id}")
def read_real_stack_state(session_id: str) -> dict[str, Any]:
    """Expose raw durable truth only from this dedicated test entrypoint."""

    repository = get_runtime_repository()
    thread = repository.get_chat_thread(session_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "database_path": str(runtime_database_path()),
        "thread": asdict(thread),
        "turns": [asdict(turn) for turn in repository.list_chat_turns(session_id)],
    }
