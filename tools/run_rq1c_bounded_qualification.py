"""Strict bounded entrypoint for the RQ1-C live qualification.

The implementation module contains the previously reviewed qualification runner.
This wrapper adds the two operational bounds that must be enforced *before* an
answer-stage provider call leaves the process:

* the whole case may start at most six physical model calls; and
* generation/binding provider timeouts are clamped to the remaining 60-second
  case deadline.

The active ResearchRun already enforces its own hard deadline and records model
attempts before dispatch.  The wrapper consumes that durable research truth and
uses the same budget for the production generation + claim-binding stages.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from typing import Any, Mapping

from src.llm_client import _resolve_timeout, chat as _production_chat
from tools import run_rq1c_bounded_qualification_impl as _impl
from tools.rq1c_git_identity import exact_checkout_git_sha

MAX_MODEL_CALLS = 6
HARD_TIMEOUT_SECONDS = 60.0

# Re-export the stable helper surface used by tests and companion tooling.
_evidence_rows = _impl._evidence_rows
_load_manifest = _impl._load_manifest
_observed_read_count = _impl._observed_read_count
_provider_audit = _impl._provider_audit
_source_rows = _impl._source_rows
_unavailable_answer_surface = _impl._unavailable_answer_surface
_answer_stage_model_calls = _impl._answer_stage_model_calls
_production_answer_surface = _impl._production_answer_surface
_production_chat_command = _impl._production_chat_command
_active_context = _impl._active_context
def _git_sha() -> str:
    return exact_checkout_git_sha(_impl.REPO_ROOT)


# The implementation resolves git identity through its module global at call time.
_impl._git_sha = _git_sha

_ORIGINAL_RUN_CASE = _impl._run_case


class QualificationModelBudgetExhausted(RuntimeError):
    """Raised before dispatch when the six-call case budget is exhausted."""


class QualificationHardDeadlineReached(TimeoutError):
    """Raised before dispatch when no case-level wall-clock budget remains."""


@dataclass
class _AnswerStageBudget:
    """One shared physical-call/deadline ledger for a qualification case."""

    started_at: float
    research_model_calls: int = 0
    max_model_calls: int = MAX_MODEL_CALLS
    hard_timeout_seconds: float = HARD_TIMEOUT_SECONDS
    required_answer_calls: int = 1
    phase_calls: dict[str, int] = field(
        default_factory=lambda: {
            "answer_generation": 0,
            "answer_claim_binding": 0,
            "other": 0,
        }
    )
    rejection_reasons: list[str] = field(default_factory=list)

    @property
    def answer_calls_started(self) -> int:
        return sum(self.phase_calls.values())

    @property
    def total_model_calls_started(self) -> int:
        return max(0, int(self.research_model_calls)) + self.answer_calls_started

    def remaining_seconds(self) -> float:
        elapsed = max(0.0, time.monotonic() - self.started_at)
        return max(0.0, self.hard_timeout_seconds - elapsed)

    def set_research_truth(self, completed: Any) -> None:
        context = getattr(completed, "research_context", None)
        context = context if isinstance(context, Mapping) else {}
        runtime = context.get("claim_engine_runtime")
        runtime = runtime if isinstance(runtime, Mapping) else {}
        model_calls = runtime.get("model_calls")
        self.research_model_calls = (
            len(model_calls) if isinstance(model_calls, list) else 0
        )
        # A successful publication needs one answer generation.  When strong
        # binding rows exist it also needs one physical binder call.  Reject an
        # impossible pipeline before spending the last slot on generation.
        self.required_answer_calls = 1 + int(bool(_impl.research_binding_rows(completed)))

    def _phase_name(self, task_name: Any) -> str:
        name = str(task_name or "").strip()
        if name == "single_chat":
            return "answer_generation"
        if name == "answer_claim_binding":
            return "answer_claim_binding"
        return "other"

    def _reject(self, reason: str, exc_type: type[Exception]) -> None:
        self.rejection_reasons.append(reason)
        raise exc_type(reason)

    def chat(self, messages: list[dict], **kwargs: Any) -> str:
        """Dispatch production chat only after reserving shared case budget."""

        phase = self._phase_name(kwargs.get("task_name"))
        if (
            self.answer_calls_started == 0
            and self.research_model_calls + self.required_answer_calls
            > self.max_model_calls
        ):
            self._reject(
                "answer_pipeline_model_call_capacity_exhausted",
                QualificationModelBudgetExhausted,
            )
        if self.total_model_calls_started >= self.max_model_calls:
            self._reject(
                "model_call_budget_exhausted_pre_call",
                QualificationModelBudgetExhausted,
            )

        remaining = self.remaining_seconds()
        if remaining <= 0:
            self._reject(
                "hard_timeout_exhausted_pre_call",
                QualificationHardDeadlineReached,
            )

        normal_timeout = float(
            _resolve_timeout(
                kwargs.get("timeout"),
                kwargs.get("task_name"),
                kwargs.get("model_profile"),
                kwargs.get("provider_profile"),
            )
        )
        bounded_timeout = min(normal_timeout, remaining)
        if bounded_timeout <= 0:
            self._reject(
                "hard_timeout_exhausted_pre_call",
                QualificationHardDeadlineReached,
            )

        # Reservation is the physical-call boundary: after this increment the
        # production client is invoked exactly once with retries already forced
        # to zero by ChatService.
        self.phase_calls[phase] = self.phase_calls.get(phase, 0) + 1
        forwarded = dict(kwargs)
        forwarded["timeout"] = bounded_timeout
        return _production_chat(messages, **forwarded)


class _ResearchBudgetProxy:
    """Delegate ResearchRun execution and load its durable call truth."""

    def __init__(self, delegate: Any, budget: _AnswerStageBudget) -> None:
        self._delegate = delegate
        self._budget = budget

    def __getattr__(self, name: str) -> Any:
        return getattr(self._delegate, name)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        completed = self._delegate.execute(*args, **kwargs)
        self._budget.set_research_truth(completed)
        return completed


def _bounded_chat_service(
    chat_service: Any, budget: _AnswerStageBudget
) -> Any:
    """Clone production dependencies while replacing only the network chat fn."""

    bounded = _impl._build_chat_service(chat_service.repository.database)
    bounded.dependencies = replace(bounded.dependencies, chat=budget.chat)
    return bounded


def _run_case(
    *,
    case: Mapping[str, str],
    repository: Any,
    service: Any,
    chat_service: Any,
    reference_date: str,
) -> dict[str, Any]:
    """Run the reviewed implementation with a pre-dispatch shared budget."""

    budget = _AnswerStageBudget(started_at=time.monotonic())
    guarded_research = _ResearchBudgetProxy(service, budget)
    bounded_chat = _bounded_chat_service(chat_service, budget)
    record = _ORIGINAL_RUN_CASE(
        case=case,
        repository=repository,
        service=guarded_research,
        chat_service=bounded_chat,
        reference_date=reference_date,
    )

    # The production answer audit remains the publication truth.  Budget truth
    # uses this wrapper's actual provider-dispatch reservations so a binder
    # logical attempt that was rejected before network egress is never counted
    # as a physical call.
    observed = record.get("budget_observed")
    if isinstance(observed, dict):
        observed["research_model_call_count"] = budget.research_model_calls
        observed["answer_generation_model_call_count"] = budget.phase_calls[
            "answer_generation"
        ]
        observed["answer_binding_model_call_count"] = budget.phase_calls[
            "answer_claim_binding"
        ]
        observed["unclassified_answer_model_call_count"] = budget.phase_calls["other"]
        observed["model_call_count"] = budget.total_model_calls_started

    elapsed = round(max(0.0, time.monotonic() - budget.started_at), 3)
    record["elapsed_seconds"] = elapsed
    if isinstance(observed, dict):
        observed["elapsed_seconds"] = elapsed

    violations = record.get("budget_contract_violations")
    if not isinstance(violations, list):
        violations = []
        record["budget_contract_violations"] = violations
    violations[:] = [
        str(item)
        for item in violations
        if item
        not in {
            "answer_stage_model_call_count_unavailable",
            "model_call_budget_exceeded",
        }
    ]
    for reason in budget.rejection_reasons:
        if reason not in violations:
            violations.append(reason)
    if budget.total_model_calls_started > budget.max_model_calls:
        if "model_call_budget_exceeded" not in violations:
            violations.append("model_call_budget_exceeded")
    if elapsed > budget.hard_timeout_seconds:
        if "hard_timeout_exceeded" not in violations:
            violations.append("hard_timeout_exceeded")
    return record


# Patch only the per-case hook used by the reviewed implementation.
_impl._run_case = _run_case

run_qualification = _impl.run_qualification
_parser = _impl._parser


def main() -> int:
    return _impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
