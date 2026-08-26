"""Offline shadow runner for research quality eval cases (RQCE-P0-C3).

This module owns only the deterministic, offline evaluation harness for
frozen research quality fixtures: a recorded legacy run transcript, the
baseline metric computation against the gold contract, and an in-process
shadow evaluation built from :mod:`src.web.research` contracts and gates.

It performs no live web access, no WebLookupService integration, no runtime
observer activation, and no legacy-output-to-ClaimState projection in
production code paths. The ResearchState built here is an eval-harness
construction from fixture inputs, not a projection of a real user run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Iterable, Literal, Mapping

from src.domain.evidence import ClaimEvidenceLinkV1
from src.evals.research_quality import (
    FrozenCorpusDocument,
    ResearchQualityEvalCase,
)
from src.web.research.contracts import (
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
from src.web.research.stop_gate import (
    ShadowStopDecision,
    evaluate_shadow_stop,
)

RESEARCH_QUALITY_RUN_SCHEMA_VERSION = "research-quality-run-v1"

RunReadOutcome = Literal["success", "failed"]
ReadState = Literal["read_ok", "read_failed", "extraction_failed", "snippet_only"]

_RUN_READ_OUTCOMES = {"success", "failed"}
_LINK_STRENGTH = 0.9
_BOUNDED_MAX_CANDIDATES = 20
_BOUNDED_MAX_READS = 8
_BOUNDED_SOFT_TIMEOUT = 45.0
_BOUNDED_HARD_TIMEOUT = 60.0


@dataclass(frozen=True)
class RunReadRecord:
    doc_id: str
    outcome: RunReadOutcome
    extraction_eligible: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "doc_id": self.doc_id,
            "outcome": self.outcome,
            "extraction_eligible": self.extraction_eligible,
        }


@dataclass(frozen=True)
class ResearchRunTranscript:
    case_id: str
    reference_date: str
    queries: tuple[str, ...] = ()
    searches: int = 0
    reads: tuple[RunReadRecord, ...] = ()
    cited_doc_ids: tuple[str, ...] = ()
    addressed_claim_surfaces: tuple[str, ...] = ()
    llm_calls: int = 0
    elapsed_seconds: float = 0.0
    closed: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "reference_date": self.reference_date,
            "queries": list(self.queries),
            "searches": self.searches,
            "reads": [record.to_dict() for record in self.reads],
            "cited_doc_ids": list(self.cited_doc_ids),
            "addressed_claim_surfaces": list(self.addressed_claim_surfaces),
            "llm_calls": self.llm_calls,
            "elapsed_seconds": self.elapsed_seconds,
            "closed": self.closed,
        }


@dataclass(frozen=True)
class RunEvaluation:
    case_id: str
    category: str
    mode: str
    closed: bool
    false_closure: bool
    violated_closure_conditions: tuple[str, ...]
    primary_retrieval: bool
    useful_read_ratio: float
    independent_cluster_count: int
    critical_claim_coverage: float
    citation_entailment: float | None
    search_count: int
    query_count: int
    read_count: int
    llm_calls: int
    elapsed_seconds: float
    failure_reasons: tuple[str, ...]
    shadow_status: str
    shadow_would_pass: bool
    shadow_would_block: bool
    legacy_would_stop_but_shadow_blocked: bool
    shadow_reasons: tuple[str, ...]
    open_critical_claims: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "category": self.category,
            "mode": self.mode,
            "closed": self.closed,
            "false_closure": self.false_closure,
            "violated_closure_conditions": list(
                self.violated_closure_conditions
            ),
            "primary_retrieval": self.primary_retrieval,
            "useful_read_ratio": self.useful_read_ratio,
            "independent_cluster_count": self.independent_cluster_count,
            "critical_claim_coverage": self.critical_claim_coverage,
            "citation_entailment": self.citation_entailment,
            "search_count": self.search_count,
            "query_count": self.query_count,
            "read_count": self.read_count,
            "llm_calls": self.llm_calls,
            "elapsed_seconds": self.elapsed_seconds,
            "failure_reasons": list(self.failure_reasons),
            "shadow_status": self.shadow_status,
            "shadow_would_pass": self.shadow_would_pass,
            "shadow_would_block": self.shadow_would_block,
            "legacy_would_stop_but_shadow_blocked": (
                self.legacy_would_stop_but_shadow_blocked
            ),
            "shadow_reasons": list(self.shadow_reasons),
            "open_critical_claims": list(self.open_critical_claims),
        }


@dataclass(frozen=True)
class ShadowRunSummary:
    total_cases: int
    closed_runs: int
    false_closures: int
    shadow_blocked_runs: int
    caught_false_closures: int
    missed_false_closures: int
    overblocked_correct_closures: int
    primary_retrieval_rate: float
    mean_useful_read_ratio: float
    mean_critical_claim_coverage: float
    per_category: tuple[tuple[str, int, int, int], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "total_cases": self.total_cases,
            "closed_runs": self.closed_runs,
            "false_closures": self.false_closures,
            "shadow_blocked_runs": self.shadow_blocked_runs,
            "caught_false_closures": self.caught_false_closures,
            "missed_false_closures": self.missed_false_closures,
            "overblocked_correct_closures": self.overblocked_correct_closures,
            "primary_retrieval_rate": self.primary_retrieval_rate,
            "mean_useful_read_ratio": self.mean_useful_read_ratio,
            "mean_critical_claim_coverage": self.mean_critical_claim_coverage,
            "per_category": [
                {"category": category, "total": total, "false_closures": false, "caught": caught}
                for category, total, false, caught in self.per_category
            ],
        }


def research_run_transcript_from_dict(raw: Any) -> ResearchRunTranscript:
    data = _mapping(raw, "research run transcript")
    _only_keys(
        data,
        {
            "case_id",
            "reference_date",
            "queries",
            "searches",
            "reads",
            "cited_doc_ids",
            "addressed_claim_surfaces",
            "llm_calls",
            "elapsed_seconds",
            "closed",
        },
        "research run transcript",
    )
    reads_raw = data.get("reads", [])
    if not isinstance(reads_raw, list):
        raise ValueError("research run transcript reads must be a list")
    records = tuple(_parse_read_record(item) for item in reads_raw)
    seen: set[str] = set()
    for record in records:
        if record.doc_id in seen:
            raise ValueError(f"duplicate transcript read doc id: {record.doc_id}")
        seen.add(record.doc_id)
    elapsed = _number(data.get("elapsed_seconds", 0.0), "transcript elapsed_seconds")
    if elapsed < 0:
        raise ValueError("transcript elapsed_seconds cannot be negative")
    return ResearchRunTranscript(
        case_id=_text(data.get("case_id"), "transcript case_id", 200),
        reference_date=_publication_date(data.get("reference_date")),
        queries=_string_tuple(data.get("queries", []), "transcript queries"),
        searches=_non_negative_int(data.get("searches", 0), "transcript searches"),
        reads=records,
        cited_doc_ids=_string_tuple(
            data.get("cited_doc_ids", []), "transcript cited_doc_ids"
        ),
        addressed_claim_surfaces=_string_tuple(
            data.get("addressed_claim_surfaces", []),
            "transcript addressed_claim_surfaces",
        ),
        llm_calls=_non_negative_int(data.get("llm_calls", 0), "transcript llm_calls"),
        elapsed_seconds=elapsed,
        closed=_boolean(data.get("closed", False), "transcript closed"),
    )


def research_run_transcript_to_dict(
    transcript: ResearchRunTranscript,
) -> dict[str, object]:
    return transcript.to_dict()


def evaluate_research_run(
    case: ResearchQualityEvalCase,
    transcript: ResearchRunTranscript,
) -> RunEvaluation:
    """Evaluate one recorded legacy run against its case gold and shadow gates."""

    if transcript.case_id != case.id:
        raise ValueError(
            f"transcript case_id {transcript.case_id} does not match {case.id}"
        )
    corpus_by_id = {document.doc_id: document for document in case.corpus}
    for record in transcript.reads:
        if record.doc_id not in corpus_by_id:
            raise ValueError(f"transcript references unknown doc id: {record.doc_id}")
    for doc_id in transcript.cited_doc_ids:
        if doc_id not in corpus_by_id:
            raise ValueError(f"transcript cites unknown doc id: {doc_id}")

    read_states = _read_states(transcript)
    cited_docs = tuple(
        corpus_by_id[doc_id] for doc_id in transcript.cited_doc_ids
    )
    successful_reads = [
        record.doc_id for record in transcript.reads if record.outcome == "success"
    ]
    cited_clusters = {document.cluster_id for document in cited_docs}

    violated = _violated_conditions(
        case=case,
        transcript=transcript,
        cited_docs=cited_docs,
        read_states=read_states,
        cited_clusters=cited_clusters,
        successful_reads=successful_reads,
    )
    false_closure = transcript.closed and bool(violated)

    primary_retrieval = any(
        document.source_role == "primary"
        and read_states.get(document.doc_id) == "read_ok"
        for document in case.corpus
    )

    useful_reads = sum(
        1 for doc_id in transcript.cited_doc_ids if read_states.get(doc_id) == "read_ok"
    )
    useful_read_ratio = (
        useful_reads / len(successful_reads) if successful_reads else 0.0
    )

    expected_surfaces = {claim.surface for claim in case.gold.expected_claims}
    addressed = set(transcript.addressed_claim_surfaces)
    critical_claim_coverage = (
        len(expected_surfaces & addressed) / len(expected_surfaces)
        if expected_surfaces
        else 0.0
    )

    failure_reasons = _failure_reasons(
        transcript=transcript,
        false_closure=false_closure,
        violated=violated,
        primary_retrieval=primary_retrieval,
        primary_required=case.gold.primary_exists,
    )

    shadow = _evaluate_shadow(
        case=case,
        transcript=transcript,
        cited_docs=cited_docs,
        read_states=read_states,
    )

    return RunEvaluation(
        case_id=case.id,
        category=case.category,
        mode=case.mode,
        closed=transcript.closed,
        false_closure=false_closure,
        violated_closure_conditions=tuple(sorted(violated)),
        primary_retrieval=primary_retrieval,
        useful_read_ratio=useful_read_ratio,
        independent_cluster_count=len(cited_clusters),
        critical_claim_coverage=critical_claim_coverage,
        citation_entailment=None,
        search_count=transcript.searches,
        query_count=len(transcript.queries),
        read_count=len(transcript.reads),
        llm_calls=transcript.llm_calls,
        elapsed_seconds=transcript.elapsed_seconds,
        failure_reasons=tuple(sorted(set(failure_reasons))),
        shadow_status=shadow.shadow_status,
        shadow_would_pass=shadow.shadow_would_pass,
        shadow_would_block=shadow.shadow_would_block,
        legacy_would_stop_but_shadow_blocked=(
            shadow.legacy_would_stop_but_shadow_blocked
        ),
        shadow_reasons=shadow.reasons,
        open_critical_claims=shadow.open_critical_claims,
    )


def evaluate_research_runs(
    cases: Iterable[ResearchQualityEvalCase],
    transcripts: Iterable[ResearchRunTranscript],
) -> tuple[RunEvaluation, ...]:
    cases_by_id = {case.id: case for case in cases}
    evaluations: list[RunEvaluation] = []
    seen: set[str] = set()
    for transcript in transcripts:
        if transcript.case_id in seen:
            raise ValueError(f"duplicate transcript for case: {transcript.case_id}")
        seen.add(transcript.case_id)
        case = cases_by_id.get(transcript.case_id)
        if case is None:
            raise ValueError(f"transcript has no matching case: {transcript.case_id}")
        evaluations.append(evaluate_research_run(case, transcript))
    return tuple(evaluations)


def summarize_run_evaluations(
    evaluations: tuple[RunEvaluation, ...],
) -> ShadowRunSummary:
    total = len(evaluations)
    closed_runs = sum(1 for item in evaluations if item.closed)
    false_closures = sum(1 for item in evaluations if item.false_closure)
    shadow_blocked = sum(1 for item in evaluations if item.shadow_would_block)
    caught = sum(
        1 for item in evaluations if item.false_closure and item.shadow_would_block
    )
    missed = sum(
        1 for item in evaluations if item.false_closure and not item.shadow_would_block
    )
    overblocked = sum(
        1
        for item in evaluations
        if item.closed and not item.false_closure and item.shadow_would_block
    )
    primary_required = [
        item for item in evaluations if item.category != "no_primary_exists"
    ]
    primary_rate = (
        sum(1 for item in primary_required if item.primary_retrieval)
        / len(primary_required)
        if primary_required
        else 0.0
    )
    mean_useful = (
        sum(item.useful_read_ratio for item in evaluations) / total if total else 0.0
    )
    mean_coverage = (
        sum(item.critical_claim_coverage for item in evaluations) / total
        if total
        else 0.0
    )
    categories = sorted({item.category for item in evaluations})
    per_category = tuple(
        (
            category,
            sum(1 for item in evaluations if item.category == category),
            sum(
                1
                for item in evaluations
                if item.category == category and item.false_closure
            ),
            sum(
                1
                for item in evaluations
                if item.category == category and item.false_closure and item.shadow_would_block
            ),
        )
        for category in categories
    )
    return ShadowRunSummary(
        total_cases=total,
        closed_runs=closed_runs,
        false_closures=false_closures,
        shadow_blocked_runs=shadow_blocked,
        caught_false_closures=caught,
        missed_false_closures=missed,
        overblocked_correct_closures=overblocked,
        primary_retrieval_rate=primary_rate,
        mean_useful_read_ratio=mean_useful,
        mean_critical_claim_coverage=mean_coverage,
        per_category=per_category,
    )


def _evaluate_shadow(
    *,
    case: ResearchQualityEvalCase,
    transcript: ResearchRunTranscript,
    cited_docs: tuple[FrozenCorpusDocument, ...],
    read_states: dict[str, str],
) -> ShadowStopDecision:
    gold = case.gold
    referenced_ids = {record.doc_id for record in transcript.reads} | set(
        transcript.cited_doc_ids
    )
    evidence = tuple(
        ResearchEvidence(
            evidence_id=f"ev_{document.doc_id}",
            locator=document.url,
            anchored_spans=(document.title,),
            lifecycle_status=(
                "read"
                if read_states.get(document.doc_id) == "read_ok"
                else "candidate"
            ),
            extraction_status=(
                "eligible"
                if read_states.get(document.doc_id) == "read_ok"
                else (
                    "read_failed"
                    if read_states.get(document.doc_id) == "read_failed"
                    else (
                        "extractor_failed"
                        if read_states.get(document.doc_id) == "extraction_failed"
                        else "not_attempted"
                    )
                )
            ),
        )
        for document in case.corpus
        if document.doc_id in referenced_ids
    )
    known_ids = [item.evidence_id for item in evidence]

    min_independent = (
        2
        if "independent_sources_below_minimum" in gold.forbidden_closure_conditions
        else 1
    )
    requires_primary = (
        gold.primary_exists and "primary" in gold.required_source_roles
    )
    unverifiable = "question_unverifiable" in gold.forbidden_closure_conditions
    claims = tuple(
        ResearchClaim(
            id=f"claim_{index}",
            question_id="q_eval",
            text=claim.surface,
            kind=claim.kind,
            priority=claim.priority,
            state="unavailable" if unverifiable else "searching",
            evidence_requirement=EvidenceRequirement(
                source_roles=tuple(gold.required_source_roles),
                min_independent_sources=min_independent,
                requires_primary_source=requires_primary,
                requires_successful_read=True,
            ),
        )
        for index, claim in enumerate(sorted(gold.expected_claims, key=lambda c: c.surface))
    )
    question = ResearchQuestion(
        id="q_eval",
        question_surface=gold.question,
        priority="critical",
        state="searching",
    )
    gaps = tuple(
        EvidenceGap(
            id=f"gap_{claim.id}",
            claim_id=claim.id,
            gap_type="evidence_shortfall",
            desired_source_role=gold.required_source_roles[0],
            priority="critical",
            attempt_count=transcript.searches,
            state="open",
        )
        for claim in claims
    )

    links: list[ResearchClaimEvidenceLink] = []
    conflicting_case = bool(gold.known_conflicts)
    cited_cluster_order: dict[str, FrozenCorpusDocument] = {}
    for document in cited_docs:
        cited_cluster_order.setdefault(document.cluster_id, document)
    clusters_in_order = list(cited_cluster_order.values())
    for claim in claims:
        for document in cited_docs:
            relation = "supports"
            if (
                conflicting_case
                and len(clusters_in_order) >= 2
                and document is not clusters_in_order[0]
                and document.cluster_id != clusters_in_order[0].cluster_id
            ):
                relation = "contradicts"
            links.append(
                ResearchClaimEvidenceLink(
                    link=ClaimEvidenceLinkV1(
                        claim_id=claim.id,
                        evidence_id=f"ev_{document.doc_id}",
                        support_type=relation,
                        confidence=_LINK_STRENGTH,
                    ),
                    source_role=document.source_role,
                    source_cluster_id=document.cluster_id,
                    locator=document.url,
                )
            )

    clusters = tuple(
        EvidenceCluster(
            id=document.cluster_id,
            evidence_ids=tuple(
                f"ev_{item.doc_id}"
                for item in case.corpus
                if item.cluster_id == document.cluster_id
                and item.doc_id in referenced_ids
            ),
            source_role=document.source_role,
            independence_key=document.cluster_id,
        )
        for document in sorted(
            {item.cluster_id: item for item in case.corpus}.values(),
            key=lambda item: item.cluster_id,
        )
        if any(
            item.doc_id in referenced_ids
            for item in case.corpus
            if item.cluster_id == document.cluster_id
        )
    )

    budget = ResearchBudget(
        max_candidates=_BOUNDED_MAX_CANDIDATES,
        max_reads=_BOUNDED_MAX_READS,
        soft_timeout_seconds=_BOUNDED_SOFT_TIMEOUT,
        hard_timeout_seconds=_BOUNDED_HARD_TIMEOUT,
        max_total_chars=0,
        candidates_used=len(case.corpus),
        reads_used=len(transcript.reads),
        elapsed_seconds=transcript.elapsed_seconds,
    )
    state = build_research_state(
        mode="shadow",
        questions=(question,),
        claims=claims,
        evidence=evidence,
        evidence_links=links,
        source_clusters=clusters,
        gaps=gaps,
        conflict_gaps=(),
        budget=budget,
        known_evidence_ids=known_ids,
    )
    return evaluate_shadow_stop(state, legacy_would_stop=transcript.closed)


def _read_states(transcript: ResearchRunTranscript) -> dict[str, str]:
    states: dict[str, str] = {}
    for record in transcript.reads:
        if record.outcome == "failed":
            states[record.doc_id] = "read_failed"
        elif record.extraction_eligible:
            states[record.doc_id] = "read_ok"
        else:
            states[record.doc_id] = "extraction_failed"
    return states


def _violated_conditions(
    *,
    case: ResearchQualityEvalCase,
    transcript: ResearchRunTranscript,
    cited_docs: tuple[FrozenCorpusDocument, ...],
    read_states: dict[str, str],
    cited_clusters: set[str],
    successful_reads: list[str],
) -> set[str]:
    gold = case.gold
    violated: set[str] = set()
    if not transcript.closed:
        return violated
    if not cited_docs:
        violated.add("no_cited_evidence")
        return violated

    for condition in gold.forbidden_closure_conditions:
        if condition == "primary_not_read":
            has_primary_read = any(
                document.source_role == "primary"
                and read_states.get(document.doc_id) == "read_ok"
                for document in case.corpus
            )
            if not has_primary_read:
                violated.add(condition)
        elif condition == "independent_sources_below_minimum":
            if len(cited_clusters) < 2:
                violated.add(condition)
        elif condition == "conflict_unresolved":
            if gold.known_conflicts and len(cited_clusters) < 2:
                violated.add(condition)
        elif condition == "freshness_unmet":
            if _freshness_unmet(
                gold_max_age=(
                    gold.freshness_requirement.max_age_days
                    if gold.freshness_requirement
                    else None
                ),
                requires_dated=(
                    gold.freshness_requirement.requires_dated_evidence
                    if gold.freshness_requirement
                    else False
                ),
                cited_docs=cited_docs,
                reference_date=transcript.reference_date,
            ):
                violated.add(condition)
        elif condition == "snippet_only_evidence":
            if any(
                read_states.get(document.doc_id) != "read_ok"
                for document in cited_docs
            ):
                violated.add(condition)
        elif condition == "extraction_failed":
            if any(
                read_states.get(document.doc_id)
                in {"read_failed", "extraction_failed"}
                for document in cited_docs
            ):
                violated.add(condition)
        elif condition == "question_unverifiable":
            violated.add(condition)
    return violated


def _freshness_unmet(
    *,
    gold_max_age: int | None,
    requires_dated: bool,
    cited_docs: tuple[FrozenCorpusDocument, ...],
    reference_date: str,
) -> bool:
    try:
        reference = date.fromisoformat(reference_date)
    except ValueError:
        return True
    fresh_any = False
    dated_any = False
    for document in cited_docs:
        if document.published_at is None:
            continue
        try:
            published = date.fromisoformat(document.published_at)
        except ValueError:
            continue
        dated_any = True
        if gold_max_age is not None and 0 <= (reference - published).days <= gold_max_age:
            fresh_any = True
    if gold_max_age is not None and not fresh_any:
        return True
    if requires_dated and not dated_any:
        return True
    return False


def _failure_reasons(
    *,
    transcript: ResearchRunTranscript,
    false_closure: bool,
    violated: set[str],
    primary_retrieval: bool,
    primary_required: bool,
) -> list[str]:
    reasons: list[str] = []
    if false_closure:
        reasons.append("false_closure")
    reasons.extend(f"violated:{condition}" for condition in sorted(violated))
    if primary_required and not primary_retrieval:
        reasons.append("primary_not_retrieved")
    if transcript.closed and not transcript.cited_doc_ids:
        reasons.append("closed_without_citations")
    for record in transcript.reads:
        if record.outcome == "failed":
            reasons.append(f"read_failed:{record.doc_id}")
    return reasons


def _parse_read_record(raw: Any) -> RunReadRecord:
    data = _mapping(raw, "transcript read record")
    _only_keys(
        data, {"doc_id", "outcome", "extraction_eligible"}, "transcript read record"
    )
    return RunReadRecord(
        doc_id=_text(data.get("doc_id"), "read doc id", 200),
        outcome=_enum(data.get("outcome"), _RUN_READ_OUTCOMES, "read outcome"),
        extraction_eligible=_boolean(
            data.get("extraction_eligible", True),
            "read extraction_eligible",
        ),
    )


def _mapping(raw: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(raw, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return raw


def _only_keys(raw: Mapping[str, Any], allowed: set[str], label: str) -> None:
    for key in raw:
        if key not in allowed:
            raise ValueError(f"unknown {label} field: {key}")


def _text(raw: Any, label: str, max_length: int) -> str:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(f"{label} must be non-empty text")
    if len(raw) > max_length:
        raise ValueError(f"{label} exceeds {max_length} characters")
    return raw


def _enum(raw: Any, allowed: set[str], label: str) -> Any:
    value = _text(raw, label, 100)
    if value not in allowed:
        raise ValueError(f"invalid {label}: {value}")
    return value


def _boolean(raw: Any, label: str) -> bool:
    if not isinstance(raw, bool):
        raise ValueError(f"{label} must be boolean")
    return raw


def _number(raw: Any, label: str) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"{label} must be numeric")
    return float(raw)


def _non_negative_int(raw: Any, label: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"{label} must be an integer")
    if raw < 0:
        raise ValueError(f"{label} cannot be negative")
    return raw


def _string_tuple(raw: Any, label: str) -> tuple[str, ...]:
    if not isinstance(raw, list):
        raise ValueError(f"{label} must be a list")
    values = tuple(_text(value, label, 500) for value in raw)
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {label}")
    return tuple(sorted(values))


def _publication_date(raw: Any) -> str:
    value = _text(raw, "transcript reference_date", 100)
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            "transcript reference_date must be an ISO-8601 date"
        ) from exc
    return value


__all__ = [
    "RESEARCH_QUALITY_RUN_SCHEMA_VERSION",
    "ReadState",
    "ResearchRunTranscript",
    "RunEvaluation",
    "RunReadOutcome",
    "RunReadRecord",
    "ShadowRunSummary",
    "evaluate_research_run",
    "evaluate_research_runs",
    "research_run_transcript_from_dict",
    "research_run_transcript_to_dict",
    "summarize_run_evaluations",
]
