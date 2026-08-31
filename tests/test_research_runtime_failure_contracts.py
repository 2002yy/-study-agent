"""v1/v2 codec, compatibility and identity tests for runtime failures.

Locks the Batch-A acceptance matrix: v1 known/unknown rows stay readable and
unmodified, v1 read->write stays v1 (no silent migration), explicit v2
round-trips all fields, unknown future v2 codes remain readable while the
writer validator stays closed, and deterministic failure ids + append-by-id
give exactly-once semantics across resume.
"""

from __future__ import annotations

from src.web.research.runtime import (
    RESEARCH_RUNTIME_SCHEMA_VERSION_V1,
    RESEARCH_RUNTIME_SCHEMA_VERSION_V2,
    ResearchRuntimeCursor,
    RuntimeFailure,
    append_runtime_failure,
    build_runtime_failure,
    runtime_failure_id,
    runtime_failure_id_unattached,
)


def _v2_failure() -> RuntimeFailure:
    return build_runtime_failure(
        failure_id=runtime_failure_id(logical_call_id="read:candidate_7", code="read_failed"),
        code="read_failed",
        phase="reading",
        item_id="candidate_7",
        detail="http 403 on fetch",
        provider_code="http_403",
        exception_type="ProviderError",
        attempt_id="read:candidate_7:attempt:2",
    )


def test_v2_round_trip_preserves_all_fields() -> None:
    failure = _v2_failure()
    restored = RuntimeFailure.from_dict(failure.to_dict(RESEARCH_RUNTIME_SCHEMA_VERSION_V2))
    assert restored == failure
    assert restored.legacy_input is False


def test_v1_known_code_compatibility() -> None:
    raw = {"code": "search_failed", "phase": "searching", "item_id": "q_1"}
    failure = RuntimeFailure.from_dict(raw)
    assert failure.code == "search_failed"
    assert failure.phase == "searching"
    assert failure.item_id == "q_1"
    assert failure.failure_id == ""
    assert failure.detail == ""
    assert failure.provider_code == ""
    assert failure.exception_type == ""
    assert failure.attempt_id == ""
    assert failure.legacy_input is True


def test_v1_unknown_historical_code_stays_raw() -> None:
    raw = {"code": "SomeOldProviderTimeoutError", "phase": "reading", "item_id": "c_2"}
    failure = RuntimeFailure.from_dict(raw)
    assert failure.code == "SomeOldProviderTimeoutError"
    assert failure.item_id == "c_2"
    assert failure.legacy_input is True


def test_v1_reader_rejects_non_three_field_shape() -> None:
    import pytest

    with pytest.raises(ValueError):
        RuntimeFailure.from_dict(
            {"code": "read_failed", "phase": "reading", "item_id": "c_1", "extra": 1}
        )


def test_v1_cursor_reserializes_as_v1() -> None:
    cursor = ResearchRuntimeCursor.from_dict(
        {
            "schema_version": RESEARCH_RUNTIME_SCHEMA_VERSION_V1,
            "round_index": 1,
            "phase": "gating",
            "planned_queries": [],
            "query_outcomes": [],
            "candidates": [],
            "planned_read_ids": [],
            "read_outcomes": [],
            "model_calls": [],
            "inflight_model_call": None,
            "inflight_external_call": None,
            "failures": [
                {
                    "code": "SomeOldDynamicFailure",
                    "phase": "reading",
                    "item_id": "c_3",
                }
            ],
            "wave_index": 1,
            "wave_id": "w_1",
            "active_gap_ids": [],
            "gain_history": [],
            "no_gain_batches_by_claim": {},
            "no_gain_batches_by_gap": {},
        }
    )
    assert cursor.schema_version == RESEARCH_RUNTIME_SCHEMA_VERSION_V1
    serialized = cursor.to_dict()
    assert serialized["schema_version"] == RESEARCH_RUNTIME_SCHEMA_VERSION_V1
    failure = serialized["failures"][0]
    assert set(failure) == {"code", "phase", "item_id"}
    assert failure["code"] == "SomeOldDynamicFailure"


def test_v1_cursor_keeps_legacy_failure_in_memory() -> None:
    cursor = ResearchRuntimeCursor.from_dict(
        {
            "schema_version": RESEARCH_RUNTIME_SCHEMA_VERSION_V1,
            "round_index": 0,
            "phase": "bootstrap",
            "planned_queries": [],
            "query_outcomes": [],
            "candidates": [],
            "planned_read_ids": [],
            "read_outcomes": [],
            "model_calls": [],
            "inflight_model_call": None,
            "inflight_external_call": None,
            "failures": [
                {"code": "OldCode", "phase": "planning", "item_id": ""}
            ],
            "wave_index": 0,
            "wave_id": "",
            "active_gap_ids": [],
            "gain_history": [],
            "no_gain_batches_by_claim": {},
            "no_gain_batches_by_gap": {},
        }
    )
    assert cursor.failures[0].legacy_input is True


