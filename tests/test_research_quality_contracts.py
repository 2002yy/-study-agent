from __future__ import annotations

from copy import deepcopy

import pytest

from src.domain.evidence import ClaimEvidenceLinkV1
from src.web.research.contracts import (
    RESEARCH_STATE_SCHEMA_VERSION,
    ConflictGap,
    EvidenceCluster,
    EvidenceGap,
    EvidenceRequirement,
    ResearchBrief,
    ResearchBudget,
    ResearchClaim,
    ResearchClaimEvidenceLink,
    ResearchEvidence,
    ResearchQuestion,
    ResearchState,
    ResearchTraceEvent,
    build_research_state,
)


def _state() -> ResearchState:
    budget = ResearchBudget(
        max_candidates=20,
        max_reads=8,
        soft_timeout_seconds=45,
        hard_timeout_seconds=60,
        max_total_chars=16000,
    )
    return build_research_state(
        mode="shadow",
        questions=[
            ResearchQuestion(
                id="q_market",
                question_surface="What is the current market position?",
                priority="critical",
                state="partially_satisfied",
            )
        ],
        claims=[
            ResearchClaim(
                id="claim_price",
                question_id="q_market",
                text="The published list price is 25 dollars.",
                kind="factual",
                priority="critical",
                state="contested",
                evidence_requirement=EvidenceRequirement(
                    source_roles=("primary", "independent_secondary"),
                    min_independent_sources=2,
                    requires_primary_source=True,
                ),
            )
        ],
        evidence=[
            ResearchEvidence(
                "ev_official",
                locator="pricing#current",
                lifecycle_status="selected",
                extraction_status="eligible",
            ),
            ResearchEvidence(
                "ev_review",
                anchored_spans=("Observed price: $30",),
                lifecycle_status="read",
                extraction_status="eligible",
            ),
        ],
        evidence_links=[
            ResearchClaimEvidenceLink(
                link=ClaimEvidenceLinkV1(
                    claim_id="claim_price",
                    evidence_id="ev_official",
                    support_type="supports",
                    confidence=0.9,
                ),
                source_role="primary",
                source_cluster_id="cluster_official",
            ),
            ResearchClaimEvidenceLink(
                link=ClaimEvidenceLinkV1(
                    claim_id="claim_price",
                    evidence_id="ev_review",
                    support_type="contradicts",
                    confidence=0.8,
                ),
                source_role="independent_secondary",
                source_cluster_id="cluster_review",
                caveats=("Different region",),
            ),
        ],
        source_clusters=[
            EvidenceCluster("cluster_official", ("ev_official",), "primary"),
            EvidenceCluster(
                "cluster_review", ("ev_review",), "independent_secondary"
            ),
        ],
        gaps=[EvidenceGap("gap_region", "claim_price", "region_scope")],
        conflict_gaps=[
            ConflictGap(
                "conflict_price",
                "claim_price",
                supporting_evidence_ids=("ev_official",),
                contradicting_evidence_ids=("ev_review",),
            )
        ],
        budget=budget,
        trace=[
            ResearchTraceEvent(
                sequence=1,
                timestamp="2026-08-26T12:00:00Z",
                run_id="run_contract_test",
                event_type="gate_evaluated",
                reason="Independent prices disagree.",
                claim_id="claim_price",
                gap_id="conflict_price",
                budget_before=budget,
                budget_after=budget,
            )
        ],
        brief=ResearchBrief(
            claim_ids=("claim_price",),
            unresolved_claim_ids=("claim_price",),
            conflict_gap_ids=("conflict_price",),
            outline=("Price differs by region.",),
        ),
        known_evidence_ids={"ev_official", "ev_review"},
    )


def test_round_trip_is_versioned_and_deterministic() -> None:
    state = _state()
    raw = state.to_dict()

    assert raw["schema_version"] == RESEARCH_STATE_SCHEMA_VERSION
    assert ResearchState.from_dict(
        raw, known_evidence_ids={"ev_review", "ev_official"}
    ) == state


