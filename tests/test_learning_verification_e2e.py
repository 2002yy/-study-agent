from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

from src.api import app
from src.application.chat_service import ChatDependencies
from src.application.policy_chat_service import (
    ExternalDataPolicyChatService,
    PolicyChatCommand,
)
from src.application.runtime_repository import get_chat_service
from src.context_builder import build_messages
from src.mode_manager import RuntimeModes
from src.pedagogy.evaluation import SemanticEvaluation
from src.repositories.pedagogy_eval_repository import PedagogyEvalRepository
from src.task_contract import (
    TaskAwarePedagogyEngine,
    TaskAwarePedagogyEvaluationService,
    route_request_with_task_contract,
)
from src.tools.web_agent import WebToolTrace


REASONED_BINARY_SEARCH = (
    "所以二分查找每轮把候选范围减半，因此问题规模按一半递减，"
    "查找次数是对数级，因为只需重复减半直到剩一个元素。"
)
MISCONCEPTION_BINARY_SEARCH = (
    "所以二分查找是 O(n)，因为每次只检查一个元素，我明白了。"
)


class EmptyRagResult:
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "skipped",
            "context": "",
            "result_count": 0,
            "results": [],
        }


class EvidenceRagResult:
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "found",
            "context": "binary search halves the candidate range",
            "result_count": 1,
            "results": [
                {
                    "score": 1.0,
                    "chunk": {
                        "chunk_id": "chunk-binary-search",
                        "source_path": "notes/binary-search.md",
                        "start_line": 1,
                        "end_line": 4,
                        "text": "Binary search halves the remaining candidate range.",
                    },
                }
            ],
        }


@dataclass
class ControlledSemanticEvaluator:
    result: SemanticEvaluation | None = None
    error: Exception | None = None
    calls: int = 0

    def evaluate(self, **_kwargs: Any) -> SemanticEvaluation:
        self.calls += 1
        if self.error is not None:
            raise self.error
        if self.result is None:
            raise AssertionError("A semantic result was not configured")
        return self.result


def _semantic_accept(*, evidence_refs: tuple[str, ...] = ()) -> SemanticEvaluation:
    return SemanticEvaluation(
        claims=("候选范围每轮减半", "复杂度是对数级",),
        correct_points=("每次将剩余规模缩小为原来的一半",),
        reasoning_complete=True,
        transfer_ready=True,
        confidence=0.94,
        evidence_refs=evidence_refs,
    )


def _install_service(
    runtime_test_context,
    semantic_evaluator: ControlledSemanticEvaluator,
    *,
    rag_result: EmptyRagResult | EvidenceRagResult | None = None,
) -> ExternalDataPolicyChatService:
    async def async_tokens(*_args: Any, **_kwargs: Any):
        yield "继续完成学习验证。"

    retrieval = rag_result or EmptyRagResult()
    dependencies = ChatDependencies(
        load_runtime_modes=lambda: RuntimeModes(
            performance_mode="fast",
            entry_mode="single",
        ),
        read_memory_bundle=lambda _context_mode: {},
        build_role_prompt=lambda role, **_kwargs: f"role:{role}",
        route_request=route_request_with_task_contract,
        retrieve_local_knowledge=lambda *_args, **_kwargs: retrieval,
        build_messages=build_messages,
        chat=lambda *_args, **_kwargs: "请把这个推理应用到一个新的有序数组。",
        stream_chat=lambda *_args, **_kwargs: iter(("继续", "完成")),
        async_stream_chat=async_tokens,
        chat_max_tokens=lambda _performance_mode: 1000,
        pedagogy_engine=TaskAwarePedagogyEngine(),
        pedagogy_evaluation=TaskAwarePedagogyEvaluationService(
            semantic_evaluator
        ),
        resolve_web_tools=lambda *_args, **_kwargs: WebToolTrace(enabled=False),
    )
    service = ExternalDataPolicyChatService(
        runtime_test_context.repository,
        dependencies,
    )
    app.dependency_overrides[get_chat_service] = lambda: service
    return service


def _learning_payload(
    session_id: str,
    user_input: str,
    *,
    rag_enabled: bool = False,
    turn_id: str | None = None,
    continuation_of_turn_id: str | None = None,
    retry_of_turn_id: str | None = None,
    partial_reply: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "user_input": user_input,
        "selected_mode": "苏格拉底",
        "selected_model": "flash",
        "task_intent": "learn",
        "session_id": session_id,
        "rag_enabled": rag_enabled,
        "web_policy": "off",
        "cloud_context_policy": "allow_local_evidence",
    }
    if turn_id is not None:
        payload["turn_id"] = turn_id
    if continuation_of_turn_id is not None:
        payload["continuation_of_turn_id"] = continuation_of_turn_id
    if retry_of_turn_id is not None:
        payload["retry_of_turn_id"] = retry_of_turn_id
    if partial_reply:
        payload["partial_reply"] = partial_reply
    return payload


def _start_learning(client: TestClient, session_id: str, *, rag_enabled: bool = False):
    response = client.post(
        "/chat",
        json=_learning_payload(
            session_id,
            "带我系统学习二分查找复杂度",
            rag_enabled=rag_enabled,
        ),
    )
    assert response.status_code == 200
    return response.json()


