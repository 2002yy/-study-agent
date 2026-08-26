"""Versioned benchmark schema for shared research quality eval cases.

This module owns only the frozen fixture format for research quality
benchmarking: the gold contract, the frozen corpus document format, and
strict fail-closed validation. It owns no runner, no metrics, no live web
access, and no integration with WebLookupService. The actual trap fixtures
arrive in RQCE-P0-C2; this schema only freezes what they must look like.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, Mapping

from src.web.research.contracts import (
    ResearchClaimKind,
    ResearchClaimPriority,
)
from src.web.research.policy import SourceRole

RESEARCH_QUALITY_EVAL_SCHEMA_VERSION = "research-quality-eval-v1"

TrapCaseCategory = Literal[
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
]
EvalCaseMode = Literal["frozen", "live"]
ForbiddenClosureCondition = Literal[
    "primary_not_read",
    "independent_sources_below_minimum",
    "conflict_unresolved",
    "freshness_unmet",
    "snippet_only_evidence",
    "extraction_failed",
    "question_unverifiable",
]

_TRAP_CATEGORIES = {
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
}
_EVAL_CASE_MODES = {"frozen", "live"}
_FORBIDDEN_CLOSURE_CONDITIONS = {
    "primary_not_read",
    "independent_sources_below_minimum",
    "conflict_unresolved",
    "freshness_unmet",
    "snippet_only_evidence",
    "extraction_failed",
    "question_unverifiable",
}
# Frozen source roles mirror src/web/research/policy.py; tests assert sync.
_SOURCE_ROLES = {
    "primary",
    "authoritative_secondary",
    "independent_secondary",
    "community",
    "aggregator",
}
_CLAIM_KINDS = {"research_question", "hypothesis", "factual", "analytical"}
_CLAIM_PRIORITIES = {"critical", "major", "context"}


@dataclass(frozen=True)
class ExpectedClaim:
    surface: str
    kind: ResearchClaimKind
    priority: ResearchClaimPriority

    def to_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "kind": self.kind,
            "priority": self.priority,
        }


@dataclass(frozen=True)
class KnownConflict:
    description: str
    surfaces: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "description": self.description,
            "surfaces": list(self.surfaces),
        }


@dataclass(frozen=True)
class FreshnessRequirement:
    max_age_days: int | None = None
    requires_dated_evidence: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "max_age_days": self.max_age_days,
            "requires_dated_evidence": self.requires_dated_evidence,
        }


@dataclass(frozen=True)
class GoldContract:
    question: str
    critical_surfaces: tuple[str, ...]
    expected_claims: tuple[ExpectedClaim, ...]
    required_source_roles: tuple[SourceRole, ...]
    primary_exists: bool
    known_conflicts: tuple[KnownConflict, ...] = ()
    freshness_requirement: FreshnessRequirement | None = None
    forbidden_closure_conditions: tuple[ForbiddenClosureCondition, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "question": self.question,
            "critical_surfaces": list(self.critical_surfaces),
            "expected_claims": [claim.to_dict() for claim in self.expected_claims],
            "required_source_roles": list(self.required_source_roles),
            "primary_exists": self.primary_exists,
            "known_conflicts": [
                conflict.to_dict() for conflict in self.known_conflicts
            ],
            "freshness_requirement": (
                self.freshness_requirement.to_dict()
                if self.freshness_requirement is not None
                else None
            ),
            "forbidden_closure_conditions": list(
                self.forbidden_closure_conditions
            ),
        }


@dataclass(frozen=True)
class FrozenCorpusDocument:
    doc_id: str
    url: str
    title: str
    source_role: SourceRole
    cluster_id: str
    published_at: str | None
    content: str

    def to_dict(self) -> dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "url": self.url,
            "title": self.title,
            "source_role": self.source_role,
            "cluster_id": self.cluster_id,
            "published_at": self.published_at,
            "content": self.content,
        }


@dataclass(frozen=True)
class ResearchQualityEvalCase:
    id: str
    category: TrapCaseCategory
    mode: EvalCaseMode
    gold: GoldContract
    corpus: tuple[FrozenCorpusDocument, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "category": self.category,
            "mode": self.mode,
            "gold": self.gold.to_dict(),
            "corpus": [document.to_dict() for document in self.corpus],
        }


def build_research_quality_eval_case(
    *,
    id: str,
    category: TrapCaseCategory,
    mode: EvalCaseMode,
    gold: GoldContract,
    corpus: tuple[FrozenCorpusDocument, ...] = (),
) -> ResearchQualityEvalCase:
    """Validate and freeze one eval case definition."""
    case = ResearchQualityEvalCase(
        id=id,
        category=category,
        mode=mode,
        gold=gold,
        corpus=tuple(corpus),
    )
    return _validate_case(case)


def research_quality_eval_case_from_dict(raw: Any) -> ResearchQualityEvalCase:
    data = _mapping(raw, "research quality eval case")
    _only_keys(
        data,
        {"id", "category", "mode", "gold", "corpus"},
        "research quality eval case",
    )
    corpus_raw = data.get("corpus", [])
    if not isinstance(corpus_raw, list):
        raise ValueError("research quality eval case corpus must be a list")
    return build_research_quality_eval_case(
        id=_id(data.get("id"), "eval case id"),
        category=_enum(data.get("category"), _TRAP_CATEGORIES, "eval case category"),
        mode=_enum(data.get("mode"), _EVAL_CASE_MODES, "eval case mode"),
        gold=_parse_gold(data.get("gold")),
        corpus=tuple(_parse_corpus_document(item) for item in corpus_raw),
    )


def research_quality_eval_case_to_dict(case: ResearchQualityEvalCase) -> dict[str, object]:
    return case.to_dict()


def load_research_quality_eval_cases(
    path: str | Path,
) -> tuple[ResearchQualityEvalCase, ...]:
    """Load one versioned eval fixture file; fail closed on any drift."""
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"unreadable research quality eval fixture: {path}") from exc
    data = _mapping(raw, "research quality eval fixture")
    _only_keys(data, {"schema_version", "cases"}, "research quality eval fixture")
    version = data.get("schema_version")
    if version != RESEARCH_QUALITY_EVAL_SCHEMA_VERSION:
        raise ValueError("unsupported research quality eval schema_version")
    cases_raw = data.get("cases")
    if not isinstance(cases_raw, list):
        raise ValueError("research quality eval fixture requires a cases list")
    cases = tuple(
        research_quality_eval_case_from_dict(item) for item in cases_raw
    )
    seen: set[str] = set()
    for case in cases:
        if case.id in seen:
            raise ValueError(f"duplicate eval case id: {case.id}")
        seen.add(case.id)
    return cases


def _parse_gold(raw: Any) -> GoldContract:
    data = _mapping(raw, "eval gold contract")
    _only_keys(
        data,
        {
            "question",
            "critical_surfaces",
            "expected_claims",
            "required_source_roles",
            "primary_exists",
            "known_conflicts",
            "freshness_requirement",
            "forbidden_closure_conditions",
        },
        "eval gold contract",
    )
    conflicts_raw = data.get("known_conflicts", [])
    if not isinstance(conflicts_raw, list):
        raise ValueError("eval gold known_conflicts must be a list")
    claims_raw = data.get("expected_claims")
    if not isinstance(claims_raw, list):
        raise ValueError("eval gold expected_claims must be a list")
    freshness = data.get("freshness_requirement")
    return GoldContract(
        question=_text(data.get("question"), "eval gold question", 2000),
        critical_surfaces=_normalized_strings(
            data.get("critical_surfaces"),
            "eval gold critical_surfaces",
            max_items=12,
        ),
        expected_claims=tuple(
            _parse_expected_claim(item) for item in claims_raw
        ),
        required_source_roles=_source_role_tuple(
            data.get("required_source_roles"), "eval gold required_source_roles"
        ),
        primary_exists=_boolean(
            data.get("primary_exists"), "eval gold primary_exists"
        ),
        known_conflicts=tuple(
            _parse_known_conflict(item) for item in conflicts_raw
        ),
        freshness_requirement=(
            _parse_freshness_requirement(freshness)
            if freshness is not None
            else None
        ),
        forbidden_closure_conditions=_forbidden_condition_tuple(
            data.get("forbidden_closure_conditions", []),
            "eval gold forbidden_closure_conditions",
        ),
    )


def _parse_expected_claim(raw: Any) -> ExpectedClaim:
    data = _mapping(raw, "expected claim")
    _only_keys(data, {"surface", "kind", "priority"}, "expected claim")
    return ExpectedClaim(
        surface=_text(data.get("surface"), "expected claim surface", 500),
        kind=_enum(data.get("kind"), _CLAIM_KINDS, "expected claim kind"),
        priority=_enum(
            data.get("priority"), _CLAIM_PRIORITIES, "expected claim priority"
        ),
    )


def _parse_known_conflict(raw: Any) -> KnownConflict:
    data = _mapping(raw, "known conflict")
    _only_keys(data, {"description", "surfaces"}, "known conflict")
    return KnownConflict(
        description=_text(data.get("description"), "known conflict description", 1000),
        surfaces=_normalized_strings(
            data.get("surfaces", []),
            "known conflict surfaces",
            max_items=12,
        ),
    )


def _parse_freshness_requirement(raw: Any) -> FreshnessRequirement:
    data = _mapping(raw, "freshness requirement")
    _only_keys(
        data,
        {"max_age_days", "requires_dated_evidence"},
        "freshness requirement",
    )
    max_age_raw = data.get("max_age_days")
    if max_age_raw is not None:
        max_age_days = _integer(max_age_raw, "freshness max_age_days")
    else:
        max_age_days = None
    return FreshnessRequirement(
        max_age_days=max_age_days,
        requires_dated_evidence=_boolean(
            data.get("requires_dated_evidence", False),
            "freshness requires_dated_evidence",
        ),
    )


def _parse_corpus_document(raw: Any) -> FrozenCorpusDocument:
    data = _mapping(raw, "frozen corpus document")
    _only_keys(
        data,
        {
            "doc_id",
            "url",
            "title",
            "source_role",
            "cluster_id",
            "published_at",
            "content",
        },
        "frozen corpus document",
    )
    published_raw = data.get("published_at")
    if published_raw is not None:
        published_at = _publication_date(published_raw)
    else:
        published_at = None
    return FrozenCorpusDocument(
        doc_id=_id(data.get("doc_id"), "corpus doc id"),
        url=_text(data.get("url"), "corpus doc url", 2000),
        title=_text(data.get("title"), "corpus doc title", 500),
        source_role=_source_role(
            data.get("source_role"), "corpus doc source role"
        ),
        cluster_id=_id(data.get("cluster_id"), "corpus doc cluster id"),
        published_at=published_at,
        content=_text(data.get("content"), "corpus doc content", 100000),
    )


def _validate_case(case: ResearchQualityEvalCase) -> ResearchQualityEvalCase:
    _validate_gold(case.gold)
    seen: set[str] = set()
    for document in case.corpus:
        if document.doc_id in seen:
            raise ValueError(f"duplicate corpus doc id: {document.doc_id}")
        seen.add(document.doc_id)
    if case.mode == "live" and case.corpus:
        raise ValueError("live eval cases cannot define a frozen corpus")
    if case.mode == "frozen" and not case.corpus:
        raise ValueError("frozen eval cases require at least one corpus document")
    gold = case.gold
    if case.category == "no_primary_exists" and gold.primary_exists:
        raise ValueError("no_primary_exists case must declare primary_exists=false")
    if not gold.primary_exists and "primary" in gold.required_source_roles:
        raise ValueError(
            "required_source_roles cannot demand primary when primary_exists=false"
        )
    unverifiable = "question_unverifiable" in gold.forbidden_closure_conditions
    if (case.category == "unanswerable_unverifiable") != unverifiable:
        raise ValueError(
            "question_unverifiable is reserved for unanswerable_unverifiable cases"
        )
    if case.category == "conflicting_primary" and not gold.known_conflicts:
        raise ValueError(
            "conflicting_primary case must declare at least one known conflict"
        )
    if case.category == "old_primary" and gold.freshness_requirement is None:
        raise ValueError("old_primary case must declare freshness_requirement")
    return case


def _validate_gold(gold: GoldContract) -> None:
    if not gold.critical_surfaces:
        raise ValueError("eval gold critical_surfaces cannot be empty")
    if not gold.expected_claims:
        raise ValueError("eval gold expected_claims cannot be empty")
    if not gold.required_source_roles:
        raise ValueError("eval gold required_source_roles cannot be empty")
    for role in gold.required_source_roles:
        if role not in _SOURCE_ROLES:
            raise ValueError(f"unknown eval gold source role: {role}")
    surfaces = [claim.surface for claim in gold.expected_claims]
    if len(set(surfaces)) != len(surfaces):
        raise ValueError("duplicate expected claim surface")
    freshness = gold.freshness_requirement
    if freshness is not None:
        if freshness.max_age_days is None and not freshness.requires_dated_evidence:
            raise ValueError(
                "freshness_requirement must set max_age_days or requires_dated_evidence"
            )
        if freshness.max_age_days is not None and freshness.max_age_days < 1:
            raise ValueError("freshness max_age_days must be at least 1")


def _mapping(raw: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return raw


def _only_keys(
    raw: Mapping[str, Any], allowed: set[str], label: str
) -> None:
    for key in raw:
        if key not in allowed:
            raise ValueError(f"unknown {label} field: {key}")


def _text(raw: Any, label: str, max_length: int) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label} must be non-empty text")
    if len(raw) > max_length:
        raise ValueError(f"{label} exceeds {max_length} characters")
    return raw


def _id(raw: Any, label: str) -> str:
    value = _text(raw, label, 200)
    if any(character.isspace() for character in value):
        raise ValueError(f"{label} cannot contain whitespace")
    return value


def _enum(raw: Any, allowed: set[str], label: str) -> Any:
    value = _text(raw, label, 100)
    if value not in allowed:
        raise ValueError(f"invalid {label}: {value}")
    return value


def _integer(raw: Any, label: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{label} must be an integer")
    return raw


def _boolean(raw: Any, label: str) -> bool:
    if not isinstance(raw, bool):
        raise ValueError(f"{label} must be boolean")
    return raw


def _source_role(raw: Any, label: str) -> Any:
    value = _text(raw, label, 100)
    if value not in _SOURCE_ROLES:
        raise ValueError(f"invalid {label}: {value}")
    return value


def _source_role_tuple(raw: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be a list")
    values = tuple(_source_role(value, label) for value in raw)
    if not values:
        raise ValueError(f"{label} cannot be empty")
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")
    return tuple(sorted(values))


def _forbidden_condition_tuple(raw: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be a list")
    values = tuple(
        _enum(value, _FORBIDDEN_CLOSURE_CONDITIONS, label) for value in raw
    )
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")
    return tuple(sorted(values))


def _normalized_strings(
    raw: Any,
    label: str,
    *,
    max_items: int,
) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be a list")
    values = tuple(_text(value, label, 500) for value in raw)
    if len(values) > max_items:
        raise ValueError(f"{label} exceeds {max_items} items")
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")
    return tuple(sorted(values))


def _publication_date(raw: Any) -> str:
    value = _text(raw, "corpus doc published_at", 100)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("corpus doc published_at must be an ISO-8601 date") from exc
    return value


__all__ = [
    "RESEARCH_QUALITY_EVAL_SCHEMA_VERSION",
    "EvalCaseMode",
    "ExpectedClaim",
    "ForbiddenClosureCondition",
    "FreshnessRequirement",
    "FrozenCorpusDocument",
    "GoldContract",
    "KnownConflict",
    "ResearchQualityEvalCase",
    "TrapCaseCategory",
    "build_research_quality_eval_case",
    "load_research_quality_eval_cases",
    "research_quality_eval_case_from_dict",
    "research_quality_eval_case_to_dict",
]
