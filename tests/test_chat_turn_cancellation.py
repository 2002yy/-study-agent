"""G12 ChatTurn cooperative cancellation — repository, service and fence tests.

Contract: docs/PROJECT_STATUS.md section 10.4 (decisions 1-24), acceptance
matrix in 10.6. These tests use the real RuntimeRepository against a temporary
SQLite database; only the chat dependencies are faked.
"""

from __future__ import annotations

import threading
from dataclasses import replace

import pytest

from src.application.chat_service import (
    ChatCommand,
    ChatDependencies,
    ChatService,
    TurnCancelled,
)
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.mode_manager import RuntimeModes
from src.repositories.runtime_repository import RuntimeRepository
from src.tools.web_agent import WebToolTrace


class FakeRagResult:
    context = "local context"

    def to_dict(self):
        return {
            "status": "found",
            "context": self.context,
            "result_count": 1,
            "results": [],
        }


def _dependencies(
    *,
    retrieve=None,
    stream_tokens: tuple[str, ...] = ("part", " two"),
    chat_reply: str = "complete reply",
) -> ChatDependencies:
    return ChatDependencies(
        load_runtime_modes=lambda: RuntimeModes(
            memory_mode="preview",
            performance_mode="standard",
        ),
        read_memory_bundle=lambda context_mode: {},
        build_role_prompt=lambda role, **kwargs: f"role:{role}",
        route_request=lambda **kwargs: {
            "role": "nahida",
            "mode": "普通",
            "model_profile": "flash",
            "reason": "test",
        },
        retrieve_local_knowledge=retrieve or (lambda *args, **kwargs: FakeRagResult()),
        build_messages=lambda **kwargs: [
            {"role": "system", "content": kwargs["role_prompt"]},
            {"role": "user", "content": kwargs["user_input"]},
        ],
        chat=lambda *args, **kwargs: chat_reply,
        stream_chat=lambda *args, **kwargs: iter(stream_tokens),
        chat_max_tokens=lambda performance_mode: 1000,
        resolve_web_tools=lambda *args, **kwargs: WebToolTrace(enabled=False),
    )


def _service(tmp_path, dependencies: ChatDependencies | None = None):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    service = ChatService(repository, dependencies or _dependencies())
    return service, repository


# ---------------------------------------------------------------------------
# Repository-level cancellation primitives
# ---------------------------------------------------------------------------


def test_request_turn_cancel_not_found_before_reservation(tmp_path):
    service, repository = _service(tmp_path)
    outcome, turn = repository.request_turn_cancel(
        "turn_missing", expected_operation_id="op_missing"
    )
    assert outcome == "not_found"
    assert turn is None


def test_request_turn_cancel_accepted_and_settles_to_cancelled(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="question", thread_id="chat_c", operation_id="op_1")
    )
    outcome, turn = repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id="op_1"
    )
    assert outcome == "accepted"
    assert turn.cancel_requested_at is not None

    settled = repository.finish_turn_cancel(
        prepared.turn.id,
        operation_id="op_1",
        stage="retrieval",
        reason="user_cancelled",
        assistant_message="",
    )
    assert settled is not None
    assert settled.status == "cancelled"
    assert settled.cancel_stage == "retrieval"
    thread = repository.get_chat_thread("chat_c")
    assert thread.active_operation_id is None


def test_finish_cancel_with_partial_settles_to_interrupted(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="question", thread_id="chat_p", operation_id="op_2")
    )
    repository.request_turn_cancel(prepared.turn.id, expected_operation_id="op_2")
    settled = repository.finish_turn_cancel(
        prepared.turn.id,
        operation_id="op_2",
        stage="generation",
        reason="user_cancelled",
        assistant_message="partial answer",
    )
    assert settled is not None
    assert settled.status == "interrupted"
    assert settled.assistant_message == "partial answer"


def test_request_cancel_after_completed_returns_already_completed(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(ChatCommand(user_input="q", thread_id="chat_done"))
    service.complete_turn(prepared, "done")
    outcome, turn = repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id=prepared.turn.operation_id
    )
    assert outcome == "already_completed"
    assert turn.status == "completed"


def test_request_cancel_operation_mismatch_rejected(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_m", operation_id="op_real")
    )
    outcome, turn = repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id="op_other"
    )
    assert outcome == "operation_mismatch"
    # No cancel marker may be written by a mismatched request.
    current = repository.get_chat_turn(prepared.turn.id)
    assert current.cancel_requested_at is None


def test_duplicate_cancel_is_idempotent(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_i", operation_id="op_i")
    )
    first = repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id="op_i"
    )
    second = repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id="op_i"
    )
    assert first[0] == "accepted"
    assert second[0] == "accepted"


