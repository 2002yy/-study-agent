"""Frozen test matrix for RQCE-P1-C batch 1 (Evidence Gain + Saturation)."""

from __future__ import annotations

from typing import Any

from src.domain.evidence import ClaimEvidenceLinkV1
from src.web.research.contracts import (
    ConflictGap,
    EvidenceCluster,
    EvidenceGap,
    EvidenceRequirement,
    ResearchBudget,
    ResearchClaim,
    ResearchClaimEvidenceLink,
    ResearchEvidence,
    ResearchQuestion,
    build_research_state,
)
from src.web.research.evidence_gain import (
    SATURATION_NO_GAIN_BATCHES,
    EvidenceGainResult,
    SaturationState,
    evaluate_evidence_gain,
    saturated_claim_ids,
    saturated_gap_ids,
    update_saturation,
)


_ALL_ROLES = (
    "primary",
    "authoritative_secondary",
    "independent_secondary",
    "community",
    "aggregator",
)


def _claim(
    claim_id: str,
    *,
    state: str = "pending",
    priority: str = "critical",
    requirement: EvidenceRequirement | None = None,
) -> ResearchClaim:
    return ResearchClaim(
        id=claim_id,
        question_id="q1",
        text=f"claim {claim_id}",
        kind="factual",
        priority=priority,  # type: ignore[arg-type]
        state=state,  # type: ignore[arg-type]
        evidence_requirement=requirement or EvidenceRequirement(source_roles=_ALL_ROLES),
    )


def _evidence(
    evidence_id: str,
    *,
    extraction_status: str = "eligible",
    lifecycle_status: str = "read",
    published_at: str = "",
) -> ResearchEvidence:
    return ResearchEvidence(
        evidence_id=evidence_id,
        locator="anchor",
        anchored_spans=("anchor",),
        lifecycle_status=lifecycle_status,  # type: ignore[arg-type]
        extraction_status=extraction_status,  # type: ignore[arg-type]
        published_at=published_at,
    )


def _link(
    claim_id: str,
    evidence_id: str,
    *,
    relation: str = "supports",
    source_role: str = "primary",
    cluster_id: str = "CX",
) -> ResearchClaimEvidenceLink:
    return ResearchClaimEvidenceLink(
        link=ClaimEvidenceLinkV1(
            claim_id=claim_id,
            evidence_id=evidence_id,
            support_type=relation,  # type: ignore[arg-type]
            confidence=0.95,
        ),
        source_role=source_role,
        source_cluster_id=cluster_id,
        locator="anchor",
    )


def _gap(
    gap_id: str,
    claim_id: str,
    *,
    state: str = "open",
    gap_type: str = "evidence",
    desired_source_role: str = "",
) -> EvidenceGap:
    return EvidenceGap(
        id=gap_id,
        claim_id=claim_id,
        gap_type=gap_type,
        desired_source_role=desired_source_role,
        priority="critical",
        state=state,  # type: ignore[arg-type]
    )


def _state(
    *,
    claims: tuple[ResearchClaim, ...] = (),
    evidence: tuple[ResearchEvidence, ...] = (),
    links: tuple[ResearchClaimEvidenceLink, ...] = (),
    clusters: tuple[EvidenceCluster, ...] = (),
    gaps: tuple[EvidenceGap, ...] = (),
    conflict_gaps: tuple[ConflictGap, ...] = (),
) -> Any:
    if not clusters:
        cluster_ids = sorted(
            {link.source_cluster_id for link in links if link.source_cluster_id}
        )
        clusters = tuple(
            EvidenceCluster(
                id=cluster_id,
                evidence_ids=tuple(
                    link.evidence_id
                    for link in links
                    if link.source_cluster_id == cluster_id
                ),
            )
            for cluster_id in cluster_ids
        )
    return build_research_state(
        mode="active",
        questions=(ResearchQuestion(id="q1", question_surface="question"),),
        claims=claims,
        evidence=evidence,
        evidence_links=links,
        source_clusters=clusters,
        gaps=gaps,
        conflict_gaps=conflict_gaps,
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date="2026-08-28",
        known_evidence_ids=tuple(item.evidence_id for item in evidence),
    )


