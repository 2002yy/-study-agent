"""Regressions for the exact-head PR #143 re-review findings."""

from __future__ import annotations

import json
from typing import Any, Callable

from src.application.answer_claim_binder import _segment_answer
from src.application.chat_service import ChatCommand, ChatDependencies, ChatService
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.mode_manager import RuntimeModes
from src.pedagogy.evaluation import PedagogyEvaluationService
from src.repositories.runtime_repository import RuntimeRepository
from src.tools.web_agent import WebToolTrace


class _FakeRagResult:
    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "found",
            "context": "local",
            "result_count": 0,
            "results": [],
        }


def _row(evidence_id: str, *, claim_id: str = "research-claim-1") -> dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "claim_id": claim_id,
        "title": f"Source {evidence_id}",
        "url": f"https://official.example/{evidence_id}",
        "source_role": "official_statement",
        "source_cluster_id": f"cluster-{evidence_id}",
        "relation": "supports",
        "strength": "strong",
        "locator": "section 1",
        "anchored_spans": ("official confirmation",),
        "caveats": (),
    }


def _binding_payload(evidence_id: str) -> str:
    return json.dumps(
        {
            "refused": False,
            "segments": [
                {
                    "segment_ref": "s1",
                    "kind": "factual",
                    "status": "asserted",
                    "evidence_support": [evidence_id],
                }
            ],
        }
    )


def _dependencies(chat_fn: Callable[..., str]) -> ChatDependencies:
    return ChatDependencies(
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
        retrieve_local_knowledge=lambda *args, **kwargs: _FakeRagResult(),
        build_messages=lambda **kwargs: [
            {"role": "system", "content": kwargs["role_prompt"]},
            {"role": "user", "content": kwargs["user_input"]},
        ],
        chat=chat_fn,
        stream_chat=lambda *args, **kwargs: iter(()),
        chat_max_tokens=lambda performance_mode: 1000,
        resolve_web_tools=lambda *args, **kwargs: WebToolTrace(enabled=False),
        pedagogy_evaluation=PedagogyEvaluationService(),
    )


def _service(tmp_path, chat_fn: Callable[..., str]) -> tuple[ChatService, RuntimeRepository]:
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    return ChatService(repository, _dependencies(chat_fn)), repository


def _command(
    *,
    rows: list[dict[str, Any]],
    continuation_of_turn_id: str | None = None,
    partial_reply: str = "",
) -> ChatCommand:
    return ChatCommand(
        user_input="这个版本发布了吗？",
        selected_role="nahida",
        web_context="source block",
        web_context_run_id="web_lookup_1",
        continuation_of_turn_id=continuation_of_turn_id,
        partial_reply=partial_reply,
        answer_validation={"evidence_rows": rows, "allowed_attempts": 1},
    )


def test_segmenter_keeps_urls_versions_and_decimals_intact() -> None:
    answer = (
        "See https://docs.python.org/3.12/ and use v3.12. "
        "The measured value is 1.25. Next sentence."
    )

    assert _segment_answer(answer) == (
        "See https://docs.python.org/3.12/ and use v3.12.",
        "The measured value is 1.25.",
        "Next sentence.",
    )


def test_pre_generation_interrupt_does_not_invent_generation_call(tmp_path) -> None:
    evidence_id = "evidence-1"

    def chat_fn(*args: Any, **kwargs: Any) -> str:
        return _binding_payload(evidence_id)

    service, _repository = _service(tmp_path, chat_fn)
    prepared = service.start_turn(_command(rows=[_row(evidence_id)]))

    interrupted = service.interrupt_turn(prepared, "")

    assert interrupted.status == "interrupted"
    assert interrupted.route_snapshot["answer_generation_calls"] == 0


def test_client_partial_commit_cannot_invent_generation_call(tmp_path) -> None:
    evidence_id = "evidence-1"

    def chat_fn(*args: Any, **kwargs: Any) -> str:
        return _binding_payload(evidence_id)

    service, _repository = _service(tmp_path, chat_fn)
    prepared = service.start_turn(_command(rows=[_row(evidence_id)]))

    committed, changed = service.commit_partial_turn(
        thread_id=prepared.thread.id,
        turn_id=prepared.turn.id,
        operation_id=prepared.turn.operation_id or "",
        user_input=prepared.turn.user_message,
        assistant_message="客户端声称已经生成",
        role="forged-role",
        mode="forged-mode",
        model="forged-model",
        route_snapshot={"answer_generation_calls": 999},
        rag_snapshot={"forged": True},
        conversation_instruction="forged",
    )

    assert changed is True
    assert committed.status == "interrupted"
    assert committed.route_snapshot["answer_generation_calls"] == 0


def test_continuation_audit_counts_prior_generation_call(tmp_path) -> None:
    evidence_id = "evidence-1"

    def chat_fn(*args: Any, **kwargs: Any) -> str:
        assert kwargs.get("task_name") == "answer_claim_binding"
        return _binding_payload(evidence_id)

    service, repository = _service(tmp_path, chat_fn)
    first = service.start_turn(_command(rows=[_row(evidence_id)]))
    assert list(service.stream(first)) == []
    interrupted = service.interrupt_turn(first, "版本已经")
    assert interrupted.status == "interrupted"
    assert interrupted.route_snapshot["answer_generation_calls"] == 1

    resumed = service.start_turn(
        _command(
            rows=[_row(evidence_id)],
            continuation_of_turn_id=interrupted.id,
            partial_reply="版本已经",
        )
    )
    assert list(service.stream(resumed)) == []
    completed = service.complete_turn(resumed, "发布。")

    audit = completed.rag_snapshot["answer_validation_audit"]
    generation = audit["phases"]["answer_generation"]
    assert generation["model_calls"] == 2
    assert generation["attempts"] == 2
    assert completed.route_snapshot["answer_generation_calls"] == 2
    assert repository.get_chat_turn(completed.id) == completed


def test_completed_turn_persists_only_binder_linked_evidence(tmp_path) -> None:
    used_id = "evidence-used"
    unused_id = "evidence-unused"

    def chat_fn(*args: Any, **kwargs: Any) -> str:
        assert kwargs.get("task_name") == "answer_claim_binding"
        return _binding_payload(used_id)

    service, _repository = _service(tmp_path, chat_fn)
    prepared = service.start_turn(
        _command(rows=[_row(used_id), _row(unused_id, claim_id="research-claim-2")])
    )
    assert list(service.stream(prepared)) == []
    completed = service.complete_turn(prepared, "版本已经发布。")

    refs = completed.rag_snapshot["research_evidence_refs"]
    assert [ref["evidence_id"] for ref in refs] == [used_id]
    assert [ref["id"] for ref in completed.evidence_snapshot["refs"]] == [used_id]