# ---------------------------------------------------------------------------
# Monotonic fence (G12 decision 6): accepted-cancel operations cannot advance
# ---------------------------------------------------------------------------


def test_fence_blocks_streaming_update_after_accepted_cancel(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_f1", operation_id="op_f1")
    )
    repository.request_turn_cancel(prepared.turn.id, expected_operation_id="op_f1")
    with pytest.raises(ValueError):
        repository.update_chat_turn(
            prepared.turn.id,
            assistant_message="late write",
            status="streaming",
            expected_status="pending",
            enforce_operation_owner=True,
            expected_operation_id="op_f1",
            forbid_cancel_requested=True,
        )


def test_fence_blocks_completion_after_accepted_cancel(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_f2", operation_id="op_f2")
    )
    assert prepared.turn.status == "streaming"
    repository.request_turn_cancel(prepared.turn.id, expected_operation_id="op_f2")
    with pytest.raises(ValueError):
        service.complete_turn(prepared, "late completion")
    # The fence kept the turn from completing; it stays streaming with the
    # cancel marker until a cancel settlement or stale recovery closes it out.
    current = repository.get_chat_turn(prepared.turn.id)
    assert current.status == "streaming"
    assert current.cancel_requested_at is not None


def test_completion_race_wins_over_cancel(tmp_path):
    """If completed commits first, the cancel must report already_completed."""
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_race", operation_id="op_race")
    )
    # Simulate completion winning the race before the cancel is registered.
    service.complete_turn(prepared, "won")
    outcome, turn = repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id="op_race"
    )
    assert outcome == "already_completed"
    finished = repository.finish_turn_cancel(
        prepared.turn.id,
        operation_id="op_race",
        stage="generation",
        reason="user_cancelled",
        assistant_message="x",
    )
    assert finished is None


# ---------------------------------------------------------------------------
# start_turn cooperative checkpoints
# ---------------------------------------------------------------------------


def test_preparation_cancel_at_route_checkpoint(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    deps = _dependencies(retrieve=lambda *a, **k: FakeRagResult())
    # Cancel from inside the route dependency: the very first checkpoint.
    holder: dict[str, str] = {}

    def slow_route(**kwargs):
        repository.request_turn_cancel(holder["turn_id"], expected_operation_id=holder["op"])
        return {
            "role": "nahida",
            "mode": "普通",
            "model_profile": "flash",
            "reason": "test",
        }

    deps = replace(deps, route_request=slow_route)
    service = ChatService(repository, deps)
    command = ChatCommand(
        user_input="q", thread_id="chat_cp", operation_id="op_cp", turn_id="turn_cp"
    )
    holder["turn_id"] = command.turn_id
    holder["op"] = command.operation_id
    with pytest.raises(TurnCancelled) as excinfo:
        service.start_turn(command)
    # The cancel registers inside the route dependency; the next checkpoint
    # after it is the pedagogy evaluation gate.
    assert excinfo.value.stage == "pedagogy_evaluate"
    turn = repository.get_chat_turn("turn_cp")
    assert turn.status == "cancelled"
    assert turn.cancel_stage == "pedagogy_evaluate"
    thread = repository.get_chat_thread("chat_cp")
    assert thread.active_operation_id is None


def test_preparation_cancel_at_retrieval_checkpoint(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))

    def cancelling_retrieve(*args, **kwargs):
        return FakeRagResult()

    deps = _dependencies(retrieve=cancelling_retrieve)
    service = ChatService(repository, deps)
    prepared_holder: dict[str, object] = {}

    original_start = ChatService.start_turn

    def spy_start(self, command):
        prepared_holder["command"] = command
        return original_start(self, command)

    # Cancel right before the retrieval call via a wrapping dependency that
    # registers the cancel then performs retrieval; the post-retrieval
    # checkpoint ("web_tools") must observe it and raise.
    def retrieve_then_register(*args, **kwargs):
        result = FakeRagResult()
        repository.request_turn_cancel(
            prepared_holder["turn_id"], expected_operation_id=prepared_holder["op"]
        )
        return result

    deps = replace(deps, retrieve_local_knowledge=retrieve_then_register)
    service = ChatService(repository, deps)
    command = ChatCommand(
        user_input="q", thread_id="chat_cr", operation_id="op_cr", turn_id="turn_cr"
    )
    prepared_holder["turn_id"] = command.turn_id
    prepared_holder["op"] = command.operation_id
    with pytest.raises(TurnCancelled) as excinfo:
        service.start_turn(command)
    assert excinfo.value.stage == "web_tools"
    turn = repository.get_chat_turn("turn_cr")
    assert turn.status == "cancelled"
    assert turn.cancel_stage == "web_tools"


