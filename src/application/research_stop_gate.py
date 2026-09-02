"""ResearchStopGate: the single owner of active-research termination truth.

P1-C batch 3: centralize research stop truth without changing the frozen RQCE
behavior or budgets. Every evidence/budget/unavailable terminal decision of
the active executor funnels through ``ResearchStopGate.evaluate``; cooperative
user cancellation remains owned by the existing operation-scoped repository
lifecycle. The gate is a pure, deterministic function of durable signals, so a
crash/resume re-evaluates the same decision.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.web.research.failure_contracts import (
    ResearchStopReason,
    require_research_stop_reason,
)

ResearchStopDecisionKind = Literal["continue", "success", "partial", "unavailable"]
ResearchStopReasonOrEmpty = ResearchStopReason | Literal[""]


@dataclass(frozen=True)
class ResearchStopDecision:
    """Canonical terminal mapping produced by the gate.

    decision mirrors the product-level outcome:
      - "continue"    wave advances, no terminal stop (reason == "")
      - "success"     evidence gate passed
      - "partial"     bounded finish with whatever evidence exists
      - "unavailable" failed without a usable result
    reason is the canonical stop reason persisted on the run
    (e.g. evidence_gate_pass, evidence_budget_exhausted). The remaining
    fields provide the normal settlement mapping. Exception paths may preserve
    their existing evidence-shaped complete/fail envelope, but the canonical
    reason still comes only from this gate.
    """

    decision: ResearchStopDecisionKind
    reason: ResearchStopReasonOrEmpty
    final_status: str = ""
    provider_status: str = ""
    answer_confidence: str = ""


@dataclass(frozen=True)
class ResearchStopSignal:
    """Durable inputs to the stop decision.

    The executor derives each signal from durable truth only (the checkpointed
    cursor, the persisted research state and the shared elapsed clock), so a
    resumed run re-evaluates the same decision after a crash.  The unavailable
    input intentionally remains ``str`` because callers may load compatibility
    state; ``evaluate`` is the writer boundary that validates any non-empty
    value before it can become a new durable stop reason.
    """

    gate_pass: bool
    hard_budget_exhausted: bool
    has_actionable_gaps: bool
    all_actionable_saturated: bool
    wave_limit_reached: bool
    has_evidence: bool
    unavailable_reason: str = ""
    unapplied_steering_blocks_completion: bool = False


class ResearchStopGate:
    """Pure decision table for active research termination.

    Priority, frozen in P1-C batch 2 (highest first) and locked:
      1. unavailable   - explicit failure (policy block, plan unavailable,
                         active_runtime_unavailable) - never competes with a
                         normal settlement
      2. gate pass     - success / evidence_gate_pass; suppressed when an
                         unapplied steering (marked late against an exhausted
                         hard/wave budget) invalidates completion computed
                         from the pre-steering graph
      3. hard budget   - partial / evidence_budget_exhausted - must not be
                         masked by saturation or the wave ceiling
      4. no actionable - partial / evidence_gap_open
      5. saturated     - partial / evidence_saturated
      6. wave ceiling  - partial / wave_limit_exhausted - never claimed as
                         saturation
      7. otherwise     - continue
    """

    @staticmethod
    def evaluate(signal: ResearchStopSignal) -> ResearchStopDecision:
        if signal.unavailable_reason:
            unavailable_reason = require_research_stop_reason(
                signal.unavailable_reason
            )
            return ResearchStopDecision(
                decision="unavailable",
                reason=unavailable_reason,
                final_status="failed",
                provider_status="unavailable",
            )
        effective_gate_pass = (
            signal.gate_pass
            and not signal.unapplied_steering_blocks_completion
        )
        if effective_gate_pass:
            return ResearchStopDecision(
                decision="success",
                reason="evidence_gate_pass",
                final_status="completed",
                provider_status="found",
                answer_confidence="high",
            )
        partial_confidence = "partial" if signal.has_evidence else "none"
        if signal.hard_budget_exhausted:
            # Frozen settle semantics: the exhausted shared budget always
            # yields "partial" confidence regardless of accumulated evidence
            # (settle L317-325 of 533b60c7).
            return ResearchStopDecision(
                decision="partial",
                reason="evidence_budget_exhausted",
                final_status="partial",
                provider_status="insufficient",
                answer_confidence="partial",
            )
        if not signal.has_actionable_gaps:
            return ResearchStopDecision(
                decision="partial",
                reason="evidence_gap_open",
                final_status="partial",
                provider_status="insufficient",
                answer_confidence=partial_confidence,
            )
        if signal.all_actionable_saturated:
            return ResearchStopDecision(
                decision="partial",
                reason="evidence_saturated",
                final_status="partial",
                provider_status="insufficient",
                answer_confidence=partial_confidence,
            )
        if signal.wave_limit_reached:
            return ResearchStopDecision(
                decision="partial",
                reason="wave_limit_exhausted",
                final_status="partial",
                provider_status="insufficient",
                answer_confidence=partial_confidence,
            )
        return ResearchStopDecision(decision="continue", reason="")


__all__ = [
    "ResearchStopDecision",
    "ResearchStopDecisionKind",
    "ResearchStopGate",
    "ResearchStopReasonOrEmpty",
    "ResearchStopSignal",
]
