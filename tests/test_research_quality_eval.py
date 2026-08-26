from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, cast

import pytest

from src.evals.research_quality import (
    RESEARCH_QUALITY_EVAL_SCHEMA_VERSION,
    FrozenCorpusDocument,
    GoldContract,
    build_research_quality_eval_case,
    load_research_quality_eval_cases,
    research_quality_eval_case_from_dict,
    research_quality_eval_case_to_dict,
)


def _corpus_document_dict() -> dict[str, Any]:
    return {
        "doc_id": "doc-official",
        "url": "https://example.test/official",
        "title": "Official statement",
        "source_role": "primary",
        "cluster_id": "cluster-official",
        "published_at": "2026-01-15",
        "content": "The official statement confirms the release date.",
    }


def _frozen_case_dict() -> dict[str, Any]:
    return {
        "id": "trap-01",
        "category": "secondary_only",
        "mode": "frozen",
        "gold": {
            "question": "When was the feature released?",
            "critical_surfaces": ["release date"],
            "expected_claims": [
                {
                    "surface": "The feature was released on a specific date.",
                    "kind": "factual",
                    "priority": "critical",
                }
            ],
            "required_source_roles": ["primary"],
            "primary_exists": True,
            "known_conflicts": [],
            "freshness_requirement": None,
            "forbidden_closure_conditions": ["primary_not_read"],
        },
        "corpus": [_corpus_document_dict()],
    }


def _live_case_dict() -> dict[str, Any]:
    return {
        "id": "trap-live-01",
        "category": "simple_factual",
        "mode": "live",
        "gold": {
            "question": "What is the current stable version?",
            "critical_surfaces": ["stable version"],
            "expected_claims": [
                {
                    "surface": "The current stable version is identifiable.",
                    "kind": "factual",
                    "priority": "critical",
                }
            ],
            "required_source_roles": ["primary", "authoritative_secondary"],
            "primary_exists": True,
            "forbidden_closure_conditions": ["snippet_only_evidence"],
        },
    }


def _build_from_dict(raw: dict[str, Any]):
    return research_quality_eval_case_from_dict(deepcopy(raw))


def test_minimal_frozen_case_round_trip() -> None:
    case = _build_from_dict(_frozen_case_dict())
    assert case.id == "trap-01"
    assert case.category == "secondary_only"
    assert case.mode == "frozen"
    assert case.gold.primary_exists is True
    assert case.gold.required_source_roles == ("primary",)
    assert case.gold.forbidden_closure_conditions == ("primary_not_read",)
    assert len(case.corpus) == 1
    restored = research_quality_eval_case_from_dict(
        json.loads(json.dumps(research_quality_eval_case_to_dict(case)))
    )
    assert restored == case


def test_live_case_without_corpus_round_trip() -> None:
    case = _build_from_dict(_live_case_dict())
    assert case.mode == "live"
    assert case.corpus == ()
    restored = research_quality_eval_case_from_dict(
        research_quality_eval_case_to_dict(case)
    )
    assert restored == case