def test_explicit_v2_cursor_reserializes_as_v2() -> None:
    raw = {
        "schema_version": RESEARCH_RUNTIME_SCHEMA_VERSION_V2,
        "round_index": 0,
        "phase": "bootstrap",
        "planned_queries": [],
        "query_outcomes": [],
        "candidates": [],
        "planned_read_ids": [],
        "read_outcomes": [],
        "model_calls": [],
        "inflight_model_call": None,
        "inflight_external_call": None,
        "failures": [_v2_failure().to_dict(RESEARCH_RUNTIME_SCHEMA_VERSION_V2)],
        "wave_index": 0,
        "wave_id": "",
        "active_gap_ids": [],
        "gain_history": [],
        "no_gain_batches_by_claim": {},
        "no_gain_batches_by_gap": {},
    }
    cursor = ResearchRuntimeCursor.from_dict(raw)
    assert cursor.schema_version == RESEARCH_RUNTIME_SCHEMA_VERSION_V2
    serialized = cursor.to_dict()
    assert serialized["schema_version"] == RESEARCH_RUNTIME_SCHEMA_VERSION_V2
    assert set(serialized["failures"][0]) == {
        "failure_id",
        "code",
        "phase",
        "item_id",
        "detail",
        "provider_code",
        "exception_type",
        "attempt_id",
    }
    assert serialized["failures"][0]["code"] == "read_failed"


def test_unknown_future_v2_code_is_readable_but_rejected_as_writer() -> None:
    from src.web.research.failure_contracts import require_research_failure_code
    import pytest

    raw = {
        "failure_id": "failure:abc",
        "code": "read_future_p2_reason",
        "phase": "reading",
        "item_id": "c_4",
        "detail": "",
        "provider_code": "",
        "exception_type": "",
        "attempt_id": "",
    }
    failure = RuntimeFailure.from_dict(raw)
    assert failure.code == "read_future_p2_reason"
    assert failure.legacy_input is False
    with pytest.raises(ValueError):
        require_research_failure_code("read_future_p2_reason")


def test_build_failure_rejects_unknown_code() -> None:
    import pytest

    with pytest.raises(ValueError):
        build_runtime_failure(
            failure_id="failure:abc",
            code="TimeoutError",  # type: ignore[arg-type]
            phase="searching",
        )
    with pytest.raises(ValueError):
        build_runtime_failure(
            failure_id="failure:abc",
            code="read_login_required",  # type: ignore[arg-type]
            phase="reading",
        )


def test_build_failure_requires_failure_id() -> None:
    import pytest

    with pytest.raises(ValueError):
        build_runtime_failure(failure_id="", code="read_failed", phase="reading")


def test_failure_id_is_deterministic() -> None:
    first = runtime_failure_id(logical_call_id="read:c_1", code="read_failed")
    second = runtime_failure_id(logical_call_id="read:c_1", code="read_failed")
    assert first == second
    assert first.startswith("failure:")
    assert len(first) == len("failure:") + 24


def test_same_logical_attempt_same_code_same_failure_id() -> None:
    resumed = runtime_failure_id(logical_call_id="read:c_1", code="read_failed")
    original = runtime_failure_id(logical_call_id="read:c_1", code="read_failed")
    assert resumed == original


def test_different_attempts_get_different_failure_ids() -> None:
    attempt_one = runtime_failure_id(logical_call_id="read:c_1", code="read_failed")
    attempt_two = runtime_failure_id(logical_call_id="read:c_1:attempt:2", code="read_failed")
    assert attempt_one != attempt_two


def test_different_codes_get_different_failure_ids() -> None:
    read = runtime_failure_id(logical_call_id="c_1", code="read_failed")
    search = runtime_failure_id(logical_call_id="c_1", code="search_failed")
    assert read != search


def test_unattached_identity_includes_all_parts() -> None:
    first = runtime_failure_id_unattached(
        phase="reading", item_id="c_1", attempt_id="", code="read_failed"
    )
    second = runtime_failure_id_unattached(
        phase="reading", item_id="c_1", attempt_id="a_2", code="read_failed"
    )
    assert first != second
    same = runtime_failure_id_unattached(
        phase="reading", item_id="c_1", attempt_id="", code="read_failed"
    )
    assert same == first


def test_append_failure_is_idempotent_by_failure_id() -> None:
    failure = _v2_failure()
    appended = append_runtime_failure((), failure)
    again = append_runtime_failure(appended, failure)
    assert len(again) == 1
    rebuilt = build_runtime_failure(
        failure_id=runtime_failure_id(
            logical_call_id="read:candidate_7", code="read_failed"
        ),
        code="read_failed",
        phase="reading",
        item_id="candidate_7",
    )
    after_resume = append_runtime_failure(appended, rebuilt)
    assert len(after_resume) == 1


def test_append_keeps_distinct_attempts() -> None:
    attempt_one = build_runtime_failure(
        failure_id=runtime_failure_id(logical_call_id="read:c_1", code="read_failed"),
        code="read_failed",
        phase="reading",
        item_id="c_1",
    )
    attempt_two = build_runtime_failure(
        failure_id=runtime_failure_id(
            logical_call_id="read:c_1:attempt:2", code="read_failed"
        ),
        code="read_failed",
        phase="reading",
        item_id="c_1",
    )
    appended = append_runtime_failure((attempt_one,), attempt_two)
    assert len(appended) == 2


def test_append_never_dedupes_legacy_failures() -> None:
    legacy = RuntimeFailure(code="OldCode", phase="reading", item_id="c_1")
    appended = append_runtime_failure((legacy,), legacy)
    assert len(appended) == 2
