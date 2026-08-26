from __future__ import annotations

import pytest

from src.domain.evidence import ClaimEvidenceLinkV1
from src.web.research.contracts import (
    EvidenceGap,
    EvidenceRequirement,
    ResearchBudget,
    ResearchClaim,
    ResearchClaimEvidenceLink,
    ResearchEvidence,
    ResearchQuestion,
    ResearchState,
    build_research_state,
)
from src.web.research.state import attach_claim_engine_state, load_claim_engine_state
from src.web.research.trace import append_research_trace, try_append_research_trace


def _budget(*, reads: int = 8) -> ResearchBudget:
    return ResearchBudget(20, reads, 45, 60, 16000)


def _state() -> ResearchState:
    return build_research_state(
        mode="shadow",
        questions=[ResearchQuestion("q1", "What is verified?", "critical")],
        claims=[
            ResearchClaim(
                "claim1",
                "q1",
                "A fact needs verification.",
                "factual",
                "critical",
                "searching",
                EvidenceRequirement(("primary",), 1, True),
            )
        ],
        evidence=[ResearchEvidence("ev1", locator="section-1")],
        evidence_links=[
            ResearchClaimEvidenceLink(
                ClaimEvidenceLinkV1("claim1", "ev1", "supports", 0.8),
                source_role="primary",
            )
        ],
        source_clusters=(),
        gaps=[EvidenceGap("gap1", "claim1", "primary_missing")],
        conflict_gaps=(),
        budget=_budget(),
        known_evidence_ids={"ev1"},
    )


def test_append_trace_is_immutable_sequenced_and_utc_normalized() -> None:
    original = _state()
    updated = append_research_trace(
        original,
        timestamp="2026-08-26T20:00:00+08:00",
        run_id="run_1",
        event_type="claim_created",
        reason="planner_decomposition",
        claim_id="claim1",
        known_evidence_ids={"ev1"},
    )

    assert original.trace == ()
    assert updated.trace[0].sequence == 0
    assert updated.trace[0].timestamp == "2026-08-26T12:00:00Z"
    assert updated.trace[0].run_id == "run_1"


def test_all_frozen_event_types_serialize() -> None:
    state = _state()
    cases = [
        ("claim_created", {"claim_id": "claim1"}),
        ("gap_created", {"gap_id": "gap1"}),
        ("query_planned", {}),
        ("search_completed", {}),
        ("candidate_ranked", {}),
        ("read_completed", {"evidence_id": "ev1"}),
        ("evidence_extracted", {"evidence_id": "ev1"}),
        ("claim_linked", {"claim_id": "claim1", "evidence_id": "ev1"}),
        ("gate_evaluated", {"claim_id": "claim1"}),
        ("stop_blocked", {}),
        ("stop_allowed", {}),
        (
            "budget_changed",
            {"budget_before": _budget(), "budget_after": _budget(reads=7)},
        ),
        ("failure_recorded", {}),
    ]

    for event_type, references in cases:
        state = append_research_trace(
            state,
            timestamp="2026-08-26T12:00:00Z",
            run_id="run_1",
            event_type=event_type,  # type: ignore[arg-type]
            reason=f"{event_type}_reason",
            known_evidence_ids={"ev1"},
            **references,  # type: ignore[arg-type]
        )

    assert [item.event_type for item in state.trace] == [item[0] for item in cases]
    assert [item.sequence for item in state.trace] == list(range(len(cases)))


@pytest.mark.parametrize(
    ("event_type", "message"),
    [
        ("claim_created", "requires claim_id"),
        ("gap_created", "requires gap_id"),
        ("read_completed", "requires evidence_id"),
        ("claim_linked", "requires claim_id and evidence_id"),
        ("budget_changed", "requires budget_before and budget_after"),
    ],
)
def test_event_specific_required_references(event_type: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        append_research_trace(
            _state(),
            timestamp="2026-08-26T12:00:00Z",
            run_id="run_1",
            event_type=event_type,  # type: ignore[arg-type]
            reason="missing_reference",
            known_evidence_ids={"ev1"},
        )


def test_invalid_timestamp_and_cross_run_trace_fail_closed() -> None:
    with pytest.raises(ValueError, match="timezone"):
        append_research_trace(
            _state(),
            timestamp="2026-08-26T12:00:00",
            run_id="run_1",
            event_type="query_planned",
            reason="timezone_missing",
            known_evidence_ids={"ev1"},
        )

    first = append_research_trace(
        _state(),
        timestamp="2026-08-26T12:00:00Z",
        run_id="run_1",
        event_type="query_planned",
        reason="initial_plan",
        known_evidence_ids={"ev1"},
    )
    with pytest.raises(ValueError, match="multiple run ids"):
        append_research_trace(
            first,
            timestamp="2026-08-26T12:00:01Z",
            run_id="run_2",
            event_type="search_completed",
            reason="wrong_owner",
            known_evidence_ids={"ev1"},
        )


def test_safe_append_retains_legacy_state_on_trace_failure() -> None:
    original = _state()
    result = try_append_research_trace(
        original,
        timestamp="invalid",
        run_id="run_1",
        event_type="not_a_trace_event",
        reason="invalid_event",
        known_evidence_ids={"ev1"},
    )

    assert result.appended is False
    assert result.status == "unavailable"
    assert result.reason == "trace_validation_failed"
    assert result.state is original


def test_trace_round_trips_through_claim_engine_context() -> None:
    state = append_research_trace(
        _state(),
        timestamp="2026-08-26T12:00:00Z",
        run_id="run_1",
        event_type="gate_evaluated",
        reason="critical_claim_still_open",
        claim_id="claim1",
        known_evidence_ids={"ev1"},
    )
    context = attach_claim_engine_state({}, state, known_evidence_ids={"ev1"})
    restored = load_claim_engine_state(context, known_evidence_ids={"ev1"})

    assert restored.available is True
    assert restored.state == state