def _evaluation(runtime_test_context, turn_id: str):
    return PedagogyEvalRepository(
        runtime_test_context.repository.database
    ).get_for_turn(turn_id)


def test_reasoned_explanation_commits_and_restores_learning_truth(
    runtime_test_context,
):
    semantic = ControlledSemanticEvaluator(result=_semantic_accept())
    _install_service(runtime_test_context, semantic)
    client = TestClient(app)
    session_id = "learning_accept_e2e"

    _start_learning(client, session_id)
    accepted = client.post(
        "/chat",
        json=_learning_payload(session_id, REASONED_BINARY_SEARCH),
    )

    assert accepted.status_code == 200
    accepted_payload = accepted.json()
    run = _evaluation(runtime_test_context, accepted_payload["turn_id"])
    stored_thread = runtime_test_context.repository.get_chat_thread(session_id)
    assert run is not None
    assert run.final_decision == "accept"
    assert semantic.calls == 1
    assert stored_thread is not None
    assert stored_thread.learning_state["phase"] == "transfer"
    assert stored_thread.learning_state["confirmed_points"] == [
        REASONED_BINARY_SEARCH
    ]

    refreshed = TestClient(app).get(f"/sessions/{session_id}")
    assert refreshed.status_code == 200
    detail = refreshed.json()
    assert detail["learning_state"] == stored_thread.learning_state
    assert detail["navigation"]["phase"] == "transfer"
    assert detail["navigation"]["confirmed_points"] == [
        REASONED_BINARY_SEARCH
    ]
    assert detail["pedagogy"]["committed_learning_state"] == detail[
        "learning_state"
    ]


def test_bare_understanding_and_known_misconception_never_confirm_mastery(
    runtime_test_context,
):
    semantic = ControlledSemanticEvaluator(result=_semantic_accept())
    _install_service(runtime_test_context, semantic)
    client = TestClient(app)

    bare_session = "learning_bare_e2e"
    _start_learning(client, bare_session)
    bare = client.post(
        "/chat",
        json=_learning_payload(bare_session, "懂了"),
    )
    bare_run = _evaluation(runtime_test_context, bare.json()["turn_id"])
    bare_thread = runtime_test_context.repository.get_chat_thread(bare_session)

    assert bare.status_code == 200
    assert bare_run is not None
    assert bare_run.final_decision == "reject"
    assert bare_run.reasons == ("understanding_asserted_without_reasoning",)
    assert bare_thread is not None
    assert bare_thread.learning_state["confirmed_points"] == []

    misconception_session = "learning_misconception_e2e"
    _start_learning(client, misconception_session)
    misconception = client.post(
        "/chat",
        json=_learning_payload(
            misconception_session,
            MISCONCEPTION_BINARY_SEARCH,
        ),
    )
    misconception_run = _evaluation(
        runtime_test_context,
        misconception.json()["turn_id"],
    )
    misconception_thread = runtime_test_context.repository.get_chat_thread(
        misconception_session
    )

    assert misconception.status_code == 200
    assert misconception_run is not None
    assert misconception_run.final_decision == "reject"
    assert misconception_run.deterministic_result["misconceptions"] == [
        "binary_search_linear_complexity"
    ]
    assert misconception_thread is not None
    assert misconception_thread.learning_state["confirmed_points"] == []
    assert misconception_thread.learning_state["unresolved_gap"] == (
        "claim_conflicts_with_known_constraints"
    )
    assert semantic.calls == 0


def test_semantic_failure_blocks_transfer_without_fabricating_mastery(
    runtime_test_context,
):
    semantic = ControlledSemanticEvaluator(error=TimeoutError("provider unavailable"))
    _install_service(runtime_test_context, semantic)
    client = TestClient(app)
    session_id = "learning_semantic_failure_e2e"

    _start_learning(client, session_id)
    attempted = client.post(
        "/chat",
        json=_learning_payload(session_id, REASONED_BINARY_SEARCH),
    )

    assert attempted.status_code == 200
    run = _evaluation(runtime_test_context, attempted.json()["turn_id"])
    thread = runtime_test_context.repository.get_chat_thread(session_id)
    assert run is not None
    assert run.final_decision == "needs_semantic_review"
    assert run.reasons == ("semantic_evaluator_failed:TimeoutError",)
    assert thread is not None
    assert thread.learning_state["phase"] == "orientation"
    assert thread.learning_state["turn_count"] == 1
    assert thread.learning_state["confirmed_points"] == []
    assert thread.learning_state["payload"]["state_advance_blocked"] is True


