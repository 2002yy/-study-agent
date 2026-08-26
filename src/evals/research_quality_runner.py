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

from dataclasses import dataclass, replace
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
    ClaimEvidenceRelation,
    ResearchBudget,
    ResearchClaim,
    ResearchClaimEvidenceLink,
    ResearchClaimKind,
    ResearchClaimPriority,
    ResearchClaimState,
    ResearchEvidence,
    ResearchQuestion,
    build_research_state,
)
from src.web.research.policy import (
    EvidencePolicyProfile,
    evidence_policy_for_claim,
)
from src.web.research.stop_gate import (
    ShadowStopDecision,
    evaluate_shadow_stop,
)

RESEARCH_QUALITY_RUN_SCHEMA_VERSION = "research-quality-run-v2"
LEGACY_RESEARCH_QUALITY_RUN_SCHEMA_VERSION = "research-quality-run-v1"

RunReadOutcome = Literal["success", "failed"]
ReadState = Literal["read_ok", "read_failed", "extraction_failed", "snippet_only"]

_RUN_READ_OUTCOMES = {"success", "failed"}
_CLAIM_KINDS = {"research_question", "hypothesis", "factual", "analytical"}
_CLAIM_PRIORITIES = {"critical", "major", "context"}
_CLAIM_STATES = {
    "pending",
    "searching",
    "satisfied",
    "partially_satisfied",
    "unresolved",
    "unavailable",
    "contested",
}
_POLICY_PROFILES = {
    "official_statement",
    "current_fact",
    "quantitative_claim",
    "causal_analysis",
    "community_sentiment",
    "exploratory_hypothesis",
}
_EVIDENCE_RELATIONS = {"supports", "contradicts", "qualifies", "background", "lead"}
_USEFUL_RELATIONS = {"supports", "contradicts", "qualifies", "lead"}
_COVERAGE_RELATIONS = {"supports", "contradicts", "qualifies"}
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
class ProjectedClaim:
    """Claim emitted by the recorded legacy projection, never by eval gold."""

    surface: str
    kind: ResearchClaimKind
    priority: ResearchClaimPriority
    state: ResearchClaimState
    evidence_policy_profile: EvidencePolicyProfile
    max_age_days: int | None = None
    requires_dated_evidence: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "surface": self.surface,
            "kind": self.kind,
            "priority": self.priority,
            "state": self.state,
            "evidence_policy_profile": self.evidence_policy_profile,
            "max_age_days": self.max_age_days,
            "requires_dated_evidence": self.requires_dated_evidence,
        }