def test_schema_version_mismatch_rejected(tmp_path) -> None:
    fixture = {
        "schema_version": "research-quality-eval-v0",
        "cases": [_frozen_case_dict()],
    }
    path = tmp_path / "wrong_version.json"
    path.write_text(json.dumps(fixture), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_research_quality_eval_cases(path)
    missing = {"cases": [_frozen_case_dict()]}
    path2 = tmp_path / "missing_version.json"
    path2.write_text(json.dumps(missing), encoding="utf-8")
    with pytest.raises(ValueError, match="schema_version"):
        load_research_quality_eval_cases(path2)


def test_unknown_fields_rejected() -> None:
    for mutation in (
        {"extra": 1},
        {"gold_extra": ("gold", "secret")},
        {"corpus_extra": ("corpus", 0, "raw_html")},
        {"claim_extra": ("gold", "expected_claims", 0, "provenance")},
    ):
        raw = deepcopy(_frozen_case_dict())
        if "extra" in mutation:
            raw["extra"] = mutation["extra"]
        elif "gold_extra" in mutation:
            raw["gold"]["secret"] = "token"
        elif "corpus_extra" in mutation:
            raw["corpus"][0]["raw_html"] = "<html>"
        else:
            raw["gold"]["expected_claims"][0]["provenance"] = "opaque"
        with pytest.raises(ValueError, match="unknown .* field"):
            _build_from_dict(raw)


def test_invalid_enums_rejected() -> None:
    mutations = (
        (("category",), "synthetic_only"),
        (("mode",), "offline"),
        (("gold", "forbidden_closure_conditions"), ["made_up_condition"]),
        (("gold", "required_source_roles"), ["blog"]),
        (("gold", "expected_claims", 0, "kind"), "speculative"),
        (("gold", "expected_claims", 0, "priority"), "urgent"),
        (("corpus", 0, "source_role"), "unknown_role"),
    )
    for path, value in mutations:
        raw = deepcopy(_frozen_case_dict())
        target: Any = raw
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value
        with pytest.raises(ValueError):
            _build_from_dict(raw)


def test_empty_required_collections_rejected() -> None:
    for field in ("critical_surfaces", "expected_claims", "required_source_roles"):
        raw = deepcopy(_frozen_case_dict())
        raw["gold"][field] = []
        with pytest.raises(ValueError, match=f"{field} cannot be empty"):
            _build_from_dict(raw)


def test_freshness_rules() -> None:
    raw = deepcopy(_frozen_case_dict())
    raw["gold"]["freshness_requirement"] = {
        "max_age_days": None,
        "requires_dated_evidence": False,
    }
    with pytest.raises(ValueError, match="freshness_requirement must set"):
        _build_from_dict(raw)
    raw["gold"]["freshness_requirement"] = {"max_age_days": 0}
    with pytest.raises(ValueError, match="max_age_days must be at least 1"):
        _build_from_dict(raw)
    raw["gold"]["freshness_requirement"] = {"max_age_days": 30}
    assert _build_from_dict(raw).gold.freshness_requirement is not None
    corpus = deepcopy(_frozen_case_dict())
    corpus["corpus"][0]["published_at"] = "2026/01/15"
    with pytest.raises(ValueError, match="ISO-8601"):
        _build_from_dict(corpus)


def test_corpus_mode_rules() -> None:
    live = deepcopy(_live_case_dict())
    live["corpus"] = [_corpus_document_dict()]
    with pytest.raises(ValueError, match="live eval cases cannot"):
        _build_from_dict(live)
    frozen = deepcopy(_frozen_case_dict())
    frozen["corpus"] = []
    with pytest.raises(ValueError, match="frozen eval cases require"):
        _build_from_dict(frozen)
    duplicate = deepcopy(_frozen_case_dict())
    duplicate["corpus"].append(_corpus_document_dict())
    with pytest.raises(ValueError, match="duplicate corpus doc id"):
        _build_from_dict(duplicate)


def test_category_cross_rules() -> None:
    no_primary = deepcopy(_frozen_case_dict())
    no_primary["category"] = "no_primary_exists"
    no_primary["gold"]["primary_exists"] = True
    with pytest.raises(ValueError, match="no_primary_exists"):
        _build_from_dict(no_primary)

    role_conflict = deepcopy(_frozen_case_dict())
    role_conflict["gold"]["primary_exists"] = False
    with pytest.raises(ValueError, match="cannot demand primary"):
        _build_from_dict(role_conflict)

    unanswerable = deepcopy(_frozen_case_dict())
    unanswerable["category"] = "unanswerable_unverifiable"
    with pytest.raises(ValueError, match="question_unverifiable"):
        _build_from_dict(unanswerable)

    reserved = deepcopy(_frozen_case_dict())
    reserved["gold"]["forbidden_closure_conditions"] = ["question_unverifiable"]
    with pytest.raises(ValueError, match="question_unverifiable"):
        _build_from_dict(reserved)

    conflicting = deepcopy(_frozen_case_dict())
    conflicting["category"] = "conflicting_primary"
    with pytest.raises(ValueError, match="conflicting_primary"):
        _build_from_dict(conflicting)

    old_primary = deepcopy(_frozen_case_dict())
    old_primary["category"] = "old_primary"
    with pytest.raises(ValueError, match="old_primary"):
        _build_from_dict(old_primary)


def test_loader_envelope_rules(tmp_path) -> None:
    bare = [_frozen_case_dict()]
    path = tmp_path / "bare.json"
    path.write_text(json.dumps(bare), encoding="utf-8")
    with pytest.raises(ValueError, match="JSON object"):
        load_research_quality_eval_cases(path)

    missing_cases = {"schema_version": RESEARCH_QUALITY_EVAL_SCHEMA_VERSION}
    path2 = tmp_path / "missing_cases.json"
    path2.write_text(json.dumps(missing_cases), encoding="utf-8")
    with pytest.raises(ValueError, match="cases list"):
        load_research_quality_eval_cases(path2)

    duplicate_ids = {
        "schema_version": RESEARCH_QUALITY_EVAL_SCHEMA_VERSION,
        "cases": [_frozen_case_dict(), _frozen_case_dict()],
    }
    path3 = tmp_path / "duplicate.json"
    path3.write_text(json.dumps(duplicate_ids), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate eval case id"):
        load_research_quality_eval_cases(path3)

    path4 = tmp_path / "unreadable.json"
    path4.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError, match="unreadable"):
        load_research_quality_eval_cases(path4)

    valid = {
        "schema_version": RESEARCH_QUALITY_EVAL_SCHEMA_VERSION,
        "cases": [_frozen_case_dict(), _live_case_dict()],
    }
    path5 = tmp_path / "valid.json"
    path5.write_text(json.dumps(valid), encoding="utf-8")
    loaded = load_research_quality_eval_cases(path5)
    assert [case.id for case in loaded] == ["trap-01", "trap-live-01"]


def test_deterministic_parse() -> None:
    raw = _frozen_case_dict()
    first = _build_from_dict(raw)
    second = _build_from_dict(raw)
    assert first == second
    assert research_quality_eval_case_to_dict(first) == (
        research_quality_eval_case_to_dict(second)
    )


def test_to_dict_key_sets_exact() -> None:
    case = _build_from_dict(_frozen_case_dict())
    payload = research_quality_eval_case_to_dict(case)
    assert set(payload) == {"id", "category", "mode", "gold", "corpus"}
    gold_payload = cast(dict[str, Any], payload["gold"])
    assert set(gold_payload) == {
        "question",
        "critical_surfaces",
        "expected_claims",
        "required_source_roles",
        "primary_exists",
        "known_conflicts",
        "freshness_requirement",
        "forbidden_closure_conditions",
    }
    corpus_payload = cast(list[dict[str, Any]], payload["corpus"])
    assert set(corpus_payload[0]) == {
        "doc_id",
        "url",
        "title",
        "source_role",
        "cluster_id",
        "published_at",
        "content",
    }


def test_duplicate_expected_claim_surface_rejected() -> None:
    raw = deepcopy(_frozen_case_dict())
    claim = deepcopy(raw["gold"]["expected_claims"][0])
    claim["priority"] = "major"
    raw["gold"]["expected_claims"].append(claim)
    with pytest.raises(ValueError, match="duplicate expected claim surface"):
        _build_from_dict(raw)


def test_source_roles_sync_with_frozen_engine() -> None:
    from src.evals.research_quality import _SOURCE_ROLES as eval_roles
    from src.web.research.contracts import _SOURCE_ROLES as contract_roles
    from src.web.research.policy import _ALL_SOURCE_ROLES as policy_roles

    assert eval_roles == contract_roles
    assert eval_roles == set(policy_roles)


def test_direct_builder_validates_like_parser() -> None:
    gold = GoldContract(
        question="When was the feature released?",
        critical_surfaces=("release date",),
        expected_claims=(),
        required_source_roles=("primary",),
        primary_exists=True,
    )
    with pytest.raises(ValueError, match="expected_claims"):
        build_research_quality_eval_case(
            id="trap-direct",
            category="secondary_only",
            mode="frozen",
            gold=gold,
            corpus=(
                FrozenCorpusDocument(
                    doc_id="doc-official",
                    url="https://example.test/official",
                    title="Official statement",
                    source_role="primary",
                    cluster_id="cluster-official",
                    published_at="2026-01-15",
                    content="The official statement confirms the release date.",
                ),
            ),
        )