def _single_claim_state(claim_id: str, **kwargs: Any) -> Any:
    return _state(claims=(_claim(claim_id, **kwargs),))


def test_same_cluster_new_url_same_role_is_not_gain() -> None:
    """New URL in an already-covered cluster with the same role: no gain."""
    before = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", source_role="primary", cluster_id="CX"),),
    )
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("C1", "E1", source_role="primary", cluster_id="CX"),
            _link("C1", "E2", source_role="primary", cluster_id="CX"),
        ),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is False
    assert result.gain_reasons == ()


def test_new_independent_cluster_is_gain() -> None:
    before = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", source_role="primary", cluster_id="CX"),),
    )
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("C1", "E1", source_role="primary", cluster_id="CX"),
            _link("C1", "E2", source_role="independent_secondary", cluster_id="CY"),
        ),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is True
    assert "new_independent_cluster" in result.gain_reasons
    assert result.affected_claim_ids == ("C1",)
    assert result.affected_gap_ids == ()


def test_secondary_to_primary_role_upgrade_is_gain() -> None:
    before = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", source_role="independent_secondary", cluster_id="CX"),),
    )
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("C1", "E1", source_role="independent_secondary", cluster_id="CX"),
            _link("C1", "E2", source_role="primary", cluster_id="CX"),
        ),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is True
    assert "better_source_role" in result.gain_reasons


def test_new_contradiction_is_gain() -> None:
    before = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", relation="supports", cluster_id="CX"),),
    )
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("C1", "E1", relation="supports", cluster_id="CX"),
            _link("C1", "E2", relation="contradicts", cluster_id="CY"),
        ),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is True
    assert "new_contradiction" in result.gain_reasons


def test_new_provenance_lead_is_gain() -> None:
    before = _state(claims=(_claim("C1"),))
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", relation="lead", source_role="primary", cluster_id="CX"),),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is True
    assert "new_provenance_lead" in result.gain_reasons


def test_claim_status_improvement_is_gain() -> None:
    before = _single_claim_state("C1", state="partially_satisfied")
    after = _single_claim_state("C1", state="satisfied")

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is True
    assert "claim_status_improvement" in result.gain_reasons
    assert result.affected_claim_ids == ("C1",)


def test_result_count_growth_alone_is_not_gain() -> None:
    """Equal ResearchState semantics (more raw results, nothing else) = no gain."""
    state = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", source_role="primary", cluster_id="CX"),),
    )

    result = evaluate_evidence_gain(state, state)

    assert result.substantive_gain is False
    assert result.gain_reasons == ()


def test_first_eligible_evidence_for_claim_is_gain() -> None:
    """A claim going from zero eligible evidence to one is substantive."""
    before = _single_claim_state("C1")
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", source_role="primary", cluster_id="CX"),),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is True
    assert "new_eligible_evidence" in result.gain_reasons


def test_first_no_gain_batch_continues() -> None:
    state = SaturationState()
    updated = update_saturation(state, evaluate_evidence_gain(_empty(), _empty()), handled_claim_ids=("C1",))

    assert updated.no_gain_batches_by_claim["C1"] == 1
    assert saturated_claim_ids(updated) == ()


def _empty() -> Any:
    return _state(claims=(_claim("C1"),))


def test_second_consecutive_no_gain_batch_saturates() -> None:
    state = SaturationState()
    state = update_saturation(state, evaluate_evidence_gain(_empty(), _empty()), handled_claim_ids=("C1",))
    state = update_saturation(state, evaluate_evidence_gain(_empty(), _empty()), handled_claim_ids=("C1",))

    assert state.no_gain_batches_by_claim["C1"] == SATURATION_NO_GAIN_BATCHES
    assert saturated_claim_ids(state) == ("C1",)
    assert state.no_gain_batches_by_gap.get("G1", 0) >= 0