@dataclass(frozen=True)
class ProjectedClaimEvidence:
    """Recorded projection of one evidence contribution to one claim."""

    claim_surface: str
    doc_id: str
    relation: ClaimEvidenceRelation
    strength: float = _LINK_STRENGTH

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_surface": self.claim_surface,
            "doc_id": self.doc_id,
            "relation": self.relation,
            "strength": self.strength,
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
    question_surface: str = ""
    projected_claims: tuple[ProjectedClaim, ...] = ()
    projected_claim_evidence: tuple[ProjectedClaimEvidence, ...] = ()
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
            "question_surface": self.question_surface,
            "projected_claims": [claim.to_dict() for claim in self.projected_claims],
            "projected_claim_evidence": [
                link.to_dict() for link in self.projected_claim_evidence
            ],
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
    primary_required: bool
    primary_retrieval: bool
    successful_read_count: int
    useful_read_count: int
    useful_read_ratio: float
    independent_cluster_count: int
    critical_claim_count: int
    covered_critical_claim_count: int
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
            "primary_required": self.primary_required,
            "primary_retrieval": self.primary_retrieval,
            "successful_read_count": self.successful_read_count,
            "useful_read_count": self.useful_read_count,
            "useful_read_ratio": self.useful_read_ratio,
            "independent_cluster_count": self.independent_cluster_count,
            "critical_claim_count": self.critical_claim_count,
            "covered_critical_claim_count": self.covered_critical_claim_count,
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
    primary_retrieved_cases: int
    primary_required_cases: int
    primary_retrieval_rate: float
    useful_read_count: int
    successful_read_count: int
    mean_useful_read_ratio: float
    covered_critical_claim_count: int
    critical_claim_count: int
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
            "primary_retrieved_cases": self.primary_retrieved_cases,
            "primary_required_cases": self.primary_required_cases,
            "primary_retrieval_rate": self.primary_retrieval_rate,
            "useful_read_count": self.useful_read_count,
            "successful_read_count": self.successful_read_count,
            "mean_useful_read_ratio": self.mean_useful_read_ratio,
            "covered_critical_claim_count": self.covered_critical_claim_count,
            "critical_claim_count": self.critical_claim_count,
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
            "question_surface",
            "projected_claims",
            "projected_claim_evidence",
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
    claims_raw = data.get("projected_claims", [])
    if not isinstance(claims_raw, list):
        raise ValueError("research run transcript projected_claims must be a list")
    projected_claims = tuple(_parse_projected_claim(item) for item in claims_raw)
    claim_surfaces = [claim.surface for claim in projected_claims]
    if len(set(claim_surfaces)) != len(claim_surfaces):
        raise ValueError("duplicate projected claim surface")
    links_raw = data.get("projected_claim_evidence", [])
    if not isinstance(links_raw, list):
        raise ValueError(
            "research run transcript projected_claim_evidence must be a list"
        )
    projected_links = tuple(_parse_projected_claim_evidence(item) for item in links_raw)
    link_keys = [
        (link.claim_surface, link.doc_id, link.relation) for link in projected_links
    ]
    if len(set(link_keys)) != len(link_keys):
        raise ValueError("duplicate projected claim evidence link")
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
        question_surface=_optional_text(
            data.get("question_surface"), "transcript question_surface", 2000
        ),
        projected_claims=projected_claims,
        projected_claim_evidence=projected_links,
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
    projected_surfaces = {claim.surface for claim in transcript.projected_claims}
    for link in transcript.projected_claim_evidence:
        if link.doc_id not in corpus_by_id:
            raise ValueError(
                f"projected claim evidence references unknown doc id: {link.doc_id}"
            )
        if link.claim_surface not in projected_surfaces:
            raise ValueError(
                "projected claim evidence references unknown claim surface: "
                f"{link.claim_surface}"
            )

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

    useful_doc_ids = {
        link.doc_id
        for link in transcript.projected_claim_evidence
        if link.relation in _USEFUL_RELATIONS
        and read_states.get(link.doc_id) == "read_ok"
    }
    useful_reads = len(useful_doc_ids)
    useful_read_ratio = (
        useful_reads / len(successful_reads) if successful_reads else 0.0
    )

    expected_surfaces = {
        claim.surface
        for claim in case.gold.expected_claims
        if claim.priority == "critical"
    }
    evidence_linked_surfaces = {
        link.claim_surface
        for link in transcript.projected_claim_evidence
        if link.relation in _COVERAGE_RELATIONS
        and read_states.get(link.doc_id) == "read_ok"
    }
    covered_surfaces = expected_surfaces & evidence_linked_surfaces
    critical_claim_coverage = (
        len(covered_surfaces) / len(expected_surfaces)
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
        corpus=case.corpus,
        transcript=transcript,
        read_states=read_states,
    )

    return RunEvaluation(
        case_id=case.id,
        category=case.category,
        mode=case.mode,
        closed=transcript.closed,
        false_closure=false_closure,
        violated_closure_conditions=tuple(sorted(violated)),
        primary_required=case.gold.primary_exists,
        primary_retrieval=primary_retrieval,
        successful_read_count=len(successful_reads),
        useful_read_count=useful_reads,
        useful_read_ratio=useful_read_ratio,
        independent_cluster_count=len(cited_clusters),
        critical_claim_count=len(expected_surfaces),
        covered_critical_claim_count=len(covered_surfaces),
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
    primary_required = [item for item in evaluations if item.primary_required]
    primary_retrieved = sum(1 for item in primary_required if item.primary_retrieval)
    primary_rate = (
        primary_retrieved / len(primary_required)
        if primary_required
        else 0.0
    )
    useful_read_count = sum(item.useful_read_count for item in evaluations)
    successful_read_count = sum(item.successful_read_count for item in evaluations)
    mean_useful = (
        sum(item.useful_read_ratio for item in evaluations) / total if total else 0.0
    )
    covered_critical_claim_count = sum(
        item.covered_critical_claim_count for item in evaluations
    )
    critical_claim_count = sum(item.critical_claim_count for item in evaluations)
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
        primary_retrieved_cases=primary_retrieved,
        primary_required_cases=len(primary_required),
        primary_retrieval_rate=primary_rate,
        useful_read_count=useful_read_count,
        successful_read_count=successful_read_count,
        mean_useful_read_ratio=mean_useful,
        covered_critical_claim_count=covered_critical_claim_count,
        critical_claim_count=critical_claim_count,
        mean_critical_claim_coverage=mean_coverage,
        per_category=per_category,
    )


