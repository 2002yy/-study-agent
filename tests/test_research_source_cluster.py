from __future__ import annotations

import pytest

from src.web.research.candidate_pool import CandidatePoolItem
from src.web.research.gap_planner import GapSearchIntent
from src.web.research.source_cluster import (
    CandidateSourceProfile,
    cluster_candidate_sources,
)


def _candidate(candidate_id: str, url: str, rank: int) -> CandidatePoolItem:
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


def test_shared_origin_clusters_cross_domain_reposts() -> None:
    candidates = (
        _candidate("a", "https://news-a.example/story", 1),
        _candidate("b", "https://news-b.example/repost", 2),
    )
    origin = "https://official.example/announcement?utm_source=repost"
    result = cluster_candidate_sources(
        candidates,
        profiles={
            "a": CandidateSourceProfile("a", "independent_secondary", origin_url=origin),
            "b": CandidateSourceProfile("b", "aggregator", origin_url=origin),
        },
    )

    assert len(result.clusters) == 1
    assert result.clusters[0].candidate_ids == ("a", "b")
    assert result.clusters[0].basis == "origin_url"
    assert result.clusters[0].independence_key == "origin:https://official.example/announcement"


def test_publisher_domain_is_conservative_fallback_not_independence_proof() -> None:
    candidates = (
        _candidate("a", "https://docs.example/one", 1),
        _candidate("b", "https://docs.example/two", 2),
        _candidate("c", "https://other.example/three", 3),
    )
    result = cluster_candidate_sources(candidates)
    assert len(result.clusters) == 2
    assert result.clusters[0].candidate_ids == ("a", "b")
    assert result.clusters[0].basis == "publisher"


def test_unknown_profile_candidate_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown candidates"):
        cluster_candidate_sources(
            (_candidate("a", "https://example.test/a", 1),),
            profiles={"other": CandidateSourceProfile("other")},
        )