def test_critical_claim_gets_third_batch() -> None:
    state = SaturationState()
    for _ in range(2):
        state = update_saturation(
            state,
            evaluate_evidence_gain(_empty(), _empty()),
            handled_claim_ids=("C1",),
            handled_gap_ids=("G1",),
        )
    assert state.no_gain_batches_by_claim["C1"] == 2

    # Critical claims take the frozen third batch before saturating; the
    # third-batch eligibility is passed in by the caller.
    assert saturated_claim_ids(state, extra_batch_eligible_claim_ids=("C1",)) == ()
    assert saturated_gap_ids(state, extra_batch_eligible_gap_ids=("G1",)) == ()
    assert saturated_claim_ids(state) == ("C1",)


def test_third_no_gain_batch_saturates_critical_claim() -> None:
    state = SaturationState()
    for _ in range(3):
        state = update_saturation(
            state,
            evaluate_evidence_gain(_empty(), _empty()),
            handled_claim_ids=("C1",),
            handled_gap_ids=("G1",),
        )

    assert saturated_claim_ids(state, extra_batch_eligible_claim_ids=("C1",)) == ("C1",)
    assert saturated_gap_ids(state, extra_batch_eligible_gap_ids=("G1",)) == ("G1",)


def test_gain_resets_only_affected_claim_and_gap() -> None:
    """Claim A saturated while claim B keeps gaining: only A stops."""
    state = SaturationState()
    # Claim A: two no-gain batches -> saturated.
    for _ in range(2):
        state = update_saturation(
            state,
            evaluate_evidence_gain(_empty(), _empty()),
            handled_claim_ids=("A", "B"),
            handled_gap_ids=("GA", "GB"),
        )

    # Claim B gains in this batch (new independent cluster); A stays no-gain.
    before = _state(
        claims=(_claim("A"), _claim("B")),
        evidence=(_evidence("E1"),),
        links=(_link("B", "E1", source_role="primary", cluster_id="CX"),),
        gaps=(_gap("GA", "A"), _gap("GB", "B")),
    )
    after = _state(
        claims=(_claim("A"), _claim("B")),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("B", "E1", source_role="primary", cluster_id="CX"),
            _link("B", "E2", source_role="independent_secondary", cluster_id="CY"),
        ),
        gaps=(_gap("GA", "A"), _gap("GB", "B")),
    )
    state = update_saturation(
        state,
        evaluate_evidence_gain(before, after, target_gap_ids=("GA", "GB")),
        handled_claim_ids=("A", "B"),
        handled_gap_ids=("GA", "GB"),
    )

    assert state.no_gain_batches_by_claim["A"] == 3
    assert state.no_gain_batches_by_claim["B"] == 0
    assert state.no_gain_batches_by_gap["GA"] == 3
    assert state.no_gain_batches_by_gap["GB"] == 0
    assert saturated_claim_ids(state) == ("A",)


def test_gain_result_roundtrips_through_dict() -> None:
    before = _single_claim_state("C1")
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", source_role="primary", cluster_id="CX"),),
    )

    result = evaluate_evidence_gain(before, after)
    restored = EvidenceGainResult.from_dict(result.to_dict())

    assert restored.substantive_gain == result.substantive_gain
    assert restored.gain_reasons == result.gain_reasons
    assert restored.affected_claim_ids == result.affected_claim_ids
    assert restored.affected_gap_ids == result.affected_gap_ids
    assert restored.metrics == result.metrics

    saturation = SaturationState.from_dict(
        SaturationState(
            no_gain_batches_by_claim={"C1": 2},
            no_gain_batches_by_gap={"G1": 1},
        ).to_dict()
    )
    assert saturation.no_gain_batches_by_claim == {"C1": 2}
    assert saturation.no_gain_batches_by_gap == {"G1": 1}

def test_new_cluster_with_only_background_links_is_not_gain() -> None:
    """A new cluster carrying only background material must not extend research."""
    before = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", relation="supports", cluster_id="CX"),),
    )
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("C1", "E1", relation="supports", cluster_id="CX"),
            _link("C1", "E2", relation="background", cluster_id="CY"),
        ),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is False
    assert result.gain_reasons == ()


