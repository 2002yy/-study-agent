from __future__ import annotations

from copy import deepcopy

import pytest

from src.web.research.candidate_assessment import (
    CANDIDATE_ASSESSMENT_SCHEMA_VERSION,
    build_candidate_assessment_request,
    parse_candidate_assessment_response,
)
from src.web.research.candidate_pool import CandidatePoolItem
from src.web.research.contracts import EvidenceRequirement, ResearchClaim
from src.web.research.gap_planner import GapSearchIntent
from src.web.research.source_cluster import CandidateClusterAssignment


def _candidate(candidate_id: str) -> CandidatePoolItem:
    url = f"https://{candidate_id}.example/item"
    return CandidatePoolItem(
        id=candidate_id,
        canonical_url=url,
        url=url,
        title=f"Title {candidate_id}",
        snippet="bounded snippet",
        source="Publisher",
        published_at="2026-08-20",
        query_ids=("query",),
        intents=(GapSearchIntent.PRIMARY,),
        providers=("searxng",),
        first_seen_rank=1,
    )


def _claim() -> ResearchClaim:
    return ResearchClaim(
        id="claim-1",
        question_id="question-1",
        text="Official current policy",
        kind="factual",
        priority="critical",
        state="searching",
        evidence_requirement=EvidenceRequirement(
            source_roles=("primary", "independent_secondary"),
            min_independent_sources=1,
            requires_primary_source=True,
            requires_successful_read=True,
            requires_dated_evidence=True,
        ),
    )


def _payload(candidate_ids: tuple[str, ...]) -> dict:
    return {
        "schema_version": CANDIDATE_ASSESSMENT_SCHEMA_VERSION,
        "assessments": [
            {
                "candidate_id": candidate_id,
                "relevance": "answer_relevant",
                "relevance_confidence": 0.8,
                "source_role": "primary",
                "source_role_confidence": 0.9,
                "expected_gain_signals": ["new_primary"],
            }
            for candidate_id in candidate_ids
        ],
    }


def _assignment(candidate_id: str) -> CandidateClusterAssignment:
    return CandidateClusterAssignment(
        candidate_id=candidate_id,
        cluster_id=f"cluster-{candidate_id}",
        independence_key=f"publisher:{candidate_id}",
        basis="publisher",
        source_role="primary",
    )


def test_request_is_bounded_and_contains_no_raw_page_body() -> None:
    request = build_candidate_assessment_request((_candidate("a"),), claim=_claim())
    payload = request.to_dict()
    assert payload["schema_version"] == CANDIDATE_ASSESSMENT_SCHEMA_VERSION
    assert set(payload["candidates"][0]) == {
        "candidate_id",
        "title",
        "snippet",
        "canonical_url",
        "published_at",
        "query_intents",
    }
    assert "body" not in payload["candidates"][0]


def test_parser_attaches_server_owned_cluster_freshness_and_cost() -> None:
    candidates = (_candidate("a"), _candidate("b"))
    request = build_candidate_assessment_request(candidates, claim=_claim())
    parsed = parse_candidate_assessment_response(
        _payload(("a", "b")),
        request=request,
        cluster_assignments={"a": _assignment("a"), "b": _assignment("b")},
        freshness_scores={"a": 0.75},
        read_costs={"a": 2.5},
    )
    assert parsed["a"].cluster_id == "cluster-a"
    assert parsed["a"].freshness_score == 0.75
    assert parsed["a"].estimated_read_cost == 2.5
    assert parsed["b"].freshness_score == 0.0


@pytest.mark.parametrize(
    "mutation",
    ["missing", "extra", "confidence", "cluster", "infinite_cost"],
)
def test_parser_fails_closed_on_untrusted_or_incomplete_output(mutation: str) -> None:
    candidates = (_candidate("a"), _candidate("b"))
    request = build_candidate_assessment_request(candidates, claim=_claim())
    payload = deepcopy(_payload(("a", "b")))
    if mutation == "missing":
        payload["assessments"].pop()
    elif mutation == "extra":
        payload["assessments"][0]["explanation"] = "unbounded"
    elif mutation == "confidence":
        payload["assessments"][0]["relevance_confidence"] = 2.0
    elif mutation == "cluster":
        payload["assessments"][0]["cluster_id"] = "model-invented"
    else:
        pass
    with pytest.raises(ValueError):
        parse_candidate_assessment_response(
            payload,
            request=request,
            cluster_assignments={"a": _assignment("a"), "b": _assignment("b")},
            read_costs={"a": float("inf")} if mutation == "infinite_cost" else None,
        )
