"""Role-aware semantic reranking for a fully collected CandidatePool.

The ranker consumes explicit semantic assessments.  It does not infer claim
relevance from token overlap and does not reuse benchmark-only matchers.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Literal, Mapping

from src.web.research.candidate_pool import CandidatePoolItem
from src.web.research.contracts import ResearchClaim

SemanticRelevance = Literal["answer_relevant", "topic_only", "off_target", "unknown"]
CandidateEligibility = Literal["eligible", "lead_only", "rejected"]

_SEMANTIC_LABELS = {"answer_relevant", "topic_only", "off_target", "unknown"}
_SOURCE_ROLES = {
    "unknown",
    "primary",
    "authoritative_secondary",
    "independent_secondary",
    "community",
    "aggregator",
}
_GAIN_SIGNALS = {
    "new_primary",
    "new_independent_cluster",
    "new_contradiction",
    "new_provenance_lead",
    "freshness_update",
    "claim_status_improvement",
}


@dataclass(frozen=True)
class CandidateSemanticAssessment:
    candidate_id: str
    relevance: SemanticRelevance
    relevance_confidence: float
    source_role: str
    source_role_confidence: float
    cluster_id: str
    expected_gain_signals: tuple[str, ...] = ()
    freshness_score: float = 0.0
    estimated_read_cost: float = 1.0


@dataclass(frozen=True)
class RankedCandidate:
    candidate: CandidatePoolItem
    assessment: CandidateSemanticAssessment
    rank: int
    eligibility: CandidateEligibility
    reason_codes: tuple[str, ...]
    new_cluster: bool
    expected_information_gain: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate": self.candidate.to_dict(),
            "rank": self.rank,
            "eligibility": self.eligibility,
            "reason_codes": list(self.reason_codes),
            "new_cluster": self.new_cluster,
            "expected_information_gain": self.expected_information_gain,
            "assessment": {
                "candidate_id": self.assessment.candidate_id,
                "relevance": self.assessment.relevance,
                "relevance_confidence": self.assessment.relevance_confidence,
                "source_role": self.assessment.source_role,
                "source_role_confidence": self.assessment.source_role_confidence,
                "cluster_id": self.assessment.cluster_id,
                "expected_gain_signals": list(self.assessment.expected_gain_signals),
                "freshness_score": self.assessment.freshness_score,
                "estimated_read_cost": self.assessment.estimated_read_cost,
            },
        }


def rank_candidate_pool(
    candidates: tuple[CandidatePoolItem, ...],
    *,
    claim: ResearchClaim,
    assessments: Mapping[str, CandidateSemanticAssessment],
    seen_cluster_ids: frozenset[str] = frozenset(),
) -> tuple[RankedCandidate, ...]:
    """Rank a complete pool with hard evidence requirements before soft fit."""

    candidate_ids = {item.id for item in candidates}
    if set(assessments) != candidate_ids:
        missing = sorted(candidate_ids - set(assessments))
        extra = sorted(set(assessments) - candidate_ids)
        raise ValueError(f"semantic assessment coverage mismatch: missing={missing}, extra={extra}")
    staged: list[tuple[tuple[float, ...], CandidatePoolItem, CandidateSemanticAssessment, CandidateEligibility, tuple[str, ...], bool, int]] = []
    for candidate in candidates:
        assessment = _validate_assessment(assessments[candidate.id], candidate.id)
        eligibility, reasons = _eligibility(claim, assessment)
        new_cluster = assessment.cluster_id not in seen_cluster_ids
        gain = len(set(assessment.expected_gain_signals))
        hard_tier = {"eligible": 2.0, "lead_only": 1.0, "rejected": 0.0}[eligibility]
        role_tier = _role_fit_tier(claim, assessment.source_role)
        semantic_tier = {
            "answer_relevant": 3.0,
            "topic_only": 1.0,
            "unknown": 0.0,
            "off_target": -1.0,
        }[assessment.relevance]
        key = (
            hard_tier,
            role_tier,
            assessment.source_role_confidence,
            semantic_tier,
            assessment.relevance_confidence,
            float(new_cluster),
            float(gain),
            assessment.freshness_score,
            -assessment.estimated_read_cost,
            -float(candidate.first_seen_rank),
        )
        staged.append((key, candidate, assessment, eligibility, reasons, new_cluster, gain))
    staged.sort(key=lambda item: item[0], reverse=True)
    return tuple(
        RankedCandidate(
            candidate=candidate,
            assessment=assessment,
            rank=index,
            eligibility=eligibility,
            reason_codes=reasons,
            new_cluster=new_cluster,
            expected_information_gain=gain,
        )
        for index, (_, candidate, assessment, eligibility, reasons, new_cluster, gain) in enumerate(staged, start=1)
    )


def _validate_assessment(
    assessment: CandidateSemanticAssessment,
    candidate_id: str,
) -> CandidateSemanticAssessment:
    if assessment.candidate_id != candidate_id:
        raise ValueError("semantic assessment candidate_id does not match mapping key")
    if assessment.relevance not in _SEMANTIC_LABELS:
        raise ValueError(f"invalid semantic relevance: {assessment.relevance}")
    if assessment.source_role not in _SOURCE_ROLES:
        raise ValueError(f"invalid source role: {assessment.source_role}")
    if not assessment.cluster_id.strip():
        raise ValueError("semantic assessment requires cluster_id")
    if not isfinite(assessment.relevance_confidence) or not 0.0 <= assessment.relevance_confidence <= 1.0:
        raise ValueError("relevance_confidence must be between 0 and 1")
    if not isfinite(assessment.source_role_confidence) or not 0.0 <= assessment.source_role_confidence <= 1.0:
        raise ValueError("source_role_confidence must be between 0 and 1")
    if not isfinite(assessment.freshness_score) or not 0.0 <= assessment.freshness_score <= 1.0:
        raise ValueError("freshness_score must be between 0 and 1")
    if not isfinite(assessment.estimated_read_cost) or assessment.estimated_read_cost <= 0:
        raise ValueError("estimated_read_cost must be positive")
    unknown = set(assessment.expected_gain_signals) - _GAIN_SIGNALS
    if unknown:
        raise ValueError(f"invalid expected gain signals: {sorted(unknown)}")
    return assessment


def _eligibility(
    claim: ResearchClaim,
    assessment: CandidateSemanticAssessment,
) -> tuple[CandidateEligibility, tuple[str, ...]]:
    if assessment.relevance == "off_target":
        return "rejected", ("semantic_off_target",)
    reasons: list[str] = []
    roles = set(claim.evidence_requirement.source_roles)
    if assessment.source_role not in roles:
        reasons.append("source_role_not_eligible")
    if claim.evidence_requirement.requires_primary_source and assessment.source_role != "primary":
        reasons.append("primary_required")
    if assessment.relevance != "answer_relevant":
        reasons.append(f"semantic_{assessment.relevance}")
    if reasons:
        return "lead_only", tuple(reasons)
    return "eligible", ("hard_requirements_met",)


def _role_fit_tier(claim: ResearchClaim, source_role: str) -> float:
    if claim.evidence_requirement.requires_primary_source and source_role == "primary":
        return 3.0
    if source_role in claim.evidence_requirement.source_roles:
        return 2.0
    return 0.0


__all__ = [
    "CandidateEligibility",
    "CandidateSemanticAssessment",
    "RankedCandidate",
    "SemanticRelevance",
    "rank_candidate_pool",
]