def _evaluate_shadow(
    *,
    corpus: tuple[FrozenCorpusDocument, ...],
    transcript: ResearchRunTranscript,
    read_states: dict[str, str],
) -> ShadowStopDecision:
    """Evaluate a recorded projection without any access to eval gold."""

    if not transcript.question_surface or not transcript.projected_claims:
        return ShadowStopDecision(
            legacy_would_stop=transcript.closed,
            legacy_should_stop=transcript.closed,
            shadow_status="unavailable",
            shadow_would_pass=False,
            shadow_would_block=False,
            legacy_would_stop_but_shadow_blocked=False,
            reasons=("shadow_projection_missing",),
        )

    corpus_by_id = {document.doc_id: document for document in corpus}
    referenced_ids = {record.doc_id for record in transcript.reads} | set(
        transcript.cited_doc_ids
    ) | {link.doc_id for link in transcript.projected_claim_evidence}
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
            published_at=document.published_at or "",
        )
        for document in corpus
        if document.doc_id in referenced_ids
    )
    known_ids = [item.evidence_id for item in evidence]

    projected_claims = tuple(
        sorted(transcript.projected_claims, key=lambda claim: claim.surface)
    )
    claim_id_by_surface: dict[str, str] = {}
    claims_list: list[ResearchClaim] = []
    for index, projected in enumerate(projected_claims):
        claim_id = f"claim_{index}"
        claim_id_by_surface[projected.surface] = claim_id
        policy = evidence_policy_for_claim(
            kind=projected.kind,
            priority=projected.priority,
            profile=projected.evidence_policy_profile,
        )
        claims_list.append(
            ResearchClaim(
                id=claim_id,
                question_id="q_eval",
                text=projected.surface,
                kind=projected.kind,
                priority=projected.priority,
                state=projected.state,
                evidence_requirement=replace(
                    policy.requirement,
                    max_age_days=projected.max_age_days,
                    requires_dated_evidence=projected.requires_dated_evidence,
                ),
            ),
        )
    claims = tuple(claims_list)
    question = ResearchQuestion(
        id="q_eval",
        question_surface=transcript.question_surface,
        priority="critical",
        state="searching",
    )
    gaps = tuple(
        EvidenceGap(
            id=f"gap_{claim.id}",
            claim_id=claim.id,
            gap_type="evidence_shortfall",
            desired_source_role=(
                claim.evidence_requirement.source_roles[0]
                if claim.evidence_requirement.source_roles
                else ""
            ),
            priority="critical",
            attempt_count=transcript.searches,
            state="open",
        )
        for claim in claims
    )

    links: list[ResearchClaimEvidenceLink] = []
    for projected_link in transcript.projected_claim_evidence:
        document = corpus_by_id[projected_link.doc_id]
        links.append(
            ResearchClaimEvidenceLink(
                link=ClaimEvidenceLinkV1(
                    claim_id=claim_id_by_surface[projected_link.claim_surface],
                    evidence_id=f"ev_{document.doc_id}",
                    support_type=projected_link.relation,
                    confidence=projected_link.strength,
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
                for item in corpus
                if item.cluster_id == document.cluster_id
                and item.doc_id in referenced_ids
            ),
            source_role=document.source_role,
            independence_key=document.cluster_id,
        )
        for document in sorted(
            {item.cluster_id: item for item in corpus}.values(),
            key=lambda item: item.cluster_id,
        )
        if any(
            item.doc_id in referenced_ids
            for item in corpus
            if item.cluster_id == document.cluster_id
        )
    )

    budget = ResearchBudget(
        max_candidates=_BOUNDED_MAX_CANDIDATES,
        max_reads=_BOUNDED_MAX_READS,
        soft_timeout_seconds=_BOUNDED_SOFT_TIMEOUT,
        hard_timeout_seconds=_BOUNDED_HARD_TIMEOUT,
        max_total_chars=0,
        candidates_used=len(corpus),
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
        reference_date=transcript.reference_date,
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


def _parse_projected_claim(raw: Any) -> ProjectedClaim:
    data = _mapping(raw, "projected claim")
    _only_keys(
        data,
        {
            "surface",
            "kind",
            "priority",
            "state",
            "evidence_policy_profile",
            "max_age_days",
            "requires_dated_evidence",
        },
        "projected claim",
    )
    return ProjectedClaim(
        surface=_text(data.get("surface"), "projected claim surface", 2000),
        kind=_enum(data.get("kind"), _CLAIM_KINDS, "projected claim kind"),
        priority=_enum(
            data.get("priority"), _CLAIM_PRIORITIES, "projected claim priority"
        ),
        state=_enum(data.get("state"), _CLAIM_STATES, "projected claim state"),
        evidence_policy_profile=_enum(
            data.get("evidence_policy_profile"),
            _POLICY_PROFILES,
            "projected claim evidence policy profile",
        ),
        max_age_days=_optional_non_negative_int(
            data.get("max_age_days"), "projected claim max_age_days"
        ),
        requires_dated_evidence=_boolean(
            data.get("requires_dated_evidence", False),
            "projected claim requires_dated_evidence",
        ),
    )


def _parse_projected_claim_evidence(raw: Any) -> ProjectedClaimEvidence:
    data = _mapping(raw, "projected claim evidence")
    _only_keys(
        data,
        {"claim_surface", "doc_id", "relation", "strength"},
        "projected claim evidence",
    )
    strength = _number(data.get("strength", _LINK_STRENGTH), "projected link strength")
    if not 0.0 <= strength <= 1.0:
        raise ValueError("projected link strength must be between 0 and 1")
    return ProjectedClaimEvidence(
        claim_surface=_text(
            data.get("claim_surface"), "projected link claim_surface", 2000
        ),
        doc_id=_text(data.get("doc_id"), "projected link doc_id", 200),
        relation=_enum(
            data.get("relation"), _EVIDENCE_RELATIONS, "projected link relation"
        ),
        strength=strength,
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


def _optional_text(raw: Any, label: str, max_length: int) -> str:
    if raw is None or raw == "":
        return ""
    return _text(raw, label, max_length)


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


def _optional_non_negative_int(raw: Any, label: str) -> int | None:
    if raw is None:
        return None
    return _non_negative_int(raw, label)


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
    "LEGACY_RESEARCH_QUALITY_RUN_SCHEMA_VERSION",
    "ProjectedClaim",
    "ProjectedClaimEvidence",
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