def test_unknown_evidence_reference_blocks_transfer(runtime_test_context):
    semantic = ControlledSemanticEvaluator(
        result=_semantic_accept(evidence_refs=("invented-evidence",))
    )
    _install_service(
        runtime_test_context,
        semantic,
        rag_result=EvidenceRagResult(),
    )
    client = TestClient(app)
    session_id = "learning_evidence_failure_e2e"

    _start_learning(client, session_id, rag_enabled=True)
    disclosed = client.post(
        "/chat",
        json=_learning_payload(
            session_id,
            "直接告诉我二分查找复杂度的结论",
            rag_enabled=True,
        ),
    )
    assert disclosed.status_code == 200
    disclosed_turn = runtime_test_context.repository.get_chat_turn(
        disclosed.json()["turn_id"]
    )
    assert disclosed_turn is not None
    assert disclosed_turn.pedagogy_snapshot["evidence_units"][0]["source_id"] == (
        "chunk-binary-search"
    )

    attempted = client.post(
        "/chat",
        json=_learning_payload(
            session_id,
            REASONED_BINARY_SEARCH,
            rag_enabled=True,
        ),
    )
    assert attempted.status_code == 200
    run = _evaluation(runtime_test_context, attempted.json()["turn_id"])
    thread = runtime_test_context.repository.get_chat_thread(session_id)
    assert run is not None
    assert run.evidence == ("chunk-binary-search",)
    assert run.final_decision == "reject"
    assert run.reasons == ("unknown_evidence_reference",)
    assert thread is not None
    assert thread.learning_state["confirmed_points"] == []
    assert thread.learning_state["payload"]["state_advance_blocked"] is True


def test_interrupted_continuation_commits_once_and_restores(runtime_test_context):
    semantic = ControlledSemanticEvaluator(result=_semantic_accept())
    service = _install_service(runtime_test_context, semantic)
    client = TestClient(app)
    session_id = "learning_continuation_e2e"

    _start_learning(client, session_id)
    interrupted_prepared = service.start_turn(
        PolicyChatCommand(
            user_input=REASONED_BINARY_SEARCH,
            selected_mode="苏格拉底",
            selected_model="flash",
            task_intent="learn",
            thread_id=session_id,
            turn_id="turn-learning-continuation",
            web_policy="off",
            cloud_context_policy="allow_local_evidence",
        )
    )
    service.interrupt_turn(interrupted_prepared, "部分回答")
    before_continuation = runtime_test_context.repository.get_chat_thread(session_id)
    assert before_continuation is not None
    assert before_continuation.learning_state["phase"] == "orientation"
    assert before_continuation.learning_state["confirmed_points"] == []

    continued = client.post(
        "/chat",
        json=_learning_payload(
            session_id,
            REASONED_BINARY_SEARCH,
            turn_id=interrupted_prepared.turn.id,
            continuation_of_turn_id=interrupted_prepared.turn.id,
            partial_reply="部分回答",
        ),
    )

    assert continued.status_code == 200
    stored_turn = runtime_test_context.repository.get_chat_turn(
        interrupted_prepared.turn.id
    )
    stored_thread = runtime_test_context.repository.get_chat_thread(session_id)
    assert stored_turn is not None
    assert stored_turn.status == "completed"
    assert stored_turn.assistant_message.startswith("部分回答")
    assert stored_thread is not None
    assert stored_thread.learning_state["confirmed_points"] == [
        REASONED_BINARY_SEARCH
    ]
    assert len(runtime_test_context.repository.list_chat_turns(session_id)) == 2

    refreshed = TestClient(app).get(f"/sessions/{session_id}").json()
    assert refreshed["turns"][-1]["turn_id"] == interrupted_prepared.turn.id
    assert refreshed["turns"][-1]["status"] == "completed"
    assert refreshed["learning_state"] == stored_thread.learning_state


def test_failed_retry_uses_new_turn_and_commits_once(runtime_test_context):
    semantic = ControlledSemanticEvaluator(result=_semantic_accept())
    service = _install_service(runtime_test_context, semantic)
    client = TestClient(app)
    session_id = "learning_retry_e2e"

    _start_learning(client, session_id)
    failed_prepared = service.start_turn(
        PolicyChatCommand(
            user_input=REASONED_BINARY_SEARCH,
            selected_mode="苏格拉底",
            selected_model="flash",
            task_intent="learn",
            thread_id=session_id,
            turn_id="turn-learning-failed",
            web_policy="off",
            cloud_context_policy="allow_local_evidence",
        )
    )
    failed = service.fail_turn(failed_prepared)
    assert failed.status == "failed"
    before_retry = runtime_test_context.repository.get_chat_thread(session_id)
    assert before_retry is not None
    assert before_retry.learning_state["confirmed_points"] == []

    retried = client.post(
        "/chat",
        json=_learning_payload(
            session_id,
            REASONED_BINARY_SEARCH,
            retry_of_turn_id=failed.id,
        ),
    )

    assert retried.status_code == 200
    child = runtime_test_context.repository.get_chat_turn(retried.json()["turn_id"])
    parent = runtime_test_context.repository.get_chat_turn(failed.id)
    stored_thread = runtime_test_context.repository.get_chat_thread(session_id)
    assert parent is not None
    assert parent.status == "failed"
    assert child is not None
    assert child.status == "completed"
    assert child.parent_turn_id == parent.id
    assert stored_thread is not None
    assert stored_thread.learning_state["confirmed_points"] == [
        REASONED_BINARY_SEARCH
    ]
    assert len(runtime_test_context.repository.list_chat_turns(session_id)) == 3
