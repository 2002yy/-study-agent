from __future__ import annotations

from typing import Any

from src.web.research.candidate_assessment import (
    CANDIDATE_ASSESSMENT_SCHEMA_VERSION,
    build_candidate_assessment_request,
    parse_candidate_assessment_response,
)
from src.web.research.candidate_pool import execute_candidate_pool_batch
from src.web.research.candidate_ranking import rank_candidate_pool
from src.web.research.contracts import (
    EvidenceGap,
    EvidenceRequirement,
    ResearchBudget,
    ResearchClaim,
)
from src.web.research.gap_planner import plan_gap_queries
from src.web.research.scheduler import plan_read_wave
from src.web.research.source_cluster import (
    CandidateSourceProfile,
    cluster_candidate_sources,
)


def test_off_target_first_nonempty_cannot_close_or_win_read_wave() -> None:
    claim = ResearchClaim(
        id="claim-rate-limit",
        question_id="question-rate-limit",
        text=(
            "What is the current official rate limit for unauthenticated "
            "requests to the GitHub REST API?"
        ),
        kind="factual",
        priority="critical",
        state="searching",
        evidence_requirement=EvidenceRequirement(
            source_roles=("primary", "independent_secondary"),
            min_independent_sources=1,
            requires_primary_source=True,
            requires_successful_read=True,
            max_age_days=30,
            requires_dated_evidence=True,
        ),
    )
    gap = EvidenceGap(
        id="gap-rate-limit",
        claim_id=claim.id,
        gap_type="primary_missing",
        desired_source_role="primary",
        priority="critical",
        state="open",
    )
    batch = plan_gap_queries(gap, claim, reference_date="2026-08-27")
    calls = 0

    def search(_query: str, *, max_results: int) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        assert max_results == 5
        if calls == 1:
            return {
                "status": "ok",
                "providers_attempted": ["bing_rss"],
                "results": [
                    {
                        "title": "Current - dictionary definition",
                        "url": "https://dictionary.example/current",
                        "provider": "bing_rss",
                    }
                ],
            }
        if calls == 2:
            return {
                "status": "ok",
                "providers_attempted": ["searxng"],
                "results": [
                    {
                        "title": "REST API rate limits",
                        "url": "https://docs.github.com/rest/using-the-rest-api/rate-limits",
                        "provider": "searxng",
                    }
                ],
            }
        return {
            "status": "empty",
            "providers_attempted": ["searxng", "bing_rss"],
            "results": [],
        }

    pool = execute_candidate_pool_batch(batch, search_exact=search)
    assert calls == 4
    assert len(pool.candidates) == 2
    by_title = {item.title: item for item in pool.candidates}
    dictionary = by_title["Current - dictionary definition"]
    official = by_title["REST API rate limits"]
    clustering = cluster_candidate_sources(
        pool.candidates,
        profiles={
            dictionary.id: CandidateSourceProfile(
                dictionary.id,
                source_role="aggregator",
            ),
            official.id: CandidateSourceProfile(
                official.id,
                source_role="primary",
            ),
        },
    )
    assignments = {item.candidate_id: item for item in clustering.assignments}
    assessment_request = build_candidate_assessment_request(pool.candidates, claim=claim)
    semantic = parse_candidate_assessment_response(
        {
            "schema_version": CANDIDATE_ASSESSMENT_SCHEMA_VERSION,
            "assessments": [
                {
                    "candidate_id": dictionary.id,
                    "relevance": "off_target",
                    "relevance_confidence": 0.99,
                    "source_role": "aggregator",
                    "source_role_confidence": 0.9,
                    "expected_gain_signals": [],
                },
                {
                    "candidate_id": official.id,
                    "relevance": "answer_relevant",
                    "relevance_confidence": 0.86,
                    "source_role": "primary",
                    "source_role_confidence": 0.98,
                    "expected_gain_signals": [
                        "new_primary",
                        "claim_status_improvement",
                    ],
                },
            ],
        },
        request=assessment_request,
        cluster_assignments=assignments,
        freshness_scores={official.id: 0.9},
    )
    ranked = rank_candidate_pool(
        pool.candidates,
        claim=claim,
        assessments=semantic,
    )
    plan = plan_read_wave(
        ranked,
        claim=claim,
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
        ),
    )
    assert ranked[0].candidate.id == official.id
    assert ranked[-1].eligibility == "rejected"
    assert plan.selected_candidate_ids == (official.id,)
    assert plan.rejected_candidate_ids == (dictionary.id,)
