"""Production executor for one bounded active Claim Engine research wave.

The existing WebLookupRepository remains the operation and persistence owner.
This executor composes the previously delivered claim, query, candidate,
assessment, ranking, scheduling, reading, extraction and Evidence Gate
components without changing off/shadow/legacy execution.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import datetime, timezone
from math import ceil
import time
from typing import Any, cast

from src.domain.evidence import ClaimEvidenceLinkV1, build_evidence_snapshot
from src.domain.runtime_entities import WebLookupRun, new_id
from src.repositories.web_lookup_repository import WebLookupRepository
from src.web.research.active_adapter import ActiveResearchGateway
from src.web.research.active_semantics import (
    RuntimeCandidateAssessor,
    RuntimeEvidenceExtractor,
)
from src.web.research.candidate_pool import (
    CandidatePoolCancelled,
    CandidatePoolItem,
    execute_candidate_pool_batch,
)
from src.web.research.candidate_ranking import (
    CandidateSemanticAssessment,
    RankedCandidate,
    rank_candidate_pool,
)
from src.web.research.claim_planner import RuntimeClaimPlanner
from src.web.research.contracts import (
    EvidenceCluster,
    EvidenceGap,
    ResearchBrief,
    ResearchClaim,
    ResearchClaimEvidenceLink,
    ResearchEvidence,
    ResearchState,
    build_research_state,
)
from src.web.research.evidence_gate import EvidenceGateResult, evaluate_evidence_gate
from src.web.research.gap_planner import GapQueryBatch, GapSearchIntent, PlannedGapQuery, plan_gap_queries
from src.web.research.model_gateway import (
    ResearchModelAttemptStart,
    ResearchModelCallAudit,
    ResearchModelGateway,
)
from src.web.research.runtime import (
    ResearchRuntimeCursor,
    RuntimeCandidate,
    RuntimeExternalAttemptStart,
    RuntimeFailure,
    RuntimePlannedQuery,
    RuntimeQueryOutcome,
    RuntimeReadOutcome,
    attach_runtime_cursor,
    begin_external_attempt,
    begin_model_attempt,
    finish_external_attempt,
    finish_model_attempt,
    load_runtime_cursor,
    recover_interrupted_external_attempt,
    recover_interrupted_model_attempt,
)
from src.web.research.scheduler import (
    ReadSchedulerPolicy,
    ReadSchedulingCancelled,
    plan_read_wave,
)
from src.web.research.source_cluster import cluster_candidate_sources
from src.web.research.state import attach_claim_engine_state

ACTIVE_RESEARCH_ASSESSMENTS_KEY = "claim_engine_assessments"
ACTIVE_RESEARCH_READ_PLAN_KEY = "claim_engine_read_plan"
ACTIVE_RESEARCH_BRIEF_KEY = "claim_engine_evidence_brief"
ACTIVE_RESEARCH_METRICS_KEY = "claim_engine_metrics"
ACTIVE_RESEARCH_POLICY_AUDITS_KEY = "claim_engine_policy_audits"

PolicyCheck = Callable[[Mapping[str, Any], str], bool]


class ActiveResearchCancelled(RuntimeError):
    pass


class ActiveResearchRuntimeExecutor:
    """Execute one active run under the durable WebLookupRun owner."""

    def __init__(
        self,
        repository: WebLookupRepository,
        gateway: ActiveResearchGateway,
        *,
        model_gateway: ResearchModelGateway | None = None,
        claim_planner: RuntimeClaimPlanner | None = None,
        candidate_assessor: RuntimeCandidateAssessor | None = None,
        evidence_extractor: RuntimeEvidenceExtractor | None = None,
        policy_check: PolicyCheck | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        utc_now: Callable[[], str] | None = None,
    ) -> None:
        self.repository = repository
        self.gateway = gateway
        shared_model = model_gateway or ResearchModelGateway(timeout_seconds=20.0)
        self.claim_planner = claim_planner or RuntimeClaimPlanner(shared_model)
        self.candidate_assessor = candidate_assessor or RuntimeCandidateAssessor(shared_model)
        self.evidence_extractor = evidence_extractor or RuntimeEvidenceExtractor(shared_model)
        self.policy_check = policy_check or _default_policy_check
        self.monotonic = monotonic
        self.utc_now = utc_now or _utc_now

    def execute(
        self,
        run_id: str,
        *,
        initial_state: ResearchState,
        raise_on_error: bool = False,
        stale_after_seconds: int = 120,
    ) -> WebLookupRun:
        existing = self._required(run_id)
        if initial_state.mode != "active":
            raise ValueError("active runtime requires active Claim Engine state")
        if existing.status == "completed" and existing.provider_status == "found":
            raise ValueError(f"WebLookupRun is already complete: {run_id}")

        operation_id = new_id("rqce_active")
        run = self.repository.begin_operation(
            run_id,
            operation_id=operation_id,
            stage="planned",
            stale_after_seconds=stale_after_seconds,
        )
        context = dict(run.research_context)
        context["run_attempt"] = int(context.get("run_attempt") or 0) + 1
        state = initial_state
        cursor_result = load_runtime_cursor(context)
        loaded_cursor = cursor_result.cursor
        cursor: ResearchRuntimeCursor
        if cursor_result.available and loaded_cursor is not None:
            cursor = loaded_cursor
        else:
            cursor = ResearchRuntimeCursor()
        cursor = recover_interrupted_model_attempt(cursor)
        cursor = recover_interrupted_external_attempt(cursor)
        query_attempts = list(run.query_attempts)
        selected_sources = [dict(item) for item in run.selected_sources]
        rejected_sources = [dict(item) for item in run.rejected_sources]
        warnings = list(run.warnings)
        execution_started = self.monotonic()
        base_elapsed = state.budget.elapsed_seconds

        def elapsed() -> float:
            return base_elapsed + max(0.0, self.monotonic() - execution_started)

        def update_budget(*, reads_used: int | None = None) -> None:
            nonlocal state
            state = replace(
                state,
                budget=replace(
                    state.budget,
                    candidates_used=min(len(cursor.candidates), state.budget.max_candidates),
                    reads_used=(state.budget.reads_used if reads_used is None else reads_used),
                    elapsed_seconds=elapsed(),
                ),
            )

        def ensure_active() -> None:
            if self.repository.cancel_requested(run_id, operation_id=operation_id):
                raise ActiveResearchCancelled("active research cancelled")

        def known_evidence_ids() -> tuple[str, ...]:
            snapshot = _evidence_snapshot(run_id, selected_sources, rejected_sources)
            return tuple(ref.id for ref in snapshot.refs)

        def checkpoint(*, stage: str | None = None) -> WebLookupRun:
            nonlocal context
            if stage is not None and self._required(run_id).stage != stage:
                self.repository.set_stage(
                    run_id,
                    stage=stage,
                    operation_id=operation_id,
                )
            update_budget()
            context = attach_runtime_cursor(context, cursor)
            context = attach_claim_engine_state(
                context,
                state,
                known_evidence_ids=known_evidence_ids(),
            )
            _update_metrics(context, state, cursor)
            return self.repository.checkpoint(
                run_id,
                operation_id=operation_id,
                research_context=context,
                query_attempts=query_attempts,
                selected_sources=selected_sources,
                rejected_sources=rejected_sources,
                items=_eligible_items(selected_sources),
                warnings=_dedupe(warnings),
                provider_status="",
                stop_reason="",
                answer_confidence="",
            )

        def remaining_timeout() -> float:
            return max(1.0, min(20.0, state.budget.hard_timeout_seconds - elapsed()))

        def ensure_budget() -> None:
            if elapsed() >= state.budget.hard_timeout_seconds:
                raise _HardBudgetReached

        def model_allowed(purpose: str, categories: tuple[str, ...]) -> bool:
            allowed = bool(self.policy_check(context, purpose))
            audits = [
                dict(item)
                for item in context.get(ACTIVE_RESEARCH_POLICY_AUDITS_KEY, [])
                if isinstance(item, Mapping)
            ]
            audits.append(
                {
                    "call_id": f"policy:{purpose}:{len(audits) + 1}",
                    "purpose": purpose,
                    "status": "allowed" if allowed else "blocked_by_policy",
                    "data_categories": list(categories),
                    "checked_at": self.utc_now(),
                }
            )
            context[ACTIVE_RESEARCH_POLICY_AUDITS_KEY] = audits[-100:]
            if not allowed:
                _append_failure("blocked_by_policy", cursor.phase, purpose)
                checkpoint()
            return allowed

        def on_model_started(marker: ResearchModelAttemptStart) -> None:
            nonlocal cursor
            ensure_active()
            ensure_budget()
            cursor = begin_model_attempt(cursor, marker)
            checkpoint()

        def on_model_finished(audit: ResearchModelCallAudit) -> None:
            nonlocal cursor
            # B5-H1 crash-consistency: keep the completed audit in memory only.
            # The caller persists it together with the semantic result in the
            # next checkpoint, so a crash before that checkpoint leaves the
            # durable truth as an inflight call that recovery resolves through
            # interrupted_unknown with a bounded new attempt instead of a
            # completed call_id that can never re-enter inflight.
            cursor = finish_model_attempt(cursor, audit)
            ensure_active()

        def _append_failure(code: str, phase: str, item_id: str = "") -> None:
            nonlocal cursor
            cursor = replace(
                cursor,
                failures=(*cursor.failures, RuntimeFailure(code=code, phase=phase, item_id=item_id)),
            )

        try:
            ensure_active()
            checkpoint()

            # Bootstrap an empty active state through the audited model boundary.
            if not state.claims:
                cursor = replace(cursor, phase="planning")
                checkpoint(stage="planned")
                categories = ("public_research_question", "research_time_context")
                if not model_allowed("research_claim_planning", categories):
                    return self._terminal_unavailable(
                        run_id,
                        operation_id=operation_id,
                        context=context,
                        cursor=cursor,
                        state=state,
                        query_attempts=query_attempts,
                        selected_sources=selected_sources,
                        rejected_sources=rejected_sources,
                        warnings=warnings,
                        reason="claim_planning_blocked_by_policy",
                    )
                bootstrap = self.claim_planner.plan(
                    run_id=run_id,
                    question=run.query,
                    reference_date=state.reference_date or _utc_date(),
                    budget=state.budget,
                    mode="active",
                    timeout_seconds=remaining_timeout(),
                    on_attempt_started=on_model_started,
                    on_attempt_finished=on_model_finished,
                )
                ensure_active()
                if not bootstrap.completed or bootstrap.state is None:
                    _append_failure(bootstrap.reason or "claim_plan_unavailable", "planning")
                    checkpoint()
                    return self._terminal_unavailable(
                        run_id,
                        operation_id=operation_id,
                        context=context,
                        cursor=cursor,
                        state=state,
                        query_attempts=query_attempts,
                        selected_sources=selected_sources,
                        rejected_sources=rejected_sources,
                        warnings=warnings,
                        reason=bootstrap.reason or "claim_plan_unavailable",
                    )
                state = bootstrap.state
                # B5-H1: persist the completed model audit together with the
                # semantic result it produced (single checkpoint boundary).
                checkpoint()

            # Deterministic query planning is resumable from the persisted cursor.
            if not cursor.planned_queries:
                planned_queries: list[RuntimePlannedQuery] = []
                claims = {claim.id: claim for claim in state.claims}
                for gap in _ordered_gaps(state):
                    claim = claims[gap.claim_id]
                    batch = plan_gap_queries(
                        gap,
                        claim,
                        reference_date=state.reference_date,
                    )
                    planned_queries.extend(_runtime_query(item) for item in batch.queries)
                cursor = replace(
                    cursor,
                    phase="searching",
                    planned_queries=tuple(planned_queries[:100]),
                )
                checkpoint(stage="searching")

            if self._required(run_id).stage != "searching":
                self.repository.set_stage(
                    run_id,
                    stage="searching",
                    operation_id=operation_id,
                )

            # Search every still-pending planned query until the shared hard budget.
            for planned in cursor.planned_queries:
                if planned.id in cursor.completed_query_ids:
                    continue
                ensure_active()
                if elapsed() >= state.budget.hard_timeout_seconds:
                    break
                # B5-H2: once the candidate pool is full, further external
                # searches can only burn shared budget on results that would
                # be dropped by the pool cap, so stop before any external call.
                if len(cursor.candidates) >= state.budget.max_candidates:
                    break
                attempt = _attempt_number(cursor, planned.id)
                marker = RuntimeExternalAttemptStart(
                    call_id=f"research_search:{run_id}:{planned.id}:attempt:{attempt}",
                    purpose="search",
                    item_id=planned.id,
                    attempt=attempt,
                    started_at=self.utc_now(),
                )
                cursor = begin_external_attempt(cursor, marker)
                checkpoint()

                audit: dict[str, Any] | None = None

                def search_exact(query: str, *, max_results: int = 5) -> Mapping[str, Any]:
                    nonlocal audit
                    try:
                        payload = self.gateway.search_detailed(query, max_items=max_results)
                        audit = self.gateway.last_search_audit()
                        return payload
                    finally:
                        pass

                one_query = _gap_query_batch(planned)
                try:
                    batch_result = execute_candidate_pool_batch(
                        one_query,
                        search_exact=search_exact,
                        should_cancel=lambda: self.repository.cancel_requested(
                            run_id, operation_id=operation_id
                        ),
                        results_per_query=5,
                        max_candidates=state.budget.max_candidates,
                    )
                finally:
                    cursor = finish_external_attempt(cursor, call_id=marker.call_id)
                    checkpoint()
                ensure_active()
                outcome = batch_result.outcomes[0]
                cursor = replace(
                    cursor,
                    query_outcomes=(
                        *cursor.query_outcomes,
                        RuntimeQueryOutcome(
                            query_id=planned.id,
                            status=_runtime_query_status(outcome.status),
                            result_count=outcome.result_count,
                            providers=outcome.providers_attempted,
                            error_code=outcome.reason if outcome.status == "unavailable" else "",
                        ),
                    ),
                    candidates=_merge_runtime_candidates(
                        cursor.candidates,
                        batch_result.candidates,
                        max_candidates=state.budget.max_candidates,
                    ),
                )
                query_attempts.append(
                    {
                        "query": planned.query,
                        "query_id": planned.id,
                        "intent": planned.intent,
                        "status": outcome.status,
                        "reason": outcome.reason,
                        "result_count": outcome.result_count,
                        "providers_attempted": list(outcome.providers_attempted),
                        "provider_errors": list(outcome.provider_errors),
                        "run_attempt": context["run_attempt"],
                        "operation_id": operation_id,
                        **({"provider_audit": {"schema_version": "research-provider-audit-v1", **audit}} if audit else {}),
                    }
                )
                checkpoint()

            cursor = replace(cursor, phase="assessing")
            checkpoint(stage="assessing")

            # Strict semantic assessment and role-aware ranking, one claim at a time.
            stored_assessments = _assessment_store(context)
            claim_rankings: dict[str, tuple[RankedCandidate, ...]] = {}
            for claim in _ordered_claims(state):
                candidates = _candidates_for_claim(cursor, claim.id)
                if not candidates:
                    continue
                saved = stored_assessments.get(claim.id)
                if isinstance(saved, list) and saved:
                    claim_rankings[claim.id] = tuple(_ranked_from_dict(item) for item in saved)
                    continue
                ensure_budget()
                clusters = cluster_candidate_sources(candidates)
                assignments = {item.candidate_id: item for item in clusters.assignments}
                categories = ("public_research_claim", "public_candidate_metadata")
                if not model_allowed("research_candidate_assessment", categories):
                    _append_failure("candidate_assessment_blocked_by_policy", "assessing", claim.id)
                    continue
                assessed = self.candidate_assessor.assess(
                    run_id=run_id,
                    claim=claim,
                    candidates=candidates,
                    assignments=assignments,
                    reference_date=state.reference_date,
                    timeout_seconds=remaining_timeout(),
                    on_attempt_started=on_model_started,
                    on_attempt_finished=on_model_finished,
                )
                ensure_active()
                if assessed.status != "completed" or not assessed.assessments:
                    _append_failure(assessed.reason or "candidate_assessment_unavailable", "assessing", claim.id)
                    checkpoint()
                    continue
                ranked = rank_candidate_pool(
                    candidates,
                    claim=claim,
                    assessments=assessed.assessments,
                )
                claim_rankings[claim.id] = ranked
                stored_assessments[claim.id] = [item.to_dict() for item in ranked]
                context[ACTIVE_RESEARCH_ASSESSMENTS_KEY] = stored_assessments
                checkpoint()

            cursor = replace(cursor, phase="ranking")
            checkpoint(stage="assessing")

            physical_reads, extraction_targets = _load_read_plan(context)
            if not physical_reads and not extraction_targets:
                physical_reads, extraction_targets = _fair_read_plan(state, claim_rankings)
                context[ACTIVE_RESEARCH_READ_PLAN_KEY] = {
                    "physical_reads": physical_reads,
                    "extraction_targets": extraction_targets,
                }
                cursor = replace(
                    cursor,
                    phase="reading",
                    planned_read_ids=tuple(item["candidate_id"] for item in physical_reads),
                )
                checkpoint(stage="reading")

            if self._required(run_id).stage != "reading":
                self.repository.set_stage(
                    run_id,
                    stage="reading",
                    operation_id=operation_id,
                )

            # Read and checkpoint each selected source under the shared character budget.
            used_chars = sum(
                int(item.get("content_chars") or 0)
                for item in context.get(ACTIVE_RESEARCH_METRICS_KEY, {}).get("reads", [])
                if isinstance(item, Mapping)
            )
            successful_reads = state.budget.reads_used
            for item in physical_reads:
                candidate_id = item["candidate_id"]
                if candidate_id in cursor.completed_read_ids:
                    continue
                ensure_active()
                if successful_reads >= state.budget.max_reads or used_chars >= state.budget.max_total_chars:
                    break
                ensure_budget()
                candidate = _candidate_by_id(cursor, candidate_id)
                source_limit = min(6000, state.budget.max_total_chars - used_chars)
                attempt = _attempt_number(cursor, candidate_id)
                marker = RuntimeExternalAttemptStart(
                    call_id=f"research_read:{run_id}:{candidate_id}:attempt:{attempt}",
                    purpose="read",
                    item_id=candidate_id,
                    attempt=attempt,
                    started_at=self.utc_now(),
                )
                cursor = begin_external_attempt(cursor, marker)
                checkpoint()
                try:
                    raw_read = dict(self.gateway.read(candidate.url, max_chars=source_limit) or {})
                except Exception as exc:
                    raw_read = {
                        "ok": False,
                        "status": "failed",
                        "url": candidate.url,
                        "error": type(exc).__name__,
                    }
                finally:
                    cursor = finish_external_attempt(cursor, call_id=marker.call_id)
                    checkpoint()
                ensure_active()
                content = str(raw_read.get("content") or raw_read.get("readme") or "")[:source_limit]
                ok = bool(raw_read.get("ok") is True and content.strip())
                status = "success" if ok else "failed"
                if ok:
                    successful_reads += 1
                    used_chars += len(content)
                cursor = replace(
                    cursor,
                    read_outcomes=(
                        *cursor.read_outcomes,
                        RuntimeReadOutcome(
                            candidate_id=candidate_id,
                            status=status,
                            content_chars=len(content) if ok else 0,
                            error_code="" if ok else _bounded_text(raw_read.get("error") or "read_failed", 200),
                        ),
                    ),
                )
                record = _source_record(
                    candidate,
                    item,
                    raw_read={**raw_read, "content": content, "status": "read" if ok else "failed"},
                )
                _upsert_source(selected_sources, record)
                update_budget(reads_used=successful_reads)
                context.setdefault(ACTIVE_RESEARCH_METRICS_KEY, {})["reads"] = [
                    outcome.to_dict() for outcome in cursor.read_outcomes
                ]
                checkpoint()

            cursor = replace(cursor, phase="extracting")
            checkpoint(stage="reading")

            # A successful read is not evidence until strict extraction validates.
            # B5-H3: extraction targets bind (candidate_id, claim_id) pairs, so
            # one physical read can serve multiple claims.
            claims_by_id = {claim.id: claim for claim in state.claims}
            for item in extraction_targets:
                candidate_id = item["candidate_id"]
                claim_id = item["claim_id"]
                source_record = _source_by_candidate(selected_sources, candidate_id)
                if source_record is None or _read_status(source_record) != "read":
                    continue
                extractions = source_record.setdefault("extractions", {})
                prior = extractions.get(claim_id)
                if isinstance(prior, Mapping) and prior.get("status") in {"eligible", "extractor_failed"}:
                    continue
                legacy = source_record.get("extraction")
                if (
                    prior is None
                    and isinstance(legacy, Mapping)
                    and legacy.get("status") in {"eligible", "extractor_failed"}
                    and legacy.get("claim_id") == claim_id
                ):
                    continue
                ensure_active()
                ensure_budget()
                extraction_categories = (
                    "public_research_claim",
                    "public_candidate_metadata",
                    "bounded_public_page_excerpt",
                )
                if not model_allowed("research_evidence_extraction", extraction_categories):
                    extractions[claim_id] = {"status": "extractor_failed", "reason": "blocked_by_policy"}
                    _append_failure("extraction_blocked_by_policy", "extracting", candidate_id)
                    checkpoint()
                    continue
                candidate = _candidate_by_id(cursor, candidate_id)
                claim = claims_by_id[item["claim_id"]]
                read = cast(Mapping[str, Any], source_record["read"])
                extracted = self.evidence_extractor.extract(
                    run_id=run_id,
                    claim=claim,
                    candidate=candidate,
                    source_role=item["source_role"],
                    source_cluster_id=item["cluster_id"],
                    content=str(read.get("content") or ""),
                    timeout_seconds=remaining_timeout(),
                    on_attempt_started=on_model_started,
                    on_attempt_finished=on_model_finished,
                )
                ensure_active()
                if extracted.status != "completed" or extracted.extraction is None:
                    extractions[claim_id] = {
                        "status": "extractor_failed",
                        "reason": extracted.reason or "extractor_unavailable",
                    }
                    _append_failure(extracted.reason or "extractor_unavailable", "extracting", candidate_id)
                    checkpoint()
                    continue
                link = extracted.extraction
                extraction_summary = {
                    "status": "eligible",
                    "claim_id": link.claim_id,
                    "relation": link.relation,
                    "strength": link.strength,
                    "locator": link.locator,
                    "anchored_spans": list(link.anchored_spans),
                    "caveats": list(link.caveats),
                    "source_role": link.source_role,
                    "source_cluster_id": link.source_cluster_id,
                    "published_at": link.published_at,
                }
                extractions[claim_id] = dict(extraction_summary)
                # Keep the singular field as a backward-compatible summary of
                # the first eligible extraction for existing consumers.
                current_summary = source_record.get("extraction")
                if not (
                    isinstance(current_summary, Mapping)
                    and current_summary.get("status") == "eligible"
                ):
                    source_record["extraction"] = extraction_summary
                evidence_id = _evidence_id_for_record(run_id, source_record, selected_sources, rejected_sources)
                state = _add_extracted_evidence(state, evidence_id=evidence_id, link=link)
                cursor = replace(
                    cursor,
                    read_outcomes=tuple(
                        replace(outcome, evidence_id=evidence_id)
                        if outcome.candidate_id == candidate_id
                        else outcome
                        for outcome in cursor.read_outcomes
                    ),
                )
                checkpoint()

            cursor = replace(cursor, phase="gating")
            checkpoint(stage="gating")
            gate = evaluate_evidence_gate(state)
            state = _state_after_gate(state, gate)
            brief = _evidence_brief(state, gate, selected_sources)
            context[ACTIVE_RESEARCH_BRIEF_KEY] = brief
            cursor = replace(
                cursor,
                phase="completed" if gate.status == "pass" else "unavailable",
            )
            checkpoint()

            if gate.status == "pass":
                final_status = "completed"
                provider_status = "found"
                reason = "evidence_gate_pass"
                confidence = "high"
            elif gate.status == "partial":
                final_status = "partial"
                provider_status = "insufficient"
                reason = "evidence_budget_exhausted"
                confidence = "partial"
            else:
                final_status = "partial"
                provider_status = "insufficient"
                reason = "evidence_gap_open"
                confidence = "partial" if state.evidence else "none"
            return self.repository.complete(
                run_id,
                operation_id=operation_id,
                items=_eligible_items(selected_sources),
                source_block=_format_evidence_brief(brief),
                warnings=_dedupe(warnings),
                research_context=context,
                query_attempts=query_attempts,
                selected_sources=selected_sources,
                rejected_sources=rejected_sources,
                provider_status=provider_status,
                stop_reason=reason,
                answer_confidence=confidence,
                final_status=final_status,
            )
        except (ActiveResearchCancelled, CandidatePoolCancelled, ReadSchedulingCancelled):
            # B5-H1: persist the in-memory cursor so a cancel that lands after
            # on_model_finished records the cleared inflight marker and any
            # completed audit; the cancelled run is terminal and never resumes.
            try:
                checkpoint()
            except Exception:
                pass
            return self.repository.finish_cancel(run_id, operation_id=operation_id)
        except _HardBudgetReached:
            update_budget()
            _append_failure("hard_budget_reached", cursor.phase)
            checkpoint()
            gate = evaluate_evidence_gate(state)
            brief = _evidence_brief(state, gate, selected_sources)
            context[ACTIVE_RESEARCH_BRIEF_KEY] = brief
            checkpoint()
            return self.repository.complete(
                run_id,
                operation_id=operation_id,
                items=_eligible_items(selected_sources),
                source_block=_format_evidence_brief(brief),
                warnings=_dedupe(warnings),
                research_context=context,
                query_attempts=query_attempts,
                selected_sources=selected_sources,
                rejected_sources=rejected_sources,
                provider_status="insufficient",
                stop_reason="evidence_budget_exhausted",
                answer_confidence="partial" if state.evidence else "none",
                final_status="partial",
            )
        except Exception as exc:
            latest = self._required(run_id)
            if latest.status != "running" or latest.active_operation_id != operation_id:
                if raise_on_error:
                    raise
                return latest
            _append_failure(type(exc).__name__, cursor.phase)
            try:
                checkpoint()
            except Exception:
                pass
            if state.evidence:
                result = self.repository.complete(
                    run_id,
                    operation_id=operation_id,
                    items=_eligible_items(selected_sources),
                    source_block=_format_evidence_brief(
                        _evidence_brief(state, None, selected_sources)
                    ),
                    warnings=_dedupe([*warnings, "active research became unavailable"]),
                    research_context=context,
                    query_attempts=query_attempts,
                    selected_sources=selected_sources,
                    rejected_sources=rejected_sources,
                    provider_status="unavailable",
                    stop_reason="active_runtime_unavailable",
                    answer_confidence="partial",
                    final_status="partial",
                )
            else:
                result = self.repository.fail(
                    run_id,
                    "active research unavailable",
                    research_context=context,
                    query_attempts=query_attempts,
                    provider_status="unavailable",
                    stop_reason="active_runtime_unavailable",
                    operation_id=operation_id,
                )
            if raise_on_error:
                raise
            return result

    def _terminal_unavailable(
        self,
        run_id: str,
        *,
        operation_id: str,
        context: dict[str, Any],
        cursor: ResearchRuntimeCursor,
        state: ResearchState,
        query_attempts: list[dict[str, Any]],
        selected_sources: list[dict[str, Any]],
        rejected_sources: list[dict[str, Any]],
        warnings: list[str],
        reason: str,
    ) -> WebLookupRun:
        context = attach_runtime_cursor(context, replace(cursor, phase="unavailable"))
        context = attach_claim_engine_state(
            context,
            state,
            known_evidence_ids=tuple(
                ref.id for ref in _evidence_snapshot(run_id, selected_sources, rejected_sources).refs
            ),
        )
        return self.repository.fail(
            run_id,
            "active research unavailable",
            research_context=context,
            query_attempts=query_attempts,
            provider_status="unavailable",
            stop_reason=reason,
            operation_id=operation_id,
        )

    def _required(self, run_id: str) -> WebLookupRun:
        run = self.repository.get(run_id)
        if run is None:
            raise ValueError(f"WebLookupRun not found: {run_id}")
        return run


class _HardBudgetReached(Exception):
    pass


def _default_policy_check(context: Mapping[str, Any], purpose: str) -> bool:
    del purpose
    policy = context.get("external_data_policy")
    return isinstance(policy, Mapping) and policy.get("web_allowed") is True


def _ordered_claims(state: ResearchState) -> tuple[ResearchClaim, ...]:
    order = {"critical": 0, "major": 1, "context": 2}
    return tuple(sorted(state.claims, key=lambda claim: (order[claim.priority], claim.id)))


def _ordered_gaps(state: ResearchState) -> tuple[EvidenceGap, ...]:
    claim_priority = {claim.id: claim.priority for claim in state.claims}
    order = {"critical": 0, "major": 1, "context": 2}
    return tuple(
        sorted(
            (
                gap
                for gap in state.gaps
                if gap.state in {"open", "searching"}
                and claim_priority.get(gap.claim_id) != "context"
            ),
            key=lambda gap: (order[claim_priority[gap.claim_id]], gap.id),
        )
    )


def _runtime_query(query: PlannedGapQuery) -> RuntimePlannedQuery:
    return RuntimePlannedQuery(
        id=query.id,
        gap_id=query.gap_id,
        claim_id=query.claim_id,
        intent=query.intent.value,
        query=query.query,
        desired_source_role=query.desired_source_role,
    )


def _gap_query_batch(query: RuntimePlannedQuery) -> GapQueryBatch:
    planned = PlannedGapQuery(
        id=query.id,
        gap_id=query.gap_id,
        claim_id=query.claim_id,
        intent=GapSearchIntent(query.intent),
        query=query.query,
        desired_source_role=query.desired_source_role,
    )
    return GapQueryBatch(
        gap_id=query.gap_id,
        claim_id=query.claim_id,
        focused_surface=query.query,
        queries=(planned,),
    )


def _runtime_query_status(status: str) -> str:
    return status if status in {"ok", "empty", "unavailable"} else "unavailable"


def _merge_runtime_candidates(
    existing: tuple[RuntimeCandidate, ...],
    incoming: tuple[CandidatePoolItem, ...],
    *,
    max_candidates: int,
) -> tuple[RuntimeCandidate, ...]:
    merged = list(existing)
    by_url = {item.url: index for index, item in enumerate(merged)}
    for item in incoming:
        index = by_url.get(item.canonical_url)
        if index is not None:
            current = merged[index]
            merged[index] = replace(
                current,
                title=item.title if len(item.title) > len(current.title) else current.title,
                snippet=item.snippet if len(item.snippet) > len(current.snippet) else current.snippet,
                query_ids=tuple(dict.fromkeys((*current.query_ids, *item.query_ids))),
                intents=tuple(dict.fromkeys((*current.intents, *(intent.value for intent in item.intents)))),
                providers=tuple(dict.fromkeys((*current.providers, *item.providers))),
            )
            continue
        if len(merged) >= max_candidates:
            continue
        by_url[item.canonical_url] = len(merged)
        merged.append(
            RuntimeCandidate(
                id=item.id,
                url=item.canonical_url,
                title=item.title,
                snippet=item.snippet,
                source=item.source,
                published_at=item.published_at,
                query_ids=item.query_ids,
                intents=tuple(intent.value for intent in item.intents),
                providers=item.providers,
                first_seen_rank=item.first_seen_rank,
            )
        )
    return tuple(merged)


def _candidate_item(item: RuntimeCandidate) -> CandidatePoolItem:
    return CandidatePoolItem(
        id=item.id,
        canonical_url=item.url,
        url=item.url,
        title=item.title,
        snippet=item.snippet,
        source=item.source,
        published_at=item.published_at,
        query_ids=item.query_ids,
        intents=tuple(GapSearchIntent(value) for value in item.intents),
        providers=item.providers,
        first_seen_rank=item.first_seen_rank,
    )


def _candidates_for_claim(cursor: ResearchRuntimeCursor, claim_id: str) -> tuple[CandidatePoolItem, ...]:
    query_ids = {item.id for item in cursor.planned_queries if item.claim_id == claim_id}
    return tuple(
        _candidate_item(item)
        for item in cursor.candidates
        if query_ids.intersection(item.query_ids)
    )


def _assessment_store(context: dict[str, Any]) -> dict[str, Any]:
    raw = context.get(ACTIVE_RESEARCH_ASSESSMENTS_KEY)
    return {str(key): value for key, value in raw.items()} if isinstance(raw, Mapping) else {}


def _ranked_from_dict(raw: Mapping[str, Any]) -> RankedCandidate:
    candidate_raw = cast(Mapping[str, Any], raw["candidate"])
    assessment_raw = cast(Mapping[str, Any], raw["assessment"])
    candidate = CandidatePoolItem(
        id=str(candidate_raw["id"]),
        canonical_url=str(candidate_raw["canonical_url"]),
        url=str(candidate_raw["url"]),
        title=str(candidate_raw["title"]),
        snippet=str(candidate_raw.get("snippet") or ""),
        source=str(candidate_raw.get("source") or ""),
        published_at=str(candidate_raw.get("published_at") or ""),
        query_ids=tuple(str(item) for item in candidate_raw.get("query_ids", [])),
        intents=tuple(GapSearchIntent(str(item)) for item in candidate_raw.get("intents", [])),
        providers=tuple(str(item) for item in candidate_raw.get("providers", [])),
        first_seen_rank=int(candidate_raw.get("first_seen_rank") or 0),
    )
    assessment = CandidateSemanticAssessment(
        candidate_id=str(assessment_raw["candidate_id"]),
        relevance=cast(Any, str(assessment_raw["relevance"])),
        relevance_confidence=float(assessment_raw["relevance_confidence"]),
        source_role=str(assessment_raw["source_role"]),
        source_role_confidence=float(assessment_raw["source_role_confidence"]),
        cluster_id=str(assessment_raw["cluster_id"]),
        expected_gain_signals=tuple(str(item) for item in assessment_raw.get("expected_gain_signals", [])),
        freshness_score=float(assessment_raw.get("freshness_score") or 0.0),
        estimated_read_cost=float(assessment_raw.get("estimated_read_cost") or 1.0),
    )
    return RankedCandidate(
        candidate=candidate,
        assessment=assessment,
        rank=int(raw["rank"]),
        eligibility=cast(Any, str(raw["eligibility"])),
        reason_codes=tuple(str(item) for item in raw.get("reason_codes", [])),
        new_cluster=bool(raw.get("new_cluster")),
        expected_information_gain=int(raw.get("expected_information_gain") or 0),
    )


def _fair_read_plan(
    state: ResearchState,
    rankings: Mapping[str, tuple[RankedCandidate, ...]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return ``(physical_reads, extraction_targets)`` for the read stage.

    B5-H3: deduplicate reads, not claim-evidence bindings. Physical reads are
    unique per candidate and bounded by the shared read budget; extraction
    targets bind ``(candidate_id, claim_id)`` pairs so one physical read can
    serve evidence extraction for multiple claims. Read-budget exhaustion
    never blocks binding an already-planned candidate to another claim: the
    budget only limits new physical candidates, not extraction-only reuse.
    """
    claims = {claim.id: claim for claim in state.claims}
    physical: list[dict[str, str]] = []
    targets: list[dict[str, str]] = []
    physical_ids: set[str] = set()
    target_pairs: set[tuple[str, str]] = set()
    # H8: cluster diversity must span every wave of a claim, including
    # selections already bound through reusable candidates, so the fresh
    # acceptance loop skips clusters this claim already covers.
    claim_clusters: dict[str, set[str]] = {}
    reserve = ceil(state.budget.max_reads / 3)
    normal_limit = max(0, state.budget.max_reads - state.budget.reads_used - reserve)

    def _bind(candidate_id: str, claim_id: str, item: RankedCandidate) -> None:
        pair = (candidate_id, claim_id)
        if pair in target_pairs:
            return
        target_pairs.add(pair)
        claim_clusters.setdefault(claim_id, set()).add(item.assessment.cluster_id)
        targets.append(
            {
                "candidate_id": candidate_id,
                "claim_id": claim_id,
                "cluster_id": item.assessment.cluster_id,
                "source_role": item.assessment.source_role,
            }
        )

    def schedule(claim_ids: list[str], wave_size: int, *, allow_reserve: bool = False) -> None:
        for claim_id in claim_ids:
            ranked = tuple(
                item
                for item in rankings.get(claim_id, ())
                if (item.candidate.id, claim_id) not in target_pairs
            )
            if not ranked:
                continue
            # Reusable candidates are already in the physical plan: binding
            # them to this claim costs extraction work only, never read budget.
            reusable = tuple(item for item in ranked if item.candidate.id in physical_ids)
            fresh = tuple(item for item in ranked if item.candidate.id not in physical_ids)
            remaining = state.budget.max_reads - state.budget.reads_used - len(physical)
            budget_open = remaining > 0 and (allow_reserve or len(physical) < normal_limit)

            conflict_open = any("new_contradiction" in item.assessment.expected_gain_signals for item in ranked)
            policy = ReadSchedulerPolicy(
                critical_wave_size=wave_size,
                major_wave_size=wave_size,
                context_wave_size=0,
            )
            fresh_selected: list[str] = []
            by_id: dict[str, RankedCandidate] = {}
            if budget_open and fresh:
                budget = replace(state.budget, reads_used=state.budget.reads_used + len(physical))
                plan = plan_read_wave(
                    fresh,
                    claim=claims[claim_id],
                    budget=budget,
                    policy=policy,
                    conflict_open=conflict_open,
                    preserve_conflict_reserve=not allow_reserve,
                )
                by_id = {item.candidate.id: item for item in fresh}
                fresh_selected = [
                    candidate_id
                    for candidate_id in plan.selected_candidate_ids
                    if candidate_id in by_id
                ]

            # Reusable bindings first (rank order, cluster-diverse within the
            # claim across waves); remaining wave slots go to new physical
            # reads, skipping clusters this claim already covers (H8) without
            # wasting slots on the skipped entries.
            slots = wave_size
            for item in reusable:
                if slots <= 0:
                    break
                if item.eligibility == "rejected":
                    continue
                if item.assessment.cluster_id in claim_clusters.get(claim_id, set()):
                    continue
                _bind(item.candidate.id, claim_id, item)
                slots -= 1
            for candidate_id in fresh_selected:
                if slots <= 0:
                    break
                item = by_id[candidate_id]
                if item.assessment.cluster_id in claim_clusters.get(claim_id, set()):
                    continue
                _bind(candidate_id, claim_id, item)
                if candidate_id not in physical_ids:
                    physical_ids.add(candidate_id)
                    physical.append(
                        {
                            "candidate_id": candidate_id,
                            "claim_id": claim_id,
                            "cluster_id": item.assessment.cluster_id,
                            "source_role": item.assessment.source_role,
                        }
                    )
                slots -= 1

    critical = [claim.id for claim in _ordered_claims(state) if claim.priority == "critical"]
    major = [claim.id for claim in _ordered_claims(state) if claim.priority == "major"]
    schedule(critical, 1)
    schedule(critical, 2)
    schedule(major, 1)
    conflict_claims = [
        claim_id
        for claim_id in critical
        if any(
            "new_contradiction" in item.assessment.expected_gain_signals
            for item in rankings.get(claim_id, ())
        )
    ]
    schedule(conflict_claims, reserve, allow_reserve=True)
    read_cap = max(0, state.budget.max_reads - state.budget.reads_used)
    return physical[:read_cap], targets


