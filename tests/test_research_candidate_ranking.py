from __future__ import annotations

import pytest

from src.web.research.candidate_pool import CandidatePoolItem
from src.web.research.candidate_ranking import (
    CandidateSemanticAssessment,
    rank_candidate_pool,
)
from src.web.research.contracts import EvidenceRequirement, ResearchClaim
from src.web.research.gap_planner import GapSearchIntent


def _candidate(candidate_id: str, rank: int) -> CandidatePoolItem:
    url = f"https://{candidate_id}.example/item"
    return CandidatePoolItem(
        id=candidate_id,
        canonical_url=url,
        url=url,
        title=f"Candidate {candidate_id}",
        snippet="",
        source="",
        published_at="",
        query_ids=("query-1",),
        intents=(GapSearchIntent.DISCOVERY,),
        providers=("test",),
        first_seen_rank=rank,
    )


def _claim(*, primary: bool = True, priority: str = "critical") -> ResearchClaim:
    return ResearchClaim(
        id="claim-1",
        question_id="question-1",
        text="Official API limit",
        kind="factual",
        priority=priority,  # type: ignore[arg-type]
        state="searching",
        evidence_requirement=EvidenceRequirement(
            source_roles=("primary", "independent_secondary"),
            min_independent_sources=1,
            requires_primary_source=primary,
            requires_successful_read=True,
        ),
    )


def _assessment(
    candidate_id: str,
    *,
    relevance: str = "answer_relevant",
    confidence: float = 0.8,
    role: str = "primary",
    cluster: str | None = None,
    gains: tuple[str, ...] = (),
) -> CandidateSemanticAssessment:
    return CandidateSemanticAssessment(
        candidate_id=candidate_id,
        relevance=relevance,  # type: ignore[arg-type]
        relevance_confidence=confidence,
        source_role=role,
        source_role_confidence=0.9,
        cluster_id=cluster or f"cluster-{candidate_id}",
        expected_gain_signals=gains,
    )


def test_hard_primary_requirement_precedes_soft_relevance_confidence() -> None:
    candidates = (_candidate("secondary", 1), _candidate("primary", 2))
    ranked = rank_candidate_pool(
        candidates,
        claim=_claim(),
        assessments={
            "secondary": _assessment(
                "secondary",
                role="independent_secondary",
                confidence=1.0,
            ),
            "primary": _assessment("primary", confidence=0.55),
        },
    )
    assert [item.candidate.id for item in ranked] == ["primary", "secondary"]
    assert ranked[0].eligibility == "eligible"
    assert ranked[1].eligibility == "lead_only"
    assert "primary_required" in ranked[1].reason_codes


def test_semantic_off_target_is_rejected_even_with_primary_role() -> None:
    candidate = _candidate("dictionary", 1)
    ranked = rank_candidate_pool(
        (candidate,),
        claim=_claim(),
        assessments={
            "dictionary": _assessment(
                "dictionary",
                relevance="off_target",
                confidence=0.99,
            )
        },
    )
    assert ranked[0].eligibility == "rejected"
    assert ranked[0].reason_codes == ("semantic_off_target",)


def test_new_cluster_and_expected_gain_break_soft_ties() -> None:
    candidates = (_candidate("seen", 1), _candidate("new", 2))
    ranked = rank_candidate_pool(
        candidates,
        claim=_claim(primary=False),
        assessments={
            "seen": _assessment("seen", role="independent_secondary", cluster="old"),
            "new": _assessment(
                "new",
                role="independent_secondary",
                cluster="new",
                gains=("new_independent_cluster", "claim_status_improvement"),
            ),
        },
        seen_cluster_ids=frozenset({"old"}),
    )
    assert ranked[0].candidate.id == "new"
    assert ranked[0].new_cluster is True
    assert ranked[0].expected_information_gain == 2


def test_every_candidate_requires_explicit_semantic_assessment() -> None:
    with pytest.raises(ValueError, match="coverage mismatch"):
        rank_candidate_pool(
            (_candidate("a", 1), _candidate("b", 2)),
            claim=_claim(),
            assessments={"a": _assessment("a")},
        )


def test_unknown_source_role_remains_explicit_lead_only_truth() -> None:
    candidate = _candidate("unknown", 1)
    ranked = rank_candidate_pool(
        (candidate,),
        claim=_claim(),
        assessments={"unknown": _assessment("unknown", role="unknown")},
    )
    assert ranked[0].eligibility == "lead_only"
    assert "source_role_not_eligible" in ranked[0].reason_codes
