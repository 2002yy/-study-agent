"""Characterization tests for the frozen stop truth (P1-C batch 3).

Every row mirrors the exact terminal mapping of the pre-refactor settle
chain in active_research_runtime.py (P1-C batch 2, merged as 533b60c7),
so the gate is proven equivalent to the old behavior before any executor
branch is wired through it.
"""

from __future__ import annotations

import pytest

from src.application.research_stop_gate import (
    ResearchStopDecision,
    ResearchStopGate,
    ResearchStopSignal,
)


def _signal(
    *,
    gate_pass: bool = False,
    hard_budget_exhausted: bool = False,
    has_actionable_gaps: bool = True,
    all_actionable_saturated: bool = False,
    wave_limit_reached: bool = False,
    has_evidence: bool = False,
    unavailable_reason: str = "",
) -> ResearchStopSignal:
    return ResearchStopSignal(
        gate_pass=gate_pass,
        hard_budget_exhausted=hard_budget_exhausted,
        has_actionable_gaps=has_actionable_gaps,
        all_actionable_saturated=all_actionable_saturated,
        wave_limit_reached=wave_limit_reached,
        has_evidence=has_evidence,
        unavailable_reason=unavailable_reason,
    )


def _expect(
    decision: str,
    reason: str,
    *,
    final_status: str = "",
    provider_status: str = "",
    answer_confidence: str = "",
) -> ResearchStopDecision:
    return ResearchStopDecision(
        decision=decision,
        reason=reason,
        final_status=final_status,
        provider_status=provider_status,
        answer_confidence=answer_confidence,
    )


# One row per frozen settle branch. The `extra` flags assert the priority
# lock: a lower-priority truth must never override a higher one, exactly as
# the old if/elif chain resolved (settle L308-350 of 533b60c7).
GATE_TABLE = [
    # gate pass -> success, regardless of anything else
    (
        _signal(gate_pass=True),
        _expect("success", "evidence_gate_pass",
                final_status="completed", provider_status="found",
                answer_confidence="high"),
    ),
    (
        _signal(gate_pass=True, hard_budget_exhausted=True),
        _expect("success", "evidence_gate_pass",
                final_status="completed", provider_status="found",
                answer_confidence="high"),
    ),
    # hard budget -> partial, even when saturation and the wave ceiling
    # are also true (the exhausted shared budget is the terminal truth);
    # frozen confidence is always "partial" (settle L317-325 of 533b60c7)
    (
        _signal(hard_budget_exhausted=True),
        _expect("partial", "evidence_budget_exhausted",
                final_status="partial", provider_status="insufficient",
                answer_confidence="partial"),
    ),
    (
        _signal(hard_budget_exhausted=True, has_evidence=True),
        _expect("partial", "evidence_budget_exhausted",
                final_status="partial", provider_status="insufficient",
                answer_confidence="partial"),
    ),
    (
        _signal(hard_budget_exhausted=True, all_actionable_saturated=True,
                wave_limit_reached=True, has_evidence=True),
        _expect("partial", "evidence_budget_exhausted",
                final_status="partial", provider_status="insufficient",
                answer_confidence="partial"),
    ),
    # no actionable gaps -> truthful terminal
    (
        _signal(has_actionable_gaps=False),
        _expect("partial", "evidence_gap_open",
                final_status="partial", provider_status="insufficient",
                answer_confidence="none"),
    ),
    (
        _signal(has_actionable_gaps=False, has_evidence=True),
        _expect("partial", "evidence_gap_open",
                final_status="partial", provider_status="insufficient",
                answer_confidence="partial"),
    ),
    # actionable gaps saturated -> partial; beats the wave ceiling
    (
        _signal(all_actionable_saturated=True),
        _expect("partial", "evidence_saturated",
                final_status="partial", provider_status="insufficient",
                answer_confidence="none"),
    ),
    (
        _signal(all_actionable_saturated=True, wave_limit_reached=True,
                has_evidence=True),
        _expect("partial", "evidence_saturated",
                final_status="partial", provider_status="insufficient",
                answer_confidence="partial"),
    ),
    # wave ceiling -> partial; never claimed as saturation
    (
        _signal(wave_limit_reached=True),
        _expect("partial", "wave_limit_exhausted",
                final_status="partial", provider_status="insufficient",
                answer_confidence="none"),
    ),
    (
        _signal(wave_limit_reached=True, has_evidence=True),
        _expect("partial", "wave_limit_exhausted",
                final_status="partial", provider_status="insufficient",
                answer_confidence="partial"),
    ),
    # otherwise -> continue, no stop reason
    (
        _signal(),
        _expect("continue", ""),
    ),
    (
        _signal(has_evidence=True),
        _expect("continue", ""),
    ),
]


@pytest.mark.parametrize(("signal", "expected"), GATE_TABLE)
def test_stop_gate_matches_frozen_settle_semantics(
    signal: ResearchStopSignal,
    expected: ResearchStopDecision,
) -> None:
    assert ResearchStopGate.evaluate(signal) == expected


def test_unavailable_reason_is_strongest_truth() -> None:
    assert ResearchStopGate.evaluate(
        _signal(
            unavailable_reason="claim_plan_unavailable",
            gate_pass=True,
            hard_budget_exhausted=True,
            has_evidence=True,
        )
    ) == _expect(
        "unavailable", "claim_plan_unavailable",
        final_status="failed", provider_status="unavailable",
    )


def test_unavailable_without_reason_is_not_invented() -> None:
    assert ResearchStopGate.evaluate(
        _signal(unavailable_reason="")
    ) == _expect("continue", "")


def test_stop_gate_is_deterministic_for_durable_truth() -> None:
    # A crash/resume re-derives the same durable signals (checkpointed
    # cursor + persisted state + shared clock), so the gate must map one
    # signal to exactly one canonical decision - never two.
    signal = _signal(
        all_actionable_saturated=True,
        wave_limit_reached=True,
        has_evidence=True,
    )
    first = ResearchStopGate.evaluate(signal)
    second = ResearchStopGate.evaluate(signal)
    assert first == second
    assert first.reason == "evidence_saturated"
    assert first.reason != "wave_limit_exhausted"
    assert first.decision == "partial"


def test_same_state_yields_exactly_one_canonical_reason() -> None:
    reasons: set[str] = set()
    for budget in (False, True):
        for has_gaps in (False, True):
            for saturated in (False, True):
                for wave in (False, True):
                    for evidence in (False, True):
                        reasons.add(
                            ResearchStopGate.evaluate(
                                _signal(
                                    hard_budget_exhausted=budget,
                                    has_actionable_gaps=has_gaps,
                                    all_actionable_saturated=saturated,
                                    wave_limit_reached=wave,
                                    has_evidence=evidence,
                                )
                            ).reason
                        )
    assert reasons == {
        "",
        "evidence_budget_exhausted",
        "evidence_gap_open",
        "evidence_saturated",
        "wave_limit_exhausted",
    }


def test_continue_has_no_stop_reason() -> None:
    decision = ResearchStopGate.evaluate(_signal())
    assert decision.decision == "continue"
    assert decision.reason == ""
    assert not decision.final_status
    assert not decision.provider_status
    assert not decision.answer_confidence