def test_builder_orders_unordered_inputs() -> None:
    state = _state()
    rebuilt = build_research_state(
        mode=state.mode,
        questions=reversed(state.questions),
        claims=reversed(state.claims),
        evidence=reversed(state.evidence),
        evidence_links=reversed(state.evidence_links),
        source_clusters=reversed(state.source_clusters),
        gaps=reversed(state.gaps),
        conflict_gaps=reversed(state.conflict_gaps),
        budget=state.budget,
        trace=reversed(state.trace),
        brief=state.brief,
        known_evidence_ids={"ev_review", "ev_official"},
    )

    assert rebuilt.to_dict() == state.to_dict()


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("claims", 0, "kind"), "opinion"),
        (("claims", 0, "priority"), "urgent"),
        (("claims", 0, "state"), "done"),
        (("evidence_links", 0, "relation"), "mentions"),
    ],
)
def test_invalid_contract_enums_fail_closed(path: tuple[object, ...], value: str) -> None:
    raw = _state().to_dict()
    target: object = raw
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]

    with pytest.raises(ValueError, match="invalid"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_unknown_server_owned_evidence_id_is_rejected() -> None:
    raw = _state().to_dict()
    raw["evidence_links"][0]["evidence_id"] = "ev_model_invented"

    with pytest.raises(ValueError, match="unknown evidence id"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_duplicate_claim_and_link_are_rejected() -> None:
    raw = _state().to_dict()
    raw["claims"].append(deepcopy(raw["claims"][0]))
    with pytest.raises(ValueError, match="duplicate claim id"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})

    raw = _state().to_dict()
    raw["evidence_links"].append(deepcopy(raw["evidence_links"][0]))
    with pytest.raises(ValueError, match="duplicate research claim evidence link"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("max_reads", 21, "max reads"),
        ("soft_timeout_seconds", 61, "soft"),
        ("hard_timeout_seconds", float("inf"), "finite"),
        ("max_total_chars", -1, "cannot be negative"),
    ],
)
def test_budget_boundaries_fail_closed(field: str, value: object, message: str) -> None:
    raw = _state().to_dict()
    raw["budget"][field] = value
    with pytest.raises(ValueError, match=message):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_link_strength_must_be_finite_probability() -> None:
    raw = _state().to_dict()
    raw["evidence_links"][0]["strength"] = 1.1
    with pytest.raises(ValueError, match="between 0 and 1"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_gap_conflict_and_brief_references_are_checked() -> None:
    raw = _state().to_dict()
    raw["gaps"][0]["claim_id"] = "claim_missing"
    with pytest.raises(ValueError, match="unknown claim id in evidence gap"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})

    raw = _state().to_dict()
    raw["conflict_gaps"][0]["contradicting_evidence_ids"] = ["ev_missing"]
    with pytest.raises(ValueError, match="unknown server-owned evidence id"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})

    raw = _state().to_dict()
    raw["brief"]["claim_ids"] = ["claim_missing"]
    with pytest.raises(ValueError, match="unknown brief claim id"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_conflict_gap_requires_matching_support_and_contradiction_links() -> None:
    raw = _state().to_dict()
    raw["evidence_links"][0]["relation"] = "qualifies"
    with pytest.raises(ValueError, match="requires a supports link"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})

    raw = _state().to_dict()
    raw["evidence_links"][1]["relation"] = "background"
    with pytest.raises(ValueError, match="requires a contradicts link"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_brief_cannot_mark_satisfied_claim_unresolved() -> None:
    raw = _state().to_dict()
    raw["claims"][0]["state"] = "satisfied"
    with pytest.raises(ValueError, match="satisfied claim cannot be unresolved"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_unresolved_and_unavailable_remain_distinct_states() -> None:
    raw = _state().to_dict()
    raw["claims"][0]["state"] = "unresolved"
    unresolved = ResearchState.from_dict(
        raw, known_evidence_ids={"ev_official", "ev_review"}
    )
    raw["claims"][0]["state"] = "unavailable"
    unavailable = ResearchState.from_dict(
        raw, known_evidence_ids={"ev_official", "ev_review"}
    )

    assert unresolved.claims[0].state == "unresolved"
    assert unavailable.claims[0].state == "unavailable"


def test_unknown_schema_and_raw_page_fields_fail_closed() -> None:
    raw = _state().to_dict()
    raw["schema_version"] = "research-state-v999"
    with pytest.raises(ValueError, match="schema_version"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})

    raw = _state().to_dict()
    raw["evidence"][0]["raw_page_body"] = "must not persist"
    with pytest.raises(ValueError, match="raw_page_body"):
        ResearchState.from_dict(raw, known_evidence_ids={"ev_official", "ev_review"})


def test_contract_has_no_raw_body_or_secret_fields() -> None:
    raw = _state().to_dict()
    serialized_keys: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            serialized_keys.update(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(raw)
    assert not ({"raw_page_body", "page_body", "api_key", "secret", "token"} & serialized_keys)
