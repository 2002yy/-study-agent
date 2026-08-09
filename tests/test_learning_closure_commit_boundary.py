from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.application.learning_closure_service import LearningClosureService
from src.application.memory_service import MemoryService
from src.application.session_service import SessionService
from src.domain.runtime_entities import ChatThread, ChatTurn
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.learning_closure_repository import LearningClosureRepository
from src.repositories.memory_repository import MemoryRepository
from src.repositories.runtime_repository import RuntimeRepository


class RecordingTruthCommitter:
    def __init__(self, *, fail: bool = False, status: str = "claim_validated"):
        self.fail = fail
        self.status = status
        self.calls = []

    def commit(self, run):
        self.calls.append(run.id)
        if self.fail:
            raise RuntimeError("durable truth unavailable")
        return SimpleNamespace(status=self.status)


def _task_contract() -> dict:
    return {
        "task_intent": "learn",
        "source_policy": "local_and_web",
        "closure_eligibility": "learning_summary",
        "learning_state_enabled": True,
        "confidence": "high",
    }


def _memory_candidate_result() -> dict:
    return {
        "candidates": [
            {
                "target": "progress",
                "content": "本轮形成了一个待持久化的学习整理。",
                "confidence": "medium",
                "source_refs": ["learning_state.objective"],
                "evaluation_refs": [],
                "learner_pending": False,
            }
        ],
        "durable_learning_candidate": None,
    }


def _durable_only_result() -> dict:
    return {
        "candidates": [],
        "durable_learning_candidate": {
            "source_ref": "github_source:turn-1:0",
            "claim_text": "恢复 durable learning state 不需要重放完整聊天 turns。",
            "claim_kind": "invariant",
            "scope": "project",
            "next_step": "刷新后检查同一 Goal 是否仍可读取。",
            "evaluation_id": "eval-1",
            "evaluation_turn_id": "turn-1",
        },
    }


def _build_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    truth_committer: RecordingTruthCommitter,
    *,
    generated_result: dict | None = None,
):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    runtime = RuntimeRepository(database)
    thread = runtime.create_chat_thread(
        ChatThread(
            id="thread-1",
            learning_state={
                "protocol": "socratic_rediscovery",
                "objective": "理解 durable resume",
                "phase": "guided_practice",
            },
        )
    )
    runtime.add_chat_turn(
        ChatTurn(
            id="turn-1",
            thread_id=thread.id,
            user_message="为什么恢复不需要重放 turns？",
            assistant_message="因为 durable learning truth 是恢复 owner。",
            status="completed",
            role="nahida",
            mode="socratic",
            model="pro",
            route_snapshot={"task_contract": _task_contract()},
            pedagogy_snapshot={"phase": "guided_practice"},
        )
    )
    session = SessionService(
        runtime,
        current_dir=tmp_path / "current",
        archive_dir=tmp_path / "archive",
    )
    memory = MemoryService(MemoryRepository(database))
    modes = SimpleNamespace(
        memory_mode="confirm",
        safe_mode=False,
        profile=SimpleNamespace(memory_write_reason=""),
    )
    monkeypatch.setattr(
        "src.application.memory_service.load_runtime_modes", lambda: modes
    )
    monkeypatch.setattr(
        "src.application.memory_service.is_memory_write_allowed", lambda _modes: True
    )

    frozen_result = generated_result or _memory_candidate_result()

    def generator(*_args, **_kwargs):
        return frozen_result

    service = LearningClosureService(
        LearningClosureRepository(database),
        session,
        memory,
        learning_truth_committer=truth_committer,
        generator=generator,
        memory_bundle_loader=lambda _mode: {},
    )
    return service, runtime, memory


def _allow_memory_write(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    written = tmp_path / "written.md"
    monkeypatch.setattr(
        "src.memory_writer.write_current_focus", lambda _content: written
    )
    monkeypatch.setattr(
        "src.memory_writer.append_memory",
        lambda _target, _content, learner_pending=False: written,
    )


def test_preview_and_ordinary_closure_generation_do_not_write_durable_truth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    truth = RecordingTruthCommitter()
    service, _runtime, _memory = _build_service(tmp_path, monkeypatch, truth)

    preview = service.create_and_execute("thread-1")

    assert preview.status == "preview_ready"
    assert truth.calls == []


def test_explicit_commit_writes_durable_truth_once_before_memory_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    truth = RecordingTruthCommitter()
    service, _runtime, _memory = _build_service(tmp_path, monkeypatch, truth)
    _allow_memory_write(monkeypatch, tmp_path)
    preview = service.create_and_execute("thread-1")

    completed = service.commit(preview.id)
    repeated = service.commit(preview.id)

    assert completed.status == "completed"
    assert repeated.status == "completed"
    assert truth.calls == [preview.id]


def test_durable_only_candidate_reaches_preview_without_fabricated_memory_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    truth = RecordingTruthCommitter()
    service, _runtime, _memory = _build_service(
        tmp_path,
        monkeypatch,
        truth,
        generated_result=_durable_only_result(),
    )

    preview = service.create_and_execute("thread-1")

    assert preview.status == "preview_ready"
    assert preview.memory_run_id is None
    assert truth.calls == []

    completed = service.commit(preview.id)
    repeated = service.commit(preview.id)

    assert completed.status == "completed"
    assert completed.memory_run_id is None
    assert repeated.status == "completed"
    assert truth.calls == [preview.id]


def test_durable_candidate_rejection_fails_closure_instead_of_silently_completing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    truth = RecordingTruthCommitter(status="candidate_claim_mismatch")
    service, _runtime, _memory = _build_service(
        tmp_path,
        monkeypatch,
        truth,
        generated_result=_durable_only_result(),
    )
    preview = service.create_and_execute("thread-1")

    failed = service.commit(preview.id)

    assert failed.status == "failed"
    assert failed.reason == "learning_truth_commit_failed"
    assert "candidate_claim_mismatch" in failed.error
    assert truth.calls == [preview.id]


def test_truth_failure_stops_before_memory_commit_and_has_distinct_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    truth = RecordingTruthCommitter(fail=True)
    service, _runtime, memory = _build_service(tmp_path, monkeypatch, truth)
    preview = service.create_and_execute("thread-1")
    assert preview.memory_run_id is not None

    failed = service.commit(preview.id)

    assert failed.status == "failed"
    assert failed.reason == "learning_truth_commit_failed"
    assert "durable truth unavailable" in failed.error
    assert truth.calls == [preview.id]
    assert memory.get(preview.memory_run_id).status == "previewed"


def test_source_current_guard_runs_before_durable_truth_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    truth = RecordingTruthCommitter()
    service, runtime, _memory = _build_service(tmp_path, monkeypatch, truth)
    preview = service.create_and_execute("thread-1")
    runtime.add_chat_turn(
        ChatTurn(
            id="turn-new",
            thread_id="thread-1",
            user_message="新的完成回合",
            assistant_message="使 closure source 失效",
            status="completed",
            role="nahida",
            mode="socratic",
            model="pro",
            route_snapshot={"task_contract": _task_contract()},
        )
    )

    failed = service.commit(preview.id)

    assert failed.status == "failed"
    assert failed.reason == "thread_source_changed"
    assert truth.calls == []