def test_generation_post_check_discards_model_output(tmp_path):
    """Decision 9: the synchronous provider call may return naturally but its
    output must be discarded once the cancel was accepted."""
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    deps = _dependencies(chat_reply="wasted model output")

    command_ref: dict[str, str] = {}

    def chatting(*args, **kwargs):
        repository.request_turn_cancel(
            command_ref["turn_id"], expected_operation_id=command_ref["op"]
        )
        return "wasted model output"

    deps = replace(deps, chat=chatting)
    service = ChatService(repository, deps)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_g", operation_id="op_g", turn_id="turn_g")
    )
    command_ref["turn_id"] = prepared.turn.id
    command_ref["op"] = prepared.turn.operation_id
    with pytest.raises(TurnCancelled) as excinfo:
        service.generate(prepared)
    assert excinfo.value.stage == "generate_post"
    turn = repository.get_chat_turn(prepared.turn.id)
    assert turn.status == "cancelled"
    # The late model output never reached the stored truth.
    assert turn.assistant_message == ""
    assert turn.status != "completed"


def test_generate_pre_check_skips_model_call_entirely(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    called = {"count": 0}

    def chatting(*args, **kwargs):
        called["count"] += 1
        return "should not happen"

    deps = replace(_dependencies(chat_reply="x"), chat=chatting)
    service = ChatService(repository, deps)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_g2", operation_id="op_g2")
    )
    repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id=prepared.turn.operation_id
    )
    with pytest.raises(TurnCancelled) as excinfo:
        service.generate(prepared)
    assert excinfo.value.stage == "generate_pre"
    assert called["count"] == 0


# ---------------------------------------------------------------------------
# Reservation semantics (G12 decision 2)
# ---------------------------------------------------------------------------


def test_turn_is_reserved_before_preparation(tmp_path):
    """The pending row must exist before the route dependency runs."""
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    observed: dict[str, object] = {}

    def route_probe(**kwargs):
        observed["row"] = repository.get_chat_turn(observed["turn_id"])
        return {
            "role": "nahida",
            "mode": "普通",
            "model_profile": "flash",
            "reason": "test",
        }

    deps = replace(_dependencies(), route_request=route_probe)
    service = ChatService(repository, deps)
    command = ChatCommand(
        user_input="q", thread_id="chat_res", operation_id="op_res", turn_id="turn_res"
    )
    observed["turn_id"] = command.turn_id
    service.start_turn(command)
    row = observed["row"]
    assert row is not None
    assert row.status == "pending"
    assert row.operation_id == "op_res"
    assert row.user_message == "q"


def test_reservation_failure_keeps_thread_usable(tmp_path):
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    deps = replace(
        _dependencies(),
        route_request=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    service = ChatService(repository, deps)
    with pytest.raises(RuntimeError):
        service.start_turn(
            ChatCommand(user_input="q", thread_id="chat_fail", operation_id="op_fail", turn_id="turn_fail")
        )
    thread = repository.get_chat_thread("chat_fail")
    assert thread.active_operation_id is None
    # Settlement: the reserved turn did not linger in pending.
    turn = repository.get_chat_turn("turn_fail")
    assert turn.status == "failed"


# ---------------------------------------------------------------------------
# Continuation re-reservation (G12 decision 8: no inheritance of old marks)
# ---------------------------------------------------------------------------


def test_continuation_clears_stale_cancel_marker(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_cont", operation_id="op_c1")
    )
    # Settle a cancellation into interrupted-with-partial, leaving the marker
    # scenario that a continuation must not inherit.
    repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id=prepared.turn.operation_id
    )
    repository.finish_turn_cancel(
        prepared.turn.id,
        operation_id=prepared.turn.operation_id,
        stage="generation",
        reason="user_cancelled",
        assistant_message="kept partial",
    )
    continued = service.start_turn(
        ChatCommand(
            user_input="q",
            thread_id="chat_cont",
            continuation_of_turn_id=prepared.turn.id,
            partial_reply="kept partial",
            operation_id="op_c2",
        )
    )
    assert continued.turn.operation_id == "op_c2"
    assert continued.turn.cancel_requested_at is None
    assert continued.turn.status == "streaming"


# ---------------------------------------------------------------------------
# Stale recovery honours accepted cancellations (restart path)
# ---------------------------------------------------------------------------


