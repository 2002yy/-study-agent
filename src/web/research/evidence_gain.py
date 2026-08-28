"""Deterministic Evidence Gain and Saturation contracts (RQCE-P1-C batch 1).

Pure contracts over ResearchState snapshots. No runtime loop, no executor
changes, no I/O: this module only answers two questions deterministically —

1. did this research batch produce substantive evidence value?
2. has a given Gap/Claim earned its stop-by-saturation counter?

Frozen gain taxonomy (exactly six reasons). New URLs, new search results,
result_count growth and same-cluster repeat evidence are never substantive
gain on their own. Saturation counters are per Gap and per Claim — never a
global run counter — with the frozen rule that two consecutive no-gain
query batches saturate, while critical/conflict claims may take one extra
batch before saturating.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from src.web.research.contracts import ResearchState

EvidenceGainReason = Literal[
    "new_eligible_evidence",
    "new_independent_cluster",
    "better_source_role",
    "new_contradiction",
    "new_provenance_lead",
    "claim_status_improvement",
]

_GAIN_REASONS: set[str] = {
    "new_eligible_evidence",
    "new_independent_cluster",
    "better_source_role",
    "new_contradiction",
    "new_provenance_lead",
    "claim_status_improvement",
}

# Deterministic source-role promotion order used by better_source_role.
_ROLE_RANK: dict[str, int] = {
    "aggregator": 0,
    "community": 1,
    "independent_secondary": 2,
    "authoritative_secondary": 3,
    "primary": 4,
}

# Relations that bear on the claim itself. Role upgrades and new independent
# clusters only count for these; background/lead links are never substantive
# gain on their own (leads are handled by new_provenance_lead).
_EVIDENCE_BEARING_RELATIONS = {"supports", "qualifies"}

# Explicit claim-state improvement edges (H-note: deliberately not a global
# integer rank). Moving into "unresolved" is a legitimate terminal state, not
# progress; unlisted edges are never improvements.
_CLAIM_IMPROVEMENT_EDGES: set[tuple[str, str]] = {
    ("pending", "searching"),
    ("pending", "partially_satisfied"),
    ("searching", "partially_satisfied"),
    ("partially_satisfied", "satisfied"),
    ("contested", "partially_satisfied"),
    ("contested", "satisfied"),
    ("unresolved", "partially_satisfied"),
    ("unresolved", "satisfied"),
}

# Frozen saturation rule: two consecutive no-gain query batches saturate a
# claim/gap; critical/conflict claims may take one extra batch.
SATURATION_NO_GAIN_BATCHES = 2
SATURATION_CRITICAL_EXTRA_BATCHES = 1


@dataclass(frozen=True)
class EvidenceGainResult:
    """Deterministic outcome of comparing two ResearchState snapshots."""

    substantive_gain: bool
    gain_reasons: tuple[EvidenceGainReason, ...]
    affected_claim_ids: tuple[str, ...]
    affected_gap_ids: tuple[str, ...]
    metrics: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "substantive_gain": self.substantive_gain,
            "gain_reasons": list(self.gain_reasons),
            "affected_claim_ids": list(self.affected_claim_ids),
            "affected_gap_ids": list(self.affected_gap_ids),
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "EvidenceGainResult":
        reasons = tuple(
            reason
            for reason in raw.get("gain_reasons", [])
            if isinstance(reason, str) and reason in _GAIN_REASONS
        )
        return cls(
            substantive_gain=bool(raw.get("substantive_gain")),
            gain_reasons=reasons,  # type: ignore[arg-type]
            affected_claim_ids=tuple(str(item) for item in raw.get("affected_claim_ids", [])),
            affected_gap_ids=tuple(str(item) for item in raw.get("affected_gap_ids", [])),
            metrics={
                str(key): int(value)
                for key, value in (raw.get("metrics") or {}).items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            },
        )


def _eligible_support_links(state: ResearchState) -> dict[str, set[tuple[str, str, str]]]:
    """claim_id -> {(evidence_id, source_role, cluster_id)} for eligible
    evidence attached through an evidence-bearing relation (supports /
    qualifies). Background and lead links never enter this map: role upgrades
    and new clusters only count for evidence that bears on the claim itself.
    """
    eligible_ids = {
        evidence.evidence_id
        for evidence in state.evidence
        if evidence.extraction_status == "eligible"
    }
    links: dict[str, set[tuple[str, str, str]]] = {}
    for link in state.evidence_links:
        if link.evidence_id not in eligible_ids:
            continue
        if link.relation not in _EVIDENCE_BEARING_RELATIONS:
            continue
        links.setdefault(link.claim_id, set()).add(
            (link.evidence_id, link.source_role, link.source_cluster_id)
        )
    return links


def _contradiction_pairs(state: ResearchState) -> set[tuple[str, str]]:
    return {
        (link.claim_id, link.evidence_id)
        for link in state.evidence_links
        if link.relation == "contradicts"
    }


def _provenance_lead_pairs(state: ResearchState) -> set[tuple[str, str]]:
    eligible_ids = {
        evidence.evidence_id
        for evidence in state.evidence
        if evidence.extraction_status == "eligible"
    }
    return {
        (link.claim_id, link.evidence_id)
        for link in state.evidence_links
        if link.relation == "lead" and link.evidence_id in eligible_ids
    }


def _best_role_rank(links: Mapping[str, set[tuple[str, str, str]]], claim_id: str) -> int:
    roles = {role for (_, role, _) in links.get(claim_id, set())}
    return max((_ROLE_RANK.get(role, 0) for role in roles), default=-1)


def evaluate_evidence_gain(
    before: ResearchState,
    after: ResearchState,
) -> EvidenceGainResult:
    """Compare two ResearchState snapshots under the frozen 6-reason taxonomy.

    The evaluation is pure and deterministic: equal snapshots always yield
    no gain, and the same before/after pair always yields the same result.
    """
    reasons: list[EvidenceGainReason] = []
    affected_claims: set[str] = set()
    metrics: dict[str, int] = {}

    before_links = _eligible_support_links(before)
    after_links = _eligible_support_links(after)

    # 1) new_eligible_evidence: a claim's FIRST eligible evidence-bearing
    # evidence (0 -> 1). This is deliberately not "any new eligible
    # evidence_id": further same-cluster, same-role repeats for an
    # already-evidenced claim are never gain, otherwise duplicate reposts
    # would keep research from ever saturating.
    first_evidence_claims = sorted(
        claim_id
        for claim_id, links in after_links.items()
        if links and claim_id not in before_links
    )
    if first_evidence_claims:
        reasons.append("new_eligible_evidence")
        affected_claims.update(first_evidence_claims)
    metrics["first_eligible_claims"] = len(first_evidence_claims)

    # 2) new_independent_cluster: a claim gains a support cluster (through an
    # evidence-bearing relation) it did not have in the before snapshot. A new
    # cluster that only carries background material is not gain.
    new_cluster_claims = sorted(
        claim_id
        for claim_id, links in after_links.items()
        if {cluster for (_, _, cluster) in links}
        - {cluster for (_, _, cluster) in before_links.get(claim_id, set())}
    )
    if new_cluster_claims:
        reasons.append("new_independent_cluster")
        affected_claims.update(new_cluster_claims)
    metrics["new_cluster_claims"] = len(new_cluster_claims)

    # 3) better_source_role: a claim's best eligible evidence-bearing role
    # rank improves (e.g. independent_secondary -> primary). Background/lead
    # relations are excluded from the comparison.
    role_upgraded_claims = sorted(
        claim_id
        for claim_id in after_links
        if _best_role_rank(after_links, claim_id) > _best_role_rank(before_links, claim_id)
    )
    if role_upgraded_claims:
        reasons.append("better_source_role")
        affected_claims.update(role_upgraded_claims)
    metrics["role_upgraded_claims"] = len(role_upgraded_claims)

    # 4) new_contradiction: a new contradicts link or a new conflict gap.
    # Counted separately so one real-world conflict (link + gap) is never
    # double-counted in the metrics.
    before_conflict_ids = {gap.id for gap in before.conflict_gaps}
    new_contradiction_links = sorted(
        _contradiction_pairs(after) - _contradiction_pairs(before)
    )
    new_conflict_gaps = [
        gap for gap in after.conflict_gaps if gap.id not in before_conflict_ids
    ]
    if new_contradiction_links or new_conflict_gaps:
        reasons.append("new_contradiction")
        affected_claims.update(claim_id for claim_id, _ in new_contradiction_links)
        affected_claims.update(gap.claim_id for gap in new_conflict_gaps)
    metrics["new_contradicting_links"] = len(new_contradiction_links)
    metrics["new_conflict_gaps"] = len(new_conflict_gaps)

    # 5) new_provenance_lead: a new relation="lead" link on eligible evidence.
    new_leads = sorted(_provenance_lead_pairs(after) - _provenance_lead_pairs(before))
    if new_leads:
        reasons.append("new_provenance_lead")
        affected_claims.update(claim_id for claim_id, _ in new_leads)
    metrics["new_provenance_leads"] = len(new_leads)

    # 6) claim_status_improvement: only the explicitly frozen improvement
    # edges count (e.g. pending -> searching, contested -> satisfied). Moving
    # into "unresolved" is a legitimate terminal state, never progress.
    before_claim_states = {claim.id: claim.state for claim in before.claims}
    improved_claims = sorted(
        claim.id
        for claim in after.claims
        if (before_claim_states.get(claim.id, claim.state), claim.state)
        in _CLAIM_IMPROVEMENT_EDGES
    )
    if improved_claims:
        reasons.append("claim_status_improvement")
        affected_claims.update(improved_claims)
    metrics["claims_improved"] = len(improved_claims)

    affected_gaps = sorted(gap.id for gap in after.gaps if gap.claim_id in affected_claims)

    return EvidenceGainResult(
        substantive_gain=bool(reasons),
        gain_reasons=tuple(reasons),
        affected_claim_ids=tuple(sorted(affected_claims)),
        affected_gap_ids=tuple(affected_gaps),
        metrics=metrics,
    )


@dataclass(frozen=True)
class SaturationState:
    """Per-gap / per-claim consecutive no-gain batch counters.

    Deliberately not a global run counter: one claim saturating must never
    stop research into another claim that is still gaining evidence.
    """

    no_gain_batches_by_claim: Mapping[str, int] = field(default_factory=dict)
    no_gain_batches_by_gap: Mapping[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "no_gain_batches_by_claim": dict(self.no_gain_batches_by_claim),
            "no_gain_batches_by_gap": dict(self.no_gain_batches_by_gap),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SaturationState":
        claims_raw = raw.get("no_gain_batches_by_claim") or {}
        gaps_raw = raw.get("no_gain_batches_by_gap") or {}
        return cls(
            no_gain_batches_by_claim={
                str(key): int(value)
                for key, value in claims_raw.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            },
            no_gain_batches_by_gap={
                str(key): int(value)
                for key, value in gaps_raw.items()
                if isinstance(value, (int, float)) and not isinstance(value, bool)
            },
        )


def update_saturation(
    previous: SaturationState,
    gain: EvidenceGainResult,
    *,
    handled_claim_ids: Iterable[str] = (),
    handled_gap_ids: Iterable[str] = (),
) -> SaturationState:
    """Advance per-claim/per-gap counters for one processed query batch.

    A handled claim/gap with substantive gain in this batch resets its
    counter; a handled claim/gap without gain increments it. Claims/gaps not
    handled in this batch keep their previous counters untouched.
    """
    affected_claims = set(gain.affected_claim_ids)
    affected_gaps = set(gain.affected_gap_ids)

    claim_counters = dict(previous.no_gain_batches_by_claim)
    for claim_id in sorted(set(handled_claim_ids)):
        if claim_id in affected_claims:
            claim_counters[claim_id] = 0
        else:
            claim_counters[claim_id] = claim_counters.get(claim_id, 0) + 1

    gap_counters = dict(previous.no_gain_batches_by_gap)
    for gap_id in sorted(set(handled_gap_ids)):
        if gap_id in affected_gaps:
            gap_counters[gap_id] = 0
        else:
            gap_counters[gap_id] = gap_counters.get(gap_id, 0) + 1

    return SaturationState(
        no_gain_batches_by_claim=claim_counters,
        no_gain_batches_by_gap=gap_counters,
    )


def saturated_claim_ids(
    state: SaturationState,
    extra_batch_eligible_claim_ids: Iterable[str] = (),
) -> tuple[str, ...]:
    """Claim ids that reached their saturation threshold.

    ``extra_batch_eligible_claim_ids`` marks claims eligible for the frozen
    third batch (critical/conflict status is decided by the caller, not by
    this primitive): they saturate at three consecutive no-gain batches
    instead of two.
    """
    extra_batch = set(extra_batch_eligible_claim_ids)
    return tuple(
        sorted(
            claim_id
            for claim_id, count in state.no_gain_batches_by_claim.items()
            if count
            >= SATURATION_NO_GAIN_BATCHES
            + (SATURATION_CRITICAL_EXTRA_BATCHES if claim_id in extra_batch else 0)
        )
    )


def saturated_gap_ids(
    state: SaturationState,
    extra_batch_eligible_gap_ids: Iterable[str] = (),
) -> tuple[str, ...]:
    """Gap ids that reached their saturation threshold (same frozen rule, with
    third-batch eligibility decided by the caller)."""
    extra_batch = set(extra_batch_eligible_gap_ids)
    return tuple(
        sorted(
            gap_id
            for gap_id, count in state.no_gain_batches_by_gap.items()
            if count
            >= SATURATION_NO_GAIN_BATCHES
            + (SATURATION_CRITICAL_EXTRA_BATCHES if gap_id in extra_batch else 0)
        )
    )


__all__ = [
    "EvidenceGainReason",
    "EvidenceGainResult",
    "SATURATION_CRITICAL_EXTRA_BATCHES",
    "SATURATION_NO_GAIN_BATCHES",
    "SaturationState",
    "evaluate_evidence_gain",
    "saturated_claim_ids",
    "saturated_gap_ids",
    "update_saturation",
]
