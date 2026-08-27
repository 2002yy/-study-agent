"""Production claim bootstrap for the Claim Engine runtime.

The model proposes only semantic claim shape.  Code owns identifiers, policy,
evidence requirements, initial gaps, trace events, and the resulting
``ResearchState``.  This module imports no evaluation helpers and performs no
search/read/persistence work.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from hashlib import sha256
from typing import Any, Mapping

from src.web.research.contracts import (
    EvidenceGap,
    EvidenceRequirement,
    ResearchBudget,
    ResearchClaim,
    ResearchQuestion,
    ResearchState,
    ResearchMode,
    ResearchTraceEvent,
    build_research_state,
)
from src.web.research.model_gateway import (
    AttemptFinishedHook,
    AttemptStartedHook,
    ResearchModelCallAudit,
    ResearchModelGateway,
)
from src.web.research.policy import evidence_policy_for_claim

RUNTIME_CLAIM_PLAN_SCHEMA_VERSION = "research-runtime-claim-plan-v1"
MAX_RUNTIME_CLAIMS = 6

_CLAIM_KINDS = {"research_question", "hypothesis", "factual", "analytical"}
_CLAIM_PRIORITIES = {"critical", "major", "context"}
_POLICY_PROFILES = {
    "official_statement",
    "current_fact",
    "quantitative_claim",
    "causal_analysis",
    "community_sentiment",
    "exploratory_hypothesis",
}

_CLAIM_SYSTEM_PROMPT = """You are a research claim planner.
Return one JSON object and no prose. Decompose only the supplied user question
into at most six independently evidence-testable claims. At least one claim
must be critical. Do not invent evidence, sources, URLs, identifiers, freshness
rules, or evidence thresholds. The runtime will assign identifiers and evidence
policy. Choose exactly one compatible policy_profile for each claim.
Schema:
{"schema_version":"research-runtime-claim-plan-v1","claims":[{"surface":"...","kind":"research_question|hypothesis|factual|analytical","priority":"critical|major|context","policy_profile":"official_statement|current_fact|quantitative_claim|causal_analysis|community_sentiment|exploratory_hypothesis"}]}"""


@dataclass(frozen=True)
class ProposedClaim:
    surface: str
    kind: str
    priority: str
    policy_profile: str


@dataclass(frozen=True)
class ClaimBootstrapResult:
    status: str
    state: ResearchState | None
    audits: tuple[ResearchModelCallAudit, ...]
    reason: str = ""

    @property
    def completed(self) -> bool:
        return self.status == "completed" and self.state is not None


class RuntimeClaimPlanner:
    def __init__(self, model_gateway: ResearchModelGateway) -> None:
        self.model_gateway = model_gateway

    def plan(
        self,
        *,
        run_id: str,
        question: str,
        reference_date: str,
        budget: ResearchBudget,
        freshness_requested: bool = False,
        freshness_days: int | None = None,
        timestamp: str | None = None,
        mode: ResearchMode = "shadow",
        timeout_seconds: float | None = None,
        on_attempt_started: AttemptStartedHook | None = None,
        on_attempt_finished: AttemptFinishedHook | None = None,
    ) -> ClaimBootstrapResult:
        normalized_run_id = _required_text(run_id, 300, "run_id")
        if mode not in {"shadow", "active"}:
            raise ValueError("unsupported research mode")
        normalized_question = _required_text(question, 4000, "question")
        normalized_reference_date = date.fromisoformat(reference_date).isoformat()
        normalized_freshness = _freshness_days(
            freshness_requested=freshness_requested,
            freshness_days=freshness_days,
        )
        audit_payload = {
            "question": normalized_question,
            "reference_date": normalized_reference_date,
            "freshness_requested": bool(freshness_requested),
            "freshness_days": normalized_freshness,
        }
        result = self.model_gateway.complete_structured(
            logical_call_id=f"research_claim_plan:{normalized_run_id}:1",
            purpose="research_claim_planning",
            messages=[
                {"role": "system", "content": _CLAIM_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _claim_user_payload(audit_payload),
                },
            ],
            audit_payload=audit_payload,
            response_schema_version=RUNTIME_CLAIM_PLAN_SCHEMA_VERSION,
            parse=_parse_claim_plan,
            data_categories=("user_question", "research_time_context"),
            data_counts={
                "user_question": 1,
                "question_chars": len(normalized_question),
            },
            max_tokens=4000,
            temperature=0.0,
            timeout_seconds=timeout_seconds,
            on_attempt_started=on_attempt_started,
            on_attempt_finished=on_attempt_finished,
        )
        if not result.completed or result.value is None:
            return ClaimBootstrapResult(
                status="unavailable",
                state=None,
                audits=result.audits,
                reason=result.reason or "claim_plan_unavailable",
            )

        state = _build_initial_state(
            run_id=normalized_run_id,
            question=normalized_question,
            reference_date=normalized_reference_date,
            proposals=result.value,
            budget=budget,
            freshness_days=normalized_freshness,
            timestamp=timestamp or _utc_now(),
            mode=mode,
        )
        return ClaimBootstrapResult(
            status="completed",
            state=state,
            audits=result.audits,
        )


def _parse_claim_plan(raw: Any) -> tuple[ProposedClaim, ...]:
    data = _strict_mapping(
        raw,
        {"schema_version", "claims"},
        "runtime claim plan",
    )
    if data.get("schema_version") != RUNTIME_CLAIM_PLAN_SCHEMA_VERSION:
        raise ValueError("unsupported runtime claim plan schema")
    claims_raw = data.get("claims")
    if not isinstance(claims_raw, list) or not 1 <= len(claims_raw) <= MAX_RUNTIME_CLAIMS:
        raise ValueError("runtime claim plan must contain one to six claims")

    proposals: list[ProposedClaim] = []
    seen: set[str] = set()
    for raw_claim in claims_raw:
        claim = _strict_mapping(
            raw_claim,
            {"surface", "kind", "priority", "policy_profile"},
            "runtime claim",
        )
        surface = _required_text(claim.get("surface"), 1000, "claim surface")
        dedupe_key = " ".join(surface.casefold().split())
        if dedupe_key in seen:
            raise ValueError("runtime claim plan contains duplicate claims")
        seen.add(dedupe_key)
        kind = _enum(claim.get("kind"), _CLAIM_KINDS, "claim kind")
        priority = _enum(claim.get("priority"), _CLAIM_PRIORITIES, "claim priority")
        profile = _enum(
            claim.get("policy_profile"), _POLICY_PROFILES, "evidence policy profile"
        )
        # This call is intentionally part of parse validation.  Invalid
        # kind/profile combinations consume an explicit model attempt and retry;
        # the runtime never repairs them with keyword heuristics.
        evidence_policy_for_claim(
            kind=kind,  # type: ignore[arg-type]
            priority=priority,  # type: ignore[arg-type]
            profile=profile,  # type: ignore[arg-type]
        )
        proposals.append(
            ProposedClaim(
                surface=surface,
                kind=kind,
                priority=priority,
                policy_profile=profile,
            )
        )
    if not any(item.priority == "critical" for item in proposals):
        raise ValueError("runtime claim plan requires at least one critical claim")
    return tuple(proposals)


def _build_initial_state(
    *,
    run_id: str,
    question: str,
    reference_date: str,
    proposals: tuple[ProposedClaim, ...],
    budget: ResearchBudget,
    freshness_days: int | None,
    timestamp: str,
    mode: ResearchMode,
) -> ResearchState:
    question_id = _stable_id("question", run_id, question)
    research_question = ResearchQuestion(
        id=question_id,
        question_surface=question,
        priority="major",
        state="unresolved",
    )
    claims: list[ResearchClaim] = []
    gaps: list[EvidenceGap] = []
    trace: list[ResearchTraceEvent] = []
    sequence = 0

    for ordinal, proposal in enumerate(proposals, start=1):
        policy = evidence_policy_for_claim(
            kind=proposal.kind,  # type: ignore[arg-type]
            priority=proposal.priority,  # type: ignore[arg-type]
            profile=proposal.policy_profile,  # type: ignore[arg-type]
        )
        requirement = _with_runtime_freshness(
            policy.requirement,
            profile=proposal.policy_profile,
            freshness_days=freshness_days,
        )
        claim_id = _stable_id(
            "claim",
            question_id,
            str(ordinal),
            proposal.surface,
        )
        claim = ResearchClaim(
            id=claim_id,
            question_id=question_id,
            text=proposal.surface,
            kind=proposal.kind,  # type: ignore[arg-type]
            priority=proposal.priority,  # type: ignore[arg-type]
            state="pending",
            evidence_requirement=requirement,
            created_by="runtime_claim_planner",
            created_reason=f"policy_profile:{proposal.policy_profile}",
        )
        gap_id = _stable_id("gap", claim_id, _initial_gap_type(requirement))
        gap = EvidenceGap(
            id=gap_id,
            claim_id=claim_id,
            gap_type=_initial_gap_type(requirement),
            desired_source_role=(requirement.source_roles[0] if requirement.source_roles else ""),
            priority=proposal.priority,  # type: ignore[arg-type]
            attempt_count=0,
            state="open",
        )
        claims.append(claim)
        gaps.append(gap)
        trace.append(
            ResearchTraceEvent(
                sequence=sequence,
                timestamp=timestamp,
                run_id=run_id,
                event_type="claim_created",
                reason="runtime_claim_plan_validated",
                claim_id=claim_id,
            )
        )
        sequence += 1
        trace.append(
            ResearchTraceEvent(
                sequence=sequence,
                timestamp=timestamp,
                run_id=run_id,
                event_type="gap_created",
                reason=f"initial_gap:{gap.gap_type}",
                claim_id=claim_id,
                gap_id=gap_id,
            )
        )
        sequence += 1

    return build_research_state(
        mode=mode,
        questions=(research_question,),
        claims=claims,
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=gaps,
        conflict_gaps=(),
        budget=budget,
        trace=trace,
        brief=None,
        reference_date=reference_date,
        known_evidence_ids=(),
    )


def _with_runtime_freshness(
    requirement: EvidenceRequirement,
    *,
    profile: str,
    freshness_days: int | None,
) -> EvidenceRequirement:
    if freshness_days is None or profile == "exploratory_hypothesis":
        return requirement
    return EvidenceRequirement(
        source_roles=requirement.source_roles,
        min_independent_sources=requirement.min_independent_sources,
        requires_primary_source=requirement.requires_primary_source,
        requires_successful_read=requirement.requires_successful_read,
        max_age_days=freshness_days,
        requires_dated_evidence=True,
    )


def _freshness_days(
    *, freshness_requested: bool, freshness_days: int | None
) -> int | None:
    if not freshness_requested:
        return None
    if freshness_days is None:
        return 30
    if isinstance(freshness_days, bool):
        raise ValueError("freshness_days must be an integer")
    value = int(freshness_days)
    if value < 1 or value > 3650:
        raise ValueError("freshness_days is out of range")
    return value


def _initial_gap_type(requirement: EvidenceRequirement) -> str:
    if requirement.requires_primary_source:
        return "primary_required"
    if requirement.min_independent_sources > 1:
        return "independent_support_required"
    return "support_required"


def _claim_user_payload(payload: Mapping[str, Any]) -> str:
    # Deliberately structured and bounded: no history, memory, local RAG, or page
    # content enters claim bootstrap.
    import json

    return json.dumps(dict(payload), ensure_ascii=False, sort_keys=True)


def _stable_id(prefix: str, *parts: str) -> str:
    material = "\u0000".join(parts)
    return f"{prefix}_{sha256(material.encode('utf-8')).hexdigest()[:24]}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strict_mapping(raw: Any, allowed: set[str], label: str) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise TypeError(f"{label} must be an object")
    data = dict(raw)
    if set(data) != allowed:
        raise ValueError(f"{label} fields do not match schema")
    return data


def _required_text(value: Any, limit: int, label: str) -> str:
    text = " ".join(str(value or "").split())[:limit]
    if not text:
        raise ValueError(f"{label} must be non-empty")
    return text


def _enum(value: Any, allowed: set[str], label: str) -> str:
    normalized = _required_text(value, 100, label)
    if normalized not in allowed:
        raise ValueError(f"invalid {label}")
    return normalized


__all__ = [
    "ClaimBootstrapResult",
    "MAX_RUNTIME_CLAIMS",
    "ProposedClaim",
    "RUNTIME_CLAIM_PLAN_SCHEMA_VERSION",
    "RuntimeClaimPlanner",
]