def test_stale_recovery_settles_accepted_cancel_to_cancelled(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_stale", operation_id="op_s1")
    )
    repository.request_turn_cancel(
        prepared.turn.id, expected_operation_id=prepared.turn.operation_id
    )
    # Simulate process death: force the operation timestamp into the past.
    import sqlite3

    db_path = tmp_path / "runtime.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        UPDATE chat_threads SET active_operation_started_at = '2000-01-01T00:00:00+00:00'
        WHERE id = 'chat_stale'
        """
    )
    conn.commit()
    conn.close()
    recovered = repository.recover_stale_chat_operations(stale_after_seconds=300)
    assert recovered == 1
    turn = repository.get_chat_turn(prepared.turn.id)
    assert turn.status == "cancelled"
    assert turn.cancel_stage == "recovery"
    thread = repository.get_chat_thread("chat_stale")
    assert thread.active_operation_id is None


def test_stale_recovery_without_cancel_marks_interrupted(tmp_path):
    service, repository = _service(tmp_path)
    prepared = service.start_turn(
        ChatCommand(user_input="q", thread_id="chat_stale2", operation_id="op_s2")
    )
    import sqlite3

    conn = sqlite3.connect(tmp_path / "runtime.db")
    conn.execute(
        """
        UPDATE chat_threads SET active_operation_started_at = '2000-01-01T00:00:00+00:00'
        WHERE id = 'chat_stale2'
        """
    )
    conn.commit()
    conn.close()
    repository.recover_stale_chat_operations(stale_after_seconds=300)
    turn = repository.get_chat_turn(prepared.turn.id)
    assert turn.status == "interrupted"


# ---------------------------------------------------------------------------
# Shared shell between base ChatService and ExternalDataPolicyChatService
# (G12 decision 13)
# ---------------------------------------------------------------------------


def test_policy_service_shares_cancellation_semantics(tmp_path):
    from src.application.policy_chat_service import ExternalDataPolicyChatService
    from src.task_contract import (
        TaskAwarePedagogyEngine,
        TaskAwarePedagogyEvaluationService,
    )

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    base_deps = _dependencies()
    deps = replace(
        base_deps,
        pedagogy_engine=TaskAwarePedagogyEngine(),
        pedagogy_evaluation=TaskAwarePedagogyEvaluationService(
            lambda **kwargs: {"decision": "accept", "reason": "test"}
        ),
        route_request=lambda **kwargs: {
            "role": "nahida",
            "mode": "普通",
            "model_profile": "flash",
            "reason": "test",
        },
    )
    command = ChatCommand(
        user_input="q", thread_id="chat_pol", operation_id="op_pol", turn_id="turn_pol"
    )

    def cancelling_retrieve(*args, **kwargs):
        repository.request_turn_cancel(command.turn_id, expected_operation_id=command.operation_id)
        return FakeRagResult()

    deps = replace(deps, retrieve_local_knowledge=cancelling_retrieve)
    policy_service = ExternalDataPolicyChatService(repository, deps)
    with pytest.raises(TurnCancelled) as excinfo:
        policy_service.start_turn(command)
    assert excinfo.value.stage == "web_tools"
    turn = repository.get_chat_turn("turn_pol")
    assert turn.status == "cancelled"
    thread = repository.get_chat_thread("chat_pol")
    assert thread.active_operation_id is None


def test_policy_service_reserves_before_preparation(tmp_path):
    from src.application.policy_chat_service import ExternalDataPolicyChatService
    from src.task_contract import (
        TaskAwarePedagogyEngine,
        TaskAwarePedagogyEvaluationService,
    )

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    observed: dict[str, object] = {}

    def route_probe(**kwargs):
        observed["row"] = repository.get_chat_turn("turn_polres")
        return {
            "role": "nahida",
            "mode": "普通",
            "model_profile": "flash",
            "reason": "test",
        }

    deps = replace(
        _dependencies(),
        route_request=route_probe,
        pedagogy_engine=TaskAwarePedagogyEngine(),
        pedagogy_evaluation=TaskAwarePedagogyEvaluationService(
            lambda **kwargs: {"decision": "accept", "reason": "test"}
        ),
    )
    service = ExternalDataPolicyChatService(repository, deps)
    command = ChatCommand(
        user_input="q",
        thread_id="chat_polres",
        operation_id="op_polres",
        turn_id="turn_polres",
    )
    service.start_turn(command)
    row = observed["row"]
    assert row is not None
    assert row.status == "pending"
    assert row.operation_id == "op_polres"


# ---------------------------------------------------------------------------
# Concurrency: cancel racing preparation from another thread
# ---------------------------------------------------------------------------


def test_concurrent_cancel_during_slow_retrieval(tmp_path):
    """A slow retrieval plus an external cancel settles to cancelled."""
    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    release = threading.Event()

    def slow_retrieve(*args, **kwargs):
        release.wait(timeout=5.0)
        return FakeRagResult()

    deps = replace(_dependencies(), retrieve_local_knowledge=slow_retrieve)
    service = ChatService(repository, deps)
    command = ChatCommand(
        user_input="q", thread_id="chat_slow", operation_id="op_slow", turn_id="turn_slow"
    )
    errors: list[Exception] = []

    def run_prepare():
        try:
            service.start_turn(command)
        except TurnCancelled:
            pass
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    worker = threading.Thread(target=run_prepare)
    worker.start()
    # Wait until the reserved row exists, then cancel while retrieval blocks.
    deadline = threading.Event()
    for _ in range(100):
        if repository.get_chat_turn("turn_slow") is not None:
            break
        deadline.wait(timeout=0.05)
    outcome, _ = repository.request_turn_cancel(
        "turn_slow", expected_operation_id="op_slow"
    )
    assert outcome == "accepted"
    release.set()
    worker.join(timeout=10)
    assert errors == []
    turn = repository.get_chat_turn("turn_slow")
    assert turn.status == "cancelled"
    assert turn.cancel_stage in {"web_tools", "retrieval"}


# ---------------------------------------------------------------------------
# Phase 2: retrieval-layer cancellation propagation (RAG checkpoints)
# ---------------------------------------------------------------------------


def test_retrieval_layer_raises_retrieval_cancelled(tmp_path):
    """should_cancel=True inside the retrieval chain raises RetrievalCancelled,
    which must propagate out of retrieve_local_knowledge (never swallowed)."""
    import time
    from pathlib import Path

    from src.rag.cancellation import RetrievalCancelled

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))

    def poll_true() -> bool:
        return True

    from src.tools.local_knowledge import retrieve_local_knowledge

    with pytest.raises(RetrievalCancelled):
        retrieve_local_knowledge(
            "explain the rag architecture in detail",
            enabled=True,
            force=True,
            index_path=tmp_path / "missing-index.json",
            should_cancel=poll_true,
        )


def test_slow_retrieval_cancel_settles_with_derivable_latency(tmp_path):
    """Decision 4/11: a cancel accepted during retrieval settles durably and
    the request-to-terminal latency is derivable from persisted timestamps."""
    import time as _time

    repository = RuntimeRepository(RuntimeDatabase(tmp_path / "runtime.db"))
    release = threading.Event()

    def slow_retrieve(*args, **kwargs):
        # Simulate a slow inner stage; the cancel lands while blocked.
        release.wait(timeout=5.0)
        from src.rag.cancellation import RetrievalCancelled

        raise RetrievalCancelled(stage="inner_search")

    deps = replace(_dependencies(), retrieve_local_knowledge=slow_retrieve)
    service = ChatService(repository, deps)
    command = ChatCommand(
        user_input="q", thread_id="chat_lat", operation_id="op_lat", turn_id="turn_lat"
    )
    errors: list[Exception] = []

    def run_prepare():
        try:
            service.start_turn(command)
        except (TurnCancelled, Exception) as exc:
            from src.rag.cancellation import RetrievalCancelled

            if not isinstance(exc, (TurnCancelled, RetrievalCancelled)):
                errors.append(exc)

    worker = threading.Thread(target=run_prepare)
    worker.start()
    for _ in range(100):
        if repository.get_chat_turn("turn_lat") is not None:
            break
        threading.Event().wait(timeout=0.05)
    outcome, turn = repository.request_turn_cancel(
        "turn_lat", expected_operation_id="op_lat"
    )
    assert outcome == "accepted"
    requested_at = turn.cancel_requested_at
    release.set()
    worker.join(timeout=10)
    assert errors == []
    settled = repository.get_chat_turn("turn_lat")
    assert settled.status == "cancelled"
    assert settled.updated_at >= requested_at


def test_retrieval_poll_observes_mid_search_cancel(tmp_path):
    """The should_cancel callable passed into the retrieval chain polls the
    repository; a cancel registered mid-search stops the next checkpoint."""
    from src.rag.cancellation import RetrievalCancelled

    class FlakyIndex:
        pass

    calls = {"n": 0}

    def poll_after_first() -> bool:
        calls["n"] += 1
        return calls["n"] > 1

    from src.tools.local_knowledge import retrieve_local_knowledge

    with pytest.raises(RetrievalCancelled):
        retrieve_local_knowledge(
            "explain the rag architecture in detail",
            enabled=True,
            force=True,
            index_path="definitely-missing.json",
            should_cancel=poll_after_first,
        )
    assert calls["n"] >= 2