def _read_plan_entries(raw: Any, keys: tuple[str, ...]) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    return [
        {key: str(item[key]) for key in keys}
        for item in raw
        if isinstance(item, Mapping) and all(key in item for key in keys)
    ]


def _load_read_plan(context: Mapping[str, Any]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Load the persisted read plan as ``(physical_reads, extraction_targets)``.

    v2 persists both lists explicitly; the v1 format stored a single list of
    claim-bound entries, which is converted so in-flight runs keep resuming.
    """
    raw = context.get(ACTIVE_RESEARCH_READ_PLAN_KEY)
    if isinstance(raw, Mapping):
        physical_keys = ("candidate_id", "claim_id", "cluster_id", "source_role")
        return (
            _read_plan_entries(raw.get("physical_reads"), physical_keys),
            _read_plan_entries(raw.get("extraction_targets"), physical_keys),
        )
    if isinstance(raw, list):
        physical_keys = ("candidate_id", "claim_id", "cluster_id", "source_role")
        entries = _read_plan_entries(raw, physical_keys)
        physical: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in entries:
            if item["candidate_id"] not in seen:
                seen.add(item["candidate_id"])
                physical.append(item)
        return physical, entries
    return [], []


def _candidate_by_id(cursor: ResearchRuntimeCursor, candidate_id: str) -> CandidatePoolItem:
    for item in cursor.candidates:
        if item.id == candidate_id:
            return _candidate_item(item)
    raise ValueError(f"unknown runtime candidate: {candidate_id}")


def _source_record(
    candidate: CandidatePoolItem,
    plan: Mapping[str, str],
    *,
    raw_read: Mapping[str, Any],
) -> dict[str, Any]:
    read = {
        "ok": raw_read.get("ok") is True,
        "status": str(raw_read.get("status") or "failed"),
        "url": candidate.url,
        "title": _bounded_text(raw_read.get("title") or candidate.title, 500),
        "content": str(raw_read.get("content") or "")[:6000],
        "error": _bounded_text(raw_read.get("error"), 200),
    }
    return {
        "candidate_id": candidate.id,
        "item": {
            "title": candidate.title,
            "url": candidate.url,
            "source": candidate.source,
            "published_at": candidate.published_at,
        },
        "assessment": {
            "title": candidate.title,
            "url": candidate.url,
            "selected": True,
            "worth_reading": True,
            "source_role": plan["source_role"],
            "source_cluster_id": plan["cluster_id"],
            "claim_id": plan["claim_id"],
            "providers": list(candidate.providers),
        },
        "read": read,
        "read_status": read["status"],
        "evidence_state": "new" if read["status"] == "read" else "invalid_or_rejected",
    }


def _upsert_source(records: list[dict[str, Any]], record: dict[str, Any]) -> None:
    candidate_id = record.get("candidate_id")
    for index, current in enumerate(records):
        if current.get("candidate_id") == candidate_id:
            records[index] = record
            return
    records.append(record)


def _source_by_candidate(records: list[dict[str, Any]], candidate_id: str) -> dict[str, Any] | None:
    return next((item for item in records if item.get("candidate_id") == candidate_id), None)


def _read_status(record: Mapping[str, Any]) -> str:
    read = record.get("read")
    return str(read.get("status") or "") if isinstance(read, Mapping) else ""


def _evidence_snapshot(
    run_id: str,
    selected_sources: list[dict[str, Any]],
    rejected_sources: list[dict[str, Any]],
):
    return build_evidence_snapshot(
        rag={
            "research_sources": {
                "run_id": run_id,
                "provider_status": "found",
                "source_truth_version": 2,
                "selected_sources": selected_sources,
                "rejected_sources": rejected_sources,
            }
        }
    )


def _evidence_id_for_record(
    run_id: str,
    record: Mapping[str, Any],
    selected_sources: list[dict[str, Any]],
    rejected_sources: list[dict[str, Any]],
) -> str:
    item = record.get("item")
    url = str(item.get("url") or "") if isinstance(item, Mapping) else ""
    for ref in _evidence_snapshot(run_id, selected_sources, rejected_sources).refs:
        if ref.url == url and ref.lifecycle_status == "selected":
            return ref.id
    raise ValueError("server-owned evidence identity unavailable")


def _add_extracted_evidence(state: ResearchState, *, evidence_id: str, link: Any) -> ResearchState:
    evidence = {item.evidence_id: item for item in state.evidence}
    evidence[evidence_id] = ResearchEvidence(
        evidence_id=evidence_id,
        locator=link.locator,
        anchored_spans=link.anchored_spans,
        lifecycle_status="read",
        extraction_status="eligible",
        published_at=link.published_at,
    )
    links = {
        (item.claim_id, item.evidence_id, item.relation): item
        for item in state.evidence_links
    }
    key = (link.claim_id, evidence_id, link.relation)
    links[key] = ResearchClaimEvidenceLink(
        link=ClaimEvidenceLinkV1(
            claim_id=link.claim_id,
            evidence_id=evidence_id,
            support_type=link.relation,
            confidence=link.strength,
        ),
        source_role=link.source_role,
        source_cluster_id=link.source_cluster_id,
        locator=link.locator,
        caveats=link.caveats,
    )
    clusters: dict[str, EvidenceCluster] = {item.id: item for item in state.source_clusters}
    current = clusters.get(link.source_cluster_id)
    clusters[link.source_cluster_id] = EvidenceCluster(
        id=link.source_cluster_id,
        evidence_ids=tuple(dict.fromkeys((*((current.evidence_ids) if current else ()), evidence_id))),
        source_role=link.source_role,
        independence_key=(current.independence_key if current else link.source_cluster_id),
    )
    return build_research_state(
        mode=state.mode,
        questions=state.questions,
        claims=state.claims,
        evidence=evidence.values(),
        evidence_links=links.values(),
        source_clusters=clusters.values(),
        gaps=state.gaps,
        conflict_gaps=state.conflict_gaps,
        budget=state.budget,
        trace=state.trace,
        brief=state.brief,
        reference_date=state.reference_date,
        known_evidence_ids=evidence,
    )


def _state_after_gate(state: ResearchState, gate: EvidenceGateResult) -> ResearchState:
    open_claims = set(gate.open_critical_claims)
    claims = tuple(
        replace(
            claim,
            state=(
                "contested"
                if any(conflict.claim_id == claim.id for conflict in gate.conflicts)
                else "unresolved"
                if claim.id in open_claims
                else "satisfied"
                if claim.priority == "critical"
                else claim.state
            ),
        )
        for claim in state.claims
    )
    gaps = tuple(
        replace(gap, state="open" if gap.claim_id in open_claims else "resolved")
        for gap in state.gaps
    )
    brief = ResearchBrief(
        claim_ids=tuple(claim.id for claim in claims),
        unresolved_claim_ids=tuple(sorted(open_claims)),
        conflict_gap_ids=tuple(item.id for item in gate.conflicts),
        outline=("eligible_evidence", "claim_links", "conflicts", "open_gaps", "gate"),
    )
    known = tuple(item.evidence_id for item in state.evidence)
    return build_research_state(
        mode=state.mode,
        questions=state.questions,
        claims=claims,
        evidence=state.evidence,
        evidence_links=state.evidence_links,
        source_clusters=state.source_clusters,
        gaps=gaps,
        conflict_gaps=gate.conflicts,
        budget=state.budget,
        trace=state.trace,
        brief=brief,
        reference_date=state.reference_date,
        known_evidence_ids=known,
    )


def _evidence_brief(
    state: ResearchState,
    gate: EvidenceGateResult | None,
    selected_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    records_by_id = {
        str(record.get("candidate_id")): record for record in selected_sources
    }
    evidence_rows: list[dict[str, Any]] = []
    for link in state.evidence_links:
        evidence = next((item for item in state.evidence if item.evidence_id == link.evidence_id), None)
        if evidence is None or evidence.extraction_status != "eligible":
            continue
        record = next(
            (
                item
                for item in records_by_id.values()
                if (
                    isinstance(item.get("extractions"), Mapping)
                    and isinstance(item["extractions"].get(link.claim_id), Mapping)
                    and str(item["extractions"][link.claim_id].get("locator") or "") == link.locator
                )
                or (
                    isinstance(item.get("extraction"), Mapping)
                    and item["extraction"].get("claim_id") == link.claim_id
                    and item["extraction"].get("locator") == link.locator
                )
            ),
            {},
        )
        item = record.get("item") if isinstance(record, Mapping) else {}
        # H7: ResearchEvidence is the source-level identity, so its
        # locator/spans are whatever the last extraction wrote; claim-specific
        # anchors live in record["extractions"][claim_id] and must win when
        # one physical read serves multiple claims.
        claim_anchor: Mapping[str, Any] | None = None
        if isinstance(record, Mapping):
            extractions_map = record.get("extractions")
            if isinstance(extractions_map, Mapping):
                detail = extractions_map.get(link.claim_id)
                if isinstance(detail, Mapping):
                    claim_anchor = detail
        anchors_source = claim_anchor if claim_anchor is not None else {}
        evidence_rows.append(
            {
                "evidence_id": link.evidence_id,
                "claim_id": link.claim_id,
                "relation": link.relation,
                "strength": link.strength,
                "source_role": link.source_role,
                "source_cluster_id": link.source_cluster_id,
                "title": str(item.get("title") or "") if isinstance(item, Mapping) else "",
                "url": str(item.get("url") or "") if isinstance(item, Mapping) else "",
                "locator": str(
                    anchors_source.get("locator") or link.locator or ""
                ),
                "anchored_spans": list(
                    anchors_source.get("anchored_spans") or evidence.anchored_spans
                ),
                "published_at": evidence.published_at,
                "caveats": list(
                    anchors_source.get("caveats") or link.caveats
                ),
            }
        )
    return {
        "schema_version": "research-evidence-brief-v1",
        "gate_status": gate.status if gate else "unavailable",
        "gate_reasons": list(gate.reasons) if gate else ["active_runtime_unavailable"],
        # H5: the conclusion constraint is a first-class brief field so
        # downstream consumers never present an unqualified strong conclusion
        # unless the Evidence Gate actually passed.
        "conditional_wording_required": (gate is None or gate.status != "pass"),
        "eligible_evidence": evidence_rows,
        "claim_links": [item.to_dict() for item in state.evidence_links if item.evidence_id in {row["evidence_id"] for row in evidence_rows}],
        "unresolved_conflicts": [item.to_dict() for item in (gate.conflicts if gate else state.conflict_gaps)],
        "open_critical_claim_ids": list(gate.open_critical_claims) if gate else [claim.id for claim in state.claims if claim.priority == "critical"],
        "open_gap_ids": list(gate.gap_ids) if gate else [gap.id for gap in state.gaps if gap.state in {"open", "searching"}],
        "budget": state.budget.to_dict(),
        "answer_instruction": (
            "Use only eligible evidence. State unresolved gaps and conflicts. "
            "When gate_status is not pass, use conditional language and do not present a complete conclusion."
        ),
    }


def _format_evidence_brief(brief: Mapping[str, Any]) -> str:
    lines = [
        "研究证据简报（仅可使用下列已读取并通过提取校验的证据）",
        f"Evidence Gate: {brief.get('gate_status', 'unavailable')}",
    ]
    for row in brief.get("eligible_evidence", []):
        if not isinstance(row, Mapping):
            continue
        lines.append(
            f"- [{row.get('relation')}] claim={row.get('claim_id')} "
            f"source={row.get('title') or row.get('url')} "
            f"cluster={row.get('source_cluster_id')} strength={row.get('strength')}"
        )
        lines.append(f"  anchor: {row.get('locator')}")
        if row.get("url"):
            lines.append(f"  url: {row.get('url')}")
    open_claims = brief.get("open_critical_claim_ids") or []
    conflicts = brief.get("unresolved_conflicts") or []
    if open_claims:
        lines.append("未闭合关键结论：" + ", ".join(str(item) for item in open_claims))
    if conflicts:
        lines.append("仍有未解决冲突；回答必须并列呈现冲突证据。")
    if brief.get("conditional_wording_required") is True:
        lines.append(
            "结论约束：研究尚未通过完整证据核验；只能使用条件化措辞，不得输出无保留强结论。"
        )
    lines.append(str(brief.get("answer_instruction") or ""))
    return "\n".join(lines)[:20000]


def _eligible_items(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(record.get("item") or {})
        for record in records
        if isinstance(record.get("extraction"), Mapping)
        and record["extraction"].get("status") == "eligible"
    ]


def _update_metrics(
    context: dict[str, Any],
    state: ResearchState,
    cursor: ResearchRuntimeCursor,
) -> None:
    context[ACTIVE_RESEARCH_METRICS_KEY] = {
        **(
            dict(context.get(ACTIVE_RESEARCH_METRICS_KEY) or {})
            if isinstance(context.get(ACTIVE_RESEARCH_METRICS_KEY), Mapping)
            else {}
        ),
        "candidate_count": len(cursor.candidates),
        "read_count": sum(item.status == "success" for item in cursor.read_outcomes),
        "cluster_count": len(state.source_clusters),
        "open_critical_gap_count": sum(
            gap.state in {"open", "searching"}
            and any(claim.id == gap.claim_id and claim.priority == "critical" for claim in state.claims)
            for gap in state.gaps
        ),
        "phase": cursor.phase,
    }


def _attempt_number(cursor: ResearchRuntimeCursor, item_id: str) -> int:
    interrupted = sum(
        failure.code == "interrupted_unknown" and item_id in failure.item_id
        for failure in cursor.failures
    )
    return min(2, 1 + interrupted)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(value)[:500] for value in values if str(value).strip()))


def _bounded_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


__all__ = [
    "ACTIVE_RESEARCH_ASSESSMENTS_KEY",
    "ACTIVE_RESEARCH_BRIEF_KEY",
    "ACTIVE_RESEARCH_METRICS_KEY",
    "ACTIVE_RESEARCH_POLICY_AUDITS_KEY",
    "ACTIVE_RESEARCH_READ_PLAN_KEY",
    "ActiveResearchCancelled",
    "ActiveResearchRuntimeExecutor",
]
