from __future__ import annotations

import json
from pathlib import Path

from src.evals.research_quality import (
    ResearchQualityEvalCase,
    load_research_quality_eval_cases,
    research_quality_eval_case_from_dict,
    research_quality_eval_case_to_dict,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "research_quality"
FROZEN_FILE = FIXTURES_DIR / "frozen_trap_cases.json"
LIVE_FILE = FIXTURES_DIR / "live_trap_cases.json"

EXPECTED_CATEGORIES = (
    "secondary_only",
    "duplicate_source",
    "old_primary",
    "conflicting_primary",
    "no_primary_exists",
    "community_opinion",
    "numerical_original_source",
    "causal_competing_explanations",
    "simple_factual",
    "unanswerable_unverifiable",
)


def _load_frozen() -> tuple[ResearchQualityEvalCase, ...]:
    return load_research_quality_eval_cases(FROZEN_FILE)


def _load_live() -> tuple[ResearchQualityEvalCase, ...]:
    return load_research_quality_eval_cases(LIVE_FILE)


def _by_category(cases: tuple[ResearchQualityEvalCase, ...]) -> dict[str, list[ResearchQualityEvalCase]]:
    grouped: dict[str, list[ResearchQualityEvalCase]] = {}
    for case in cases:
        grouped.setdefault(case.category, []).append(case)
    return grouped


def test_twenty_unique_cases_across_all_categories() -> None:
    frozen = _load_frozen()
    live = _load_live()
    all_cases = frozen + live
    assert len(all_cases) == 20
    ids = [case.id for case in all_cases]
    assert len(set(ids)) == 20
    grouped = _by_category(all_cases)
    assert set(grouped) == set(EXPECTED_CATEGORIES)
    for category in EXPECTED_CATEGORIES:
        assert len(grouped[category]) == 2, category


def test_each_category_has_one_frozen_and_one_live() -> None:
    frozen = _by_category(_load_frozen())
    live = _by_category(_load_live())
    assert set(frozen) == set(EXPECTED_CATEGORIES)
    assert set(live) == set(EXPECTED_CATEGORIES)
    for category in EXPECTED_CATEGORIES:
        assert frozen[category][0].mode == "frozen", category
        assert live[category][0].mode == "live", category
        assert frozen[category][0].id.startswith("trap-"), category
        assert frozen[category][0].id.endswith("-frozen"), category
        assert live[category][0].id.startswith("trap-"), category
        assert live[category][0].id.endswith("-live"), category


def test_frozen_cases_carry_corpus_and_live_cases_do_not() -> None:
    for case in _load_frozen():
        assert case.corpus, case.id
        for document in case.corpus:
            assert document.content.strip(), (case.id, document.doc_id)
    for case in _load_live():
        assert case.corpus == (), case.id


def test_every_case_has_critical_claim() -> None:
    for case in _load_frozen() + _load_live():
        assert any(
            claim.priority == "critical" for claim in case.gold.expected_claims
        ), case.id


def test_secondary_only_trap_requires_primary_read() -> None:
    case = _by_category(_load_frozen())["secondary_only"][0]
    assert "primary" in case.gold.required_source_roles
    assert case.gold.primary_exists
    assert "primary_not_read" in case.gold.forbidden_closure_conditions
    roles = {document.source_role for document in case.corpus}
    assert "primary" in roles
    assert "aggregator" in roles


def test_duplicate_source_trap_has_syndicated_cluster() -> None:
    case = _by_category(_load_frozen())["duplicate_source"][0]
    clusters = [document.cluster_id for document in case.corpus]
    duplicated = {cluster for cluster in clusters if clusters.count(cluster) > 1}
    assert duplicated, "duplicate_source corpus must contain a syndicated cluster"
    assert "independent_sources_below_minimum" in case.gold.forbidden_closure_conditions


def test_old_primary_trap_declares_freshness() -> None:
    case = _by_category(_load_frozen())["old_primary"][0]
    assert case.gold.freshness_requirement is not None
    assert case.gold.freshness_requirement.max_age_days is not None
    assert "freshness_unmet" in case.gold.forbidden_closure_conditions
    published = [document.published_at for document in case.corpus]
    assert "2021-06-01" in published, "old primary doc must be stale by design"


def test_conflicting_primary_trap_declares_known_conflict() -> None:
    case = _by_category(_load_frozen())["conflicting_primary"][0]
    assert case.gold.known_conflicts
    assert "conflict_unresolved" in case.gold.forbidden_closure_conditions
    primaries = [
        document for document in case.corpus if document.source_role == "primary"
    ]
    assert len({document.cluster_id for document in primaries}) >= 2


def test_no_primary_exists_trap_forbids_primary_demand() -> None:
    case = _by_category(_load_frozen())["no_primary_exists"][0]
    assert not case.gold.primary_exists
    assert "primary" not in case.gold.required_source_roles
    assert not any(
        document.source_role == "primary" for document in case.corpus
    )


def test_community_opinion_trap_uses_sentiment_roles() -> None:
    case = _by_category(_load_frozen())["community_opinion"][0]
    assert "community" in case.gold.required_source_roles
    assert not case.gold.primary_exists
    assert not any(
        document.source_role == "primary" for document in case.corpus
    )


def test_numerical_original_trap_demands_primary_only() -> None:
    case = _by_category(_load_frozen())["numerical_original_source"][0]
    assert case.gold.required_source_roles == ("primary",)
    assert "primary_not_read" in case.gold.forbidden_closure_conditions
    assert any(
        document.source_role == "aggregator" for document in case.corpus
    ), "aggregator lead must exist to represent the rounding trap"


def test_causal_competing_trap_lists_two_claims() -> None:
    case = _by_category(_load_frozen())["causal_competing_explanations"][0]
    assert len(case.gold.expected_claims) >= 2
    assert case.gold.known_conflicts


def test_simple_factual_trap_stays_minimal_control() -> None:
    case = _by_category(_load_frozen())["simple_factual"][0]
    assert case.gold.forbidden_closure_conditions == ("snippet_only_evidence",)
    assert case.gold.freshness_requirement is None
    assert not case.gold.known_conflicts


def test_unanswerable_trap_binds_unverifiable_condition() -> None:
    frozen = _by_category(_load_frozen())["unanswerable_unverifiable"][0]
    assert "question_unverifiable" in frozen.gold.forbidden_closure_conditions
    for case in _load_frozen() + _load_live():
        if case.category != "unanswerable_unverifiable":
            assert (
                "question_unverifiable" not in case.gold.forbidden_closure_conditions
            ), case.id


def test_all_cases_round_trip_json_safe() -> None:
    for case in _load_frozen() + _load_live():
        payload = json.loads(json.dumps(research_quality_eval_case_to_dict(case)))
        assert research_quality_eval_case_from_dict(payload) == case