def test_background_link_cannot_be_first_eligible_evidence() -> None:
    """The 0 -> 1 rule only fires for evidence-bearing relations."""
    before = _single_claim_state("C1")
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", relation="background", cluster_id="CX"),),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is False
    assert "new_eligible_evidence" not in result.gain_reasons


def test_searching_to_unresolved_is_not_improvement() -> None:
    """Moving into unresolved is a legitimate terminal state, never progress."""
    before = _single_claim_state("C1", state="searching")
    after = _single_claim_state("C1", state="unresolved")

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is False
    assert "claim_status_improvement" not in result.gain_reasons


def test_contradiction_metrics_count_links_and_gaps_separately() -> None:
    """One real-world conflict (link + gap) must not double-count in metrics."""
    before = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", relation="supports", cluster_id="CX"),),
    )
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("C1", "E1", relation="supports", cluster_id="CX"),
            _link("C1", "E2", relation="contradicts", cluster_id="CY"),
        ),
        conflict_gaps=(
            ConflictGap(
                id="CG1",
                claim_id="C1",
                supporting_evidence_ids=("E1",),
                contradicting_evidence_ids=("E2",),
            ),
        ),
    )

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is True
    assert "new_contradiction" in result.gain_reasons
    assert result.metrics["new_contradicting_links"] == 1
    assert result.metrics["new_conflict_gaps"] == 1
    assert "new_contradictions" not in result.metrics

def test_pending_to_searching_with_zero_evidence_is_not_gain() -> None:
    """R1: workflow progress is not epistemic gain (no fake first batch)."""
    before = _single_claim_state("C1", state="pending")
    after = _single_claim_state("C1", state="searching")

    result = evaluate_evidence_gain(before, after)

    assert result.substantive_gain is False
    assert result.gain_reasons == ()
    updated = update_saturation(
        SaturationState(), result, handled_claim_ids=("C1",)
    )
    assert updated.no_gain_batches_by_claim["C1"] == 1


def test_wrong_role_evidence_is_not_gain() -> None:
    """R2: a primary source cannot satisfy a community-only requirement."""
    requirement = EvidenceRequirement(source_roles=("community",))
    before = _state(
        claims=(_claim("C1", requirement=requirement),),
        evidence=(_evidence("E1"),),
        links=(
            _link(
                "C1",
                "E1",
                source_role="community",
                cluster_id="CX",
            ),
        ),
    )
    after = _state(
        claims=(_claim("C1", requirement=requirement),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link(
                "C1",
                "E1",
                source_role="community",
                cluster_id="CX",
            ),
            _link(
                "C1",
                "E2",
                source_role="primary",
                cluster_id="CY",
            ),
        ),
    )

    result = evaluate_evidence_gain(before, after)

    # The Gate would reject E2 for this claim; Gain must agree.
    assert result.substantive_gain is False
    assert result.gain_reasons == ()


def test_stale_and_unread_evidence_are_not_gain() -> None:
    """R2: freshness and successful-read rules bind Gain to the Gate."""
    stale_requirement = EvidenceRequirement(
        source_roles=_ALL_ROLES,
        max_age_days=30,
    )
    before_stale = _state(
        claims=(_claim("C1", requirement=stale_requirement),),
    )
    after_stale = _state(
        claims=(_claim("C1", requirement=stale_requirement),),
        evidence=(
            _evidence("E1", published_at="2020-01-01"),
        ),
        links=(
            _link("C1", "E1", source_role="primary", cluster_id="CX"),
        ),
    )
    assert evaluate_evidence_gain(before_stale, after_stale).substantive_gain is False

    unread_requirement = EvidenceRequirement(
        source_roles=_ALL_ROLES,
        requires_successful_read=True,
    )
    before_unread = _state(
        claims=(_claim("C2", requirement=unread_requirement),),
    )
    after_unread = _state(
        claims=(_claim("C2", requirement=unread_requirement),),
        evidence=(
            _evidence("E3", lifecycle_status="candidate"),
        ),
        links=(
            _link("C2", "E3", source_role="primary", cluster_id="CX"),
        ),
    )
    assert evaluate_evidence_gain(before_unread, after_unread).substantive_gain is False


