"""Tests for the durable active-steering envelope (P1-C batch 3, decision 3A).

The steering metadata lives inside the owning WebLookupRun context as an
append-only, server-owned-ID list; the executor consumes it at wave
boundaries. These tests lock the append/merge contract so concurrent
arrivals survive checkpoints and applied state is never overwritten by
stale durable copies.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.web.research.steering import (
    ACTIVE_RESEARCH_STEERING_KEY,
    active_steering_entries,
    append_active_steering,
    is_active_claim_engine_context,
    merge_active_steering_context,
)


def _active_context() -> dict[str, Any]:
    return {"claim_engine": {"mode": "active", "schema_version": "1"}}


def test_is_active_claim_engine_context_requires_active_mode() -> None:
    assert is_active_claim_engine_context(_active_context()) is True
    assert (
        is_active_claim_engine_context({"claim_engine": {"mode": "shadow"}})
        is False
    )
    assert is_active_claim_engine_context({"deep": {}}) is False
    assert is_active_claim_engine_context({}) is False


def test_append_adds_one_server_owned_pending_entry() -> None:
    context = append_active_steering(
        _active_context(),
        entry_id="steering_1",
        content="Focus on the 2026 release notes",
        received_at="2026-08-31T00:00:00+00:00",
    )
    entries = active_steering_entries(context)
    assert len(entries) == 1
    assert entries[0]["id"] == "steering_1"
    assert entries[0]["status"] == "pending"
    assert entries[0]["applied_wave"] is None
    assert entries[0]["claim_id"] == ""
    assert entries[0]["gap_id"] == ""
    assert entries[0]["late_reason"] == ""


def test_append_is_idempotent_by_server_owned_id() -> None:
    context = append_active_steering(
        _active_context(),
        entry_id="steering_1",
        content="first",
        received_at="2026-08-31T00:00:00+00:00",
    )
    context = append_active_steering(
        context,
        entry_id="steering_1",
        content="second - must not replace the first",
        received_at="2026-08-31T00:00:01+00:00",
    )
    entries = active_steering_entries(context)
    assert len(entries) == 1
    assert entries[0]["content"] == "first"


def test_append_keeps_append_only_insertion_order() -> None:
    context = append_active_steering(
        _active_context(),
        entry_id="steering_2",
        content="second",
        received_at="2026-08-31T00:00:02+00:00",
    )
    context = append_active_steering(
        context,
        entry_id="steering_1",
        content="first",
        received_at="2026-08-31T00:00:01+00:00",
    )
    entries = active_steering_entries(context)
    assert [item["id"] for item in entries] == ["steering_2", "steering_1"]
    merged = merge_active_steering_context(context, {})
    assert [
        item["id"] for item in active_steering_entries(merged)
    ] == ["steering_1", "steering_2"]


def test_entries_filter_rejects_anonymous_data() -> None:
    context = {
        **_active_context(),
        ACTIVE_RESEARCH_STEERING_KEY: [
            {"id": "ok", "status": "pending", "content": "good"},
            {"id": "", "status": "pending", "content": "bad"},
            {"status": "pending", "content": "no id"},
            {"id": "bad-status", "status": "not-a-status"},
            "not a mapping",
        ],
    }
    entries = active_steering_entries(context)
    assert len(entries) == 1
    assert entries[0]["id"] == "ok"


def test_merge_keeps_durable_only_entries_arrived_concurrently() -> None:
    incoming = append_active_steering(
        _active_context(),
        entry_id="steering_a",
        content="a",
        received_at="2026-08-31T00:00:00+00:00",
    )
    durable = append_active_steering(
        incoming,
        entry_id="steering_b",
        content="b",
        received_at="2026-08-31T00:00:01+00:00",
    )
    merged = merge_active_steering_context(incoming, durable)
    assert {item["id"] for item in active_steering_entries(merged)} == {
        "steering_a",
        "steering_b",
    }


def test_merge_incoming_applied_state_wins_over_stale_durable() -> None:
    durable = append_active_steering(
        _active_context(),
        entry_id="steering_a",
        content="a",
        received_at="2026-08-31T00:00:00+00:00",
    )
    incoming = dict(durable)
    incoming[ACTIVE_RESEARCH_STEERING_KEY] = [
        {
            **item,
            "status": "applied",
            "applied_wave": 2,
            "claim_id": "claim_steering_x",
            "gap_id": "gap_steering_x",
        }
        for item in active_steering_entries(incoming)
    ]
    merged = merge_active_steering_context(incoming, durable)
    entries = active_steering_entries(merged)
    assert len(entries) == 1
    assert entries[0]["status"] == "applied"
    assert entries[0]["applied_wave"] == 2
    assert entries[0]["claim_id"] == "claim_steering_x"


def test_merge_is_noop_without_any_steering() -> None:
    incoming = _active_context()
    durable = _active_context()
    merged = merge_active_steering_context(incoming, durable)
    assert merged == incoming


@pytest.mark.parametrize(
    "mutator",
    [
        lambda context: merge_active_steering_context(context, {}),
        lambda context: append_active_steering(
            context,
            entry_id="steering_n",
            content="n",
            received_at="2026-08-31T00:00:09+00:00",
        ),
    ],
)
def test_envelope_operations_never_mutate_inputs(mutator: Any) -> None:
    context = append_active_steering(
        _active_context(),
        entry_id="steering_1",
        content="first",
        received_at="2026-08-31T00:00:00+00:00",
    )
    snapshot = active_steering_entries(context)
    mutator(context)
    assert active_steering_entries(context) == snapshot
