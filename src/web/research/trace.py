"""Deterministic Research Trace v1 append helpers.

The strict helper is for Claim Engine code that must surface contract bugs. The
safe helper is the legacy boundary: it returns the original immutable state and
a bounded reason code instead of letting trace failure break research.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from src.web.research.contracts import (
    ResearchBudget,
    ResearchState,
    ResearchTraceEvent,
    ResearchTraceEventType,
    build_research_state,
)

TraceAppendStatus = Literal["appended", "unavailable"]


@dataclass(frozen=True)
class TraceAppendResult:
    status: TraceAppendStatus
    state: ResearchState
    reason: str = ""

    @property
    def appended(self) -> bool:
        return self.status == "appended"


def append_research_trace(
    state: ResearchState,
    *,
    timestamp: str,
    run_id: str,
    event_type: ResearchTraceEventType,
    reason: str,
    known_evidence_ids: Iterable[str],
    claim_id: str = "",
    gap_id: str = "",
    evidence_id: str = "",
    budget_before: ResearchBudget | None = None,
    budget_after: ResearchBudget | None = None,
) -> ResearchState:
    """Append one validated event without mutating the prior state."""

    _validate_event_references(
        event_type=event_type,
        claim_id=claim_id,
        gap_id=gap_id,
        evidence_id=evidence_id,
        budget_before=budget_before,
        budget_after=budget_after,
    )
    sequence = max((item.sequence for item in state.trace), default=-1) + 1
    event = ResearchTraceEvent(
        sequence=sequence,
        timestamp=timestamp,
        run_id=run_id,
        event_type=event_type,
        reason=reason,
        claim_id=claim_id,
        gap_id=gap_id,
        evidence_id=evidence_id,
        budget_before=budget_before,
        budget_after=budget_after,
    )
    return build_research_state(
        mode=state.mode,
        questions=state.questions,
        claims=state.claims,
        evidence=state.evidence,
        evidence_links=state.evidence_links,
        source_clusters=state.source_clusters,
        gaps=state.gaps,
        conflict_gaps=state.conflict_gaps,
        budget=state.budget,
        trace=(*state.trace, event),
        brief=state.brief,
        known_evidence_ids=known_evidence_ids,
    )


def try_append_research_trace(
    state: ResearchState,
    *,
    timestamp: str,
    run_id: str,
    event_type: ResearchTraceEventType,
    reason: str,
    known_evidence_ids: Iterable[str],
    claim_id: str = "",
    gap_id: str = "",
    evidence_id: str = "",
    budget_before: ResearchBudget | None = None,
    budget_after: ResearchBudget | None = None,
) -> TraceAppendResult:
    """Fail safe at the legacy boundary while retaining immutable old state."""

    try:
        updated = append_research_trace(
            state,
            timestamp=timestamp,
            run_id=run_id,
            event_type=event_type,
            reason=reason,
            known_evidence_ids=known_evidence_ids,
            claim_id=claim_id,
            gap_id=gap_id,
            evidence_id=evidence_id,
            budget_before=budget_before,
            budget_after=budget_after,
        )
    except (TypeError, ValueError):
        return TraceAppendResult(
            status="unavailable",
            state=state,
            reason="trace_validation_failed",
        )
    return TraceAppendResult(status="appended", state=updated)


def _validate_event_references(
    *,
    event_type: str,
    claim_id: str,
    gap_id: str,
    evidence_id: str,
    budget_before: ResearchBudget | None,
    budget_after: ResearchBudget | None,
) -> None:
    if event_type in {"claim_created", "gate_evaluated"} and not claim_id:
        raise ValueError(f"{event_type} requires claim_id")
    if event_type == "gap_created" and not gap_id:
        raise ValueError("gap_created requires gap_id")
    if event_type in {"read_completed", "evidence_extracted"} and not evidence_id:
        raise ValueError(f"{event_type} requires evidence_id")
    if event_type == "claim_linked" and (not claim_id or not evidence_id):
        raise ValueError("claim_linked requires claim_id and evidence_id")
    if event_type == "budget_changed" and (
        budget_before is None or budget_after is None
    ):
        raise ValueError("budget_changed requires budget_before and budget_after")