def test_gap_attribution_is_not_broadcast_from_claim_gain() -> None:
    """R3: one claim, two gaps, only G2 served -> G1 counter must not reset."""
    before = _state(
        claims=(_claim("C1"),),
        gaps=(_gap("G1", "C1", gap_type="primary_missing", desired_source_role="primary"), _gap("G2", "C1", gap_type="independent_sources")),
    )
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"), _evidence("E2")),
        links=(
            _link("C1", "E1", source_role="primary", cluster_id="CX"),
            _link("C1", "E2", source_role="independent_secondary", cluster_id="CY"),
        ),
        gaps=(_gap("G1", "C1", gap_type="primary_missing", desired_source_role="primary"), _gap("G2", "C1", gap_type="independent_sources")),
    )
    assert evaluate_evidence_gain(before, after).substantive_gain is True

    # This batch targeted G1 and G2; both are served by the claim-level gain.
    result = evaluate_evidence_gain(before, after, target_gap_ids=("G1", "G2"))
    assert result.affected_gap_ids == ("G1", "G2")

    # But a batch targeting only G2 must not reset G1's saturation counter.
    result_g2_only = evaluate_evidence_gain(before, after, target_gap_ids=("G2",))
    assert result_g2_only.affected_claim_ids == ("C1",)
    assert result_g2_only.affected_gap_ids == ("G2",)

    state = SaturationState(no_gain_batches_by_claim={"C1": 1}, no_gain_batches_by_gap={"G1": 1, "G2": 1})
    state = update_saturation(
        state,
        result_g2_only,
        handled_claim_ids=("C1",),
        handled_gap_ids=("G1", "G2"),
    )
    assert state.no_gain_batches_by_claim["C1"] == 0
    # G1 (primary gap) was handled but not served: its counter increments.
    assert state.no_gain_batches_by_gap["G1"] == 2
    assert state.no_gain_batches_by_gap["G2"] == 0


def test_conflict_gap_is_only_credited_by_contradiction_gain() -> None:
    """R3: a conflict-flavoured gap is not reset by unrelated claim gains."""
    gap = _gap("G1", "C1", gap_type="open_conflict")
    before = _state(claims=(_claim("C1"),), gaps=(gap,))
    after = _state(
        claims=(_claim("C1"),),
        evidence=(_evidence("E1"),),
        links=(_link("C1", "E1", source_role="primary", cluster_id="CX"),),
        gaps=(gap,),
    )

    result = evaluate_evidence_gain(before, after, target_gap_ids=("G1",))

    assert result.affected_claim_ids == ("C1",)
    assert result.affected_gap_ids == ()


def test_serialization_fails_closed_on_malformed_payloads() -> None:
    """P2: contracts must reject invalid persisted payloads, not degrade."""
    import pytest

    valid = EvidenceGainResult(
        substantive_gain=True,
        gain_reasons=("new_independent_cluster",),
        affected_claim_ids=("C1",),
        affected_gap_ids=("G1",),
        metrics={"new_cluster_claims": 1},
    )
    restored = EvidenceGainResult.from_dict(valid.to_dict())
    assert restored.substantive_gain is True

    with pytest.raises(ValueError):
        EvidenceGainResult.from_dict({"substantive_gain": True, "gain_reasons": []})
    with pytest.raises(ValueError):
        EvidenceGainResult.from_dict(
            {"substantive_gain": False, "gain_reasons": ["new_contradiction"]}
        )
    with pytest.raises(ValueError):
        EvidenceGainResult.from_dict(
            {"substantive_gain": True, "gain_reasons": ["not_a_reason"]}
        )
    with pytest.raises(ValueError):
        SaturationState.from_dict({"no_gain_batches_by_claim": {"C1": -1}})
    with pytest.raises(ValueError):
        SaturationState.from_dict({"no_gain_batches_by_claim": {"C1": 1.5}})
    with pytest.raises(ValueError):
        EvidenceGainResult.from_dict("not an object")
    with pytest.raises(ValueError):
        SaturationState.from_dict("not an object")
