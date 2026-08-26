from __future__ import annotations

import pytest

from src.web.research.policy import evidence_policy_for_claim


def test_official_statement_requires_read_primary_evidence() -> None:
    policy = evidence_policy_for_claim(
        kind="factual",
        priority="critical",
        profile="official_statement",
    )

    assert policy.eligible_source_roles == ("primary",)
    assert policy.requirement.requires_primary_source is True
    assert policy.requirement.requires_successful_read is True
    assert policy.requirement.min_independent_sources == 1
    assert "aggregator" in policy.lead_only_source_roles


def test_community_sentiment_does_not_require_official_primary() -> None:
    policy = evidence_policy_for_claim(
        kind="analytical",
        priority="critical",
        profile="community_sentiment",
    )

    assert policy.eligible_source_roles == ("community", "independent_secondary")
    assert policy.requirement.requires_primary_source is False
    assert policy.requirement.min_independent_sources == 2
    assert "primary" in policy.lead_only_source_roles
    assert "aggregator" in policy.lead_only_source_roles


@pytest.mark.parametrize(
    "profile",
    ["current_fact", "quantitative_claim", "causal_analysis"],
)
def test_formal_fact_and_analysis_profiles_exclude_community_and_aggregator(
    profile: str,
) -> None:
    kind = "analytical" if profile in {"quantitative_claim", "causal_analysis"} else "factual"
    policy = evidence_policy_for_claim(
        kind=kind,  # type: ignore[arg-type]
        priority="major",
        profile=profile,  # type: ignore[arg-type]
    )

    assert "community" not in policy.eligible_source_roles
    assert "aggregator" not in policy.eligible_source_roles
    assert policy.requirement.requires_successful_read is True


def test_critical_policy_requires_more_independent_sources_than_major() -> None:
    critical = evidence_policy_for_claim(
        kind="factual",
        priority="critical",
        profile="current_fact",
    )
    major = evidence_policy_for_claim(
        kind="factual",
        priority="major",
        profile="current_fact",
    )

    assert critical.requirement.min_independent_sources == 2
    assert major.requirement.min_independent_sources == 1


def test_hypothesis_cannot_close_as_evidence_gated_fact() -> None:
    policy = evidence_policy_for_claim(
        kind="hypothesis",
        priority="major",
        profile="exploratory_hypothesis",
    )

    assert policy.closure_semantics == "hypothesis_only"
    assert "aggregator" in policy.lead_only_source_roles


@pytest.mark.parametrize(
    ("kind", "profile"),
    [
        ("analytical", "official_statement"),
        ("factual", "causal_analysis"),
        ("factual", "exploratory_hypothesis"),
    ],
)
def test_incompatible_profile_and_claim_kind_fail_closed(kind: str, profile: str) -> None:
    with pytest.raises(ValueError, match="incompatible"):
        evidence_policy_for_claim(
            kind=kind,  # type: ignore[arg-type]
            priority="critical",
            profile=profile,  # type: ignore[arg-type]
        )


def test_policy_is_deterministic_and_json_safe() -> None:
    first = evidence_policy_for_claim(
        kind="factual",
        priority="critical",
        profile="quantitative_claim",
    )
    second = evidence_policy_for_claim(
        kind="factual",
        priority="critical",
        profile="quantitative_claim",
    )

    assert first == second
    assert first.to_dict() == second.to_dict()
    assert set(first.to_dict()) == {
        "profile",
        "requirement",
        "eligible_source_roles",
        "lead_only_source_roles",
        "closure_semantics",
    }
