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
from src.web.research.evidence_gate import evidence_link_eligibility

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
    # ("pending", "searching") is deliberately ABSENT (R1): starting to work
    # on a claim is workflow progress, not epistemic gain — otherwise the
    # first query batch would always fake a gain and delay saturation.
    ("pending", "partially_satisfied"),
    ("searching", "partially_satisfied"),
    ("partially_satisfied", "satisfied"),
    ("contested", "partially_satisfied"),
    ("contested", "satisfied"),
    ("unresolved", "partially_satisfied"),
    ("unresolved", "satisfied"),
}

# Frozen gap-attribution markers (R3): a targeted conflict-flavoured gap is
# only credited by contradiction gains; a gap with a desired source role is
# credited by role upgrades or first evidence; any other targeted gap of an
# affected claim is credited by any claim-level gain.
_CONFLICT_GAP_MARKERS = ("conflict", "contradict", "counter")

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
    # R4: per-claim reason attribution. The batch-level gain_reasons list is
    # the union; this mapping is the audit fact the multi-wave runtime will
    # need for trace and durable resume (which claim was moved by what).
    gain_reasons_by_claim: Mapping[str, tuple[EvidenceGainReason, ...]] = field(
        default_factory=dict
    )

    def to_dict(self) -> dict[str, Any]:
        return {
            "substantive_gain": self.substantive_gain,
            "gain_reasons": list(self.gain_reasons),
            "gain_reasons_by_claim": {
                claim_id: list(reasons)
                for claim_id, reasons in self.gain_reasons_by_claim.items()
            },
            "affected_claim_ids": list(self.affected_claim_ids),
            "affected_gap_ids": list(self.affected_gap_ids),
            "metrics": dict(self.metrics),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "EvidenceGainResult":
        """Strict restore (P2): malformed or self-inconsistent payloads fail
        closed instead of silently degrading saturation truth."""
        if not isinstance(raw, Mapping):
            raise ValueError("evidence gain result must be an object")
        raw_reasons = raw.get("gain_reasons")
        if not isinstance(raw_reasons, list) or any(
            not isinstance(reason, str) or reason not in _GAIN_REASONS
            for reason in raw_reasons
        ):
            raise ValueError("invalid gain reasons")
        if len(set(raw_reasons)) != len(raw_reasons):
            raise ValueError("duplicate gain reasons")
        substantive = raw.get("substantive_gain")
        if not isinstance(substantive, bool):
            raise ValueError("substantive_gain must be a boolean")
        if substantive != bool(raw_reasons):
            raise ValueError("substantive_gain contradicts gain_reasons")
        for key in ("affected_claim_ids", "affected_gap_ids"):
            ids_raw = raw.get(key)
            if not isinstance(ids_raw, list) or any(
                not isinstance(item, str) or not item for item in ids_raw
            ):
                raise ValueError(f"invalid {key}")
            if len(set(ids_raw)) != len(ids_raw):
                raise ValueError(f"duplicate ids in {key}")
        metrics_raw = raw.get("metrics") or {}
        if not isinstance(metrics_raw, Mapping):
            raise ValueError("metrics must be an object")
        metrics: dict[str, int] = {}
        for key, value in metrics_raw.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError("metrics must be non-negative integers")
            metrics[str(key)] = value
        raw_by_claim = raw.get("gain_reasons_by_claim") or {}
        if not isinstance(raw_by_claim, Mapping):
            raise ValueError("gain_reasons_by_claim must be an object")
        reasons_by_claim: dict[str, tuple[EvidenceGainReason, ...]] = {}
        for claim_id, claim_reasons in raw_by_claim.items():
            if not isinstance(claim_reasons, list) or any(
                not isinstance(reason, str) or reason not in _GAIN_REASONS
                for reason in claim_reasons
            ):
                raise ValueError("invalid gain_reasons_by_claim entry")
            reasons_by_claim[str(claim_id)] = tuple(claim_reasons)  # type: ignore[arg-type]
        return cls(
            substantive_gain=substantive,
            gain_reasons=tuple(raw_reasons),  # type: ignore[arg-type]
            gain_reasons_by_claim=reasons_by_claim,
            affected_claim_ids=tuple(raw["affected_claim_ids"]),
            affected_gap_ids=tuple(raw["affected_gap_ids"]),
            metrics=metrics,
        )


def _eligible_support_links(state: ResearchState) -> dict[str, set[tuple[str, str, str]]]:
    """claim_id -> {(evidence_id, source_role, cluster_id)} for evidence the
    Evidence Gate would actually accept.

    R2: eligibility is the shared Gate predicate (requirement role match,
    cluster present, extraction eligible, successful read, freshness) —
    never a second, weaker rule. Only evidence-bearing relations (supports /
    qualifies) enter this map; background/lead links never count as
    substantive gain on their own.
    """
    evidence_by_id = {evidence.evidence_id: evidence for evidence in state.evidence}
    claims_by_id = {claim.id: claim for claim in state.claims}
    links: dict[str, set[tuple[str, str, str]]] = {}
    for link in state.evidence_links:
        claim = claims_by_id.get(link.claim_id)
        if claim is None:
            continue
        if link.relation not in _EVIDENCE_BEARING_RELATIONS:
            continue
        if not evidence_link_eligibility(
            claim=claim,
            link=link,
            evidence=evidence_by_id.get(link.evidence_id),
            reference_date=state.reference_date,
        ):
            continue
        links.setdefault(link.claim_id, set()).add(
            (link.evidence_id, link.source_role, link.source_cluster_id)
        )
    return links


def _contradiction_pairs(state: ResearchState) -> set[tuple[str, str]]:
    """Contradicts links the Gate would accept (shared eligibility, R2)."""
    evidence_by_id = {evidence.evidence_id: evidence for evidence in state.evidence}
    claims_by_id = {claim.id: claim for claim in state.claims}
    pairs: set[tuple[str, str]] = set()
    for link in state.evidence_links:
        if link.relation != "contradicts":
            continue
        claim = claims_by_id.get(link.claim_id)
        if claim is None:
            continue
        if not evidence_link_eligibility(
            claim=claim,
            link=link,
            evidence=evidence_by_id.get(link.evidence_id),
            reference_date=state.reference_date,
        ):
            continue
        pairs.add((link.claim_id, link.evidence_id))
    return pairs


def _provenance_lead_pairs(state: ResearchState) -> set[tuple[str, str]]:
    """Lead links on Gate-eligible evidence (shared eligibility, R2)."""
    evidence_by_id = {evidence.evidence_id: evidence for evidence in state.evidence}
    claims_by_id = {claim.id: claim for claim in state.claims}
    pairs: set[tuple[str, str]] = set()
    for link in state.evidence_links:
        if link.relation != "lead":
            continue
        claim = claims_by_id.get(link.claim_id)
        if claim is None:
            continue
        if not evidence_link_eligibility(
            claim=claim,
            link=link,
            evidence=evidence_by_id.get(link.evidence_id),
            reference_date=state.reference_date,
        ):
            continue
        pairs.add((link.claim_id, link.evidence_id))
    return pairs


def _best_role_rank(links: Mapping[str, set[tuple[str, str, str]]], claim_id: str) -> int:
    roles = {role for (_, role, _) in links.get(claim_id, set())}
    return max((_ROLE_RANK.get(role, 0) for role in roles), default=-1)


def _gap_credited(
    gap: Any,
    claim_reasons: set[EvidenceGainReason],
    before_links: Mapping[str, set[tuple[str, str, str]]],
    after_links: Mapping[str, set[tuple[str, str, str]]],
) -> bool:
    """R3/R5: decide whether a targeted gap is actually credited by this batch.

    Attribution uses only the reasons of the gap's OWN claim (R4: no
    cross-claim reason leakage), and a desired_source_role gap is credited by
    comparing the actual Gate-eligible roles before vs after (R5) — gaining a
    different role than the one the gap wants is real claim progress but not
    progress for this gap.
    """
    gap_type = str(getattr(gap, "gap_type", "")).casefold()
    if any(marker in gap_type for marker in _CONFLICT_GAP_MARKERS):
        return "new_contradiction" in claim_reasons
    desired_role = str(getattr(gap, "desired_source_role", "") or "").strip()
    if desired_role:
        before_roles = {role for (_, role, _) in before_links.get(gap.claim_id, set())}
        after_roles = {role for (_, role, _) in after_links.get(gap.claim_id, set())}
        return desired_role not in before_roles and desired_role in after_roles
    return bool(claim_reasons)


def evaluate_evidence_gain(
    before: ResearchState,
    after: ResearchState,
    *,
    target_gap_ids: Iterable[str] = (),
) -> EvidenceGainResult:
    """Compare two ResearchState snapshots under the frozen 6-reason taxonomy.

    ``target_gap_ids`` are the gaps this batch actually served. Gap
    attribution is never broadcast from claim-level gains: only a targeted
    gap whose own claim's gain reasons (R4) and actual role coverage (R5)
    were genuinely served by the batch is credited. The evaluation is pure
    and deterministic.
    """
    reasons: list[EvidenceGainReason] = []
    reasons_by_claim: dict[str, set[EvidenceGainReason]] = {}
    affected_claims: set[str] = set()
    metrics: dict[str, int] = {}

    def _record(reason: EvidenceGainReason, claim_ids: Iterable[str]) -> None:
        reasons.append(reason)
        for claim_id in claim_ids:
            affected_claims.add(claim_id)
            reasons_by_claim.setdefault(claim_id, set()).add(reason)

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
        _record("new_eligible_evidence", first_evidence_claims)
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
        _record("new_independent_cluster", new_cluster_claims)
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
        _record("better_source_role", role_upgraded_claims)
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
        _record(
            "new_contradiction",
            [claim_id for claim_id, _ in new_contradiction_links]
            + [gap.claim_id for gap in new_conflict_gaps],
        )
    metrics["new_contradicting_links"] = len(new_contradiction_links)
    metrics["new_conflict_gaps"] = len(new_conflict_gaps)

    # 5) new_provenance_lead: a new relation="lead" link on eligible evidence.
    new_leads = sorted(_provenance_lead_pairs(after) - _provenance_lead_pairs(before))
    if new_leads:
        _record("new_provenance_lead", [claim_id for claim_id, _ in new_leads])
    metrics["new_provenance_leads"] = len(new_leads)

    # 6) claim_status_improvement: only the explicitly frozen improvement
    # edges count. Moving into "unresolved" is a legitimate terminal state,
    # never progress.
    before_claim_states = {claim.id: claim.state for claim in before.claims}
    improved_claims = sorted(
        claim.id
        for claim in after.claims
        if (before_claim_states.get(claim.id, claim.state), claim.state)
        in _CLAIM_IMPROVEMENT_EDGES
    )
    if improved_claims:
        _record("claim_status_improvement", improved_claims)
    metrics["claims_improved"] = len(improved_claims)

    # R3/R4/R5: explicit gap attribution. Only targeted gaps whose OWN claim
    # gained (R4: no cross-claim reason leakage) and whose type/role was
    # genuinely served (R5: desired role must actually appear) are credited.
    targeted_ids = set(target_gap_ids)
    affected_gaps = sorted(
        gap.id
        for gap in after.gaps
        if gap.id in targeted_ids
        and _gap_credited(
            gap,
            reasons_by_claim.get(gap.claim_id, set()),
            before_links,
            after_links,
        )
    )

    return EvidenceGainResult(
        substantive_gain=bool(reasons),
        gain_reasons=tuple(reasons),
        gain_reasons_by_claim={
            claim_id: tuple(sorted(claim_reasons))
            for claim_id, claim_reasons in sorted(reasons_by_claim.items())
        },
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
        """Strict restore (P2): counters must be non-negative integers."""
        if not isinstance(raw, Mapping):
            raise ValueError("saturation state must be an object")

        def counters(key: str) -> dict[str, int]:
            raw_counters = raw.get(key) or {}
            if not isinstance(raw_counters, Mapping):
                raise ValueError(f"{key} must be an object")
            result: dict[str, int] = {}
            for counter_key, value in raw_counters.items():
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                ):
                    raise ValueError("saturation counters must be non-negative integers")
                result[str(counter_key)] = value
            return result

        return cls(
            no_gain_batches_by_claim=counters("no_gain_batches_by_claim"),
            no_gain_batches_by_gap=counters("no_gain_batches_by_gap"),
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
