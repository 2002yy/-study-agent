"""Server-owned answer-stage model-call audit (RQ1-C answer batch).

``rag_snapshot["answer_validation_audit"]`` is the authoritative record of the
final-answer model phases for one ChatTurn:

- ``answer_generation``       physical answer-generator calls that contributed to
                              this turn; continuations accumulate prior calls;
- ``answer_claim_binding``    binder provider calls behind the publication gate.

It answers one question only: how many physical model calls happened in the
answer stage, in which phase, and what was the canonical outcome.  It never
carries provider message bodies; ``error_type`` is a type name or a canonical
reason token at most.  It is deliberately separate from ``external_data_policy``
audit JSON (which records what data was allowed to leave) and from the
research-run ``cursor.model_calls`` audit (which describes the research run
itself).

Client-supplied content is never trusted: normalizing rebuilds every field from
whitelisted, bounded values, and identity is fixed to the assistant message
that actually reached the learner (``learner_answer_sha256``), while
``candidate_answer_sha256`` stays the pre-gate candidate identity.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

ANSWER_VALIDATION_AUDIT_SCHEMA = "answer-validation-audit-v1"
PHASE_ANSWER_GENERATION = "answer_generation"
PHASE_ANSWER_CLAIM_BINDING = "answer_claim_binding"
PHASE_OUTCOME_COMPLETED = "completed"
PHASE_OUTCOME_PASSED = "passed"
PHASE_OUTCOME_REJECTED = "rejected"
PHASE_OUTCOME_BUDGET_EXHAUSTED = "budget_exhausted"
PHASE_OUTCOME_INTERRUPTED = "interrupted"

_KNOWN_PHASES = frozenset({PHASE_ANSWER_GENERATION, PHASE_ANSWER_CLAIM_BINDING})
_KNOWN_OUTCOMES = frozenset(
    {
        PHASE_OUTCOME_COMPLETED,
        PHASE_OUTCOME_PASSED,
        PHASE_OUTCOME_REJECTED,
        PHASE_OUTCOME_BUDGET_EXHAUSTED,
        PHASE_OUTCOME_INTERRUPTED,
    }
)
_MAX_PHASES = 8
_MAX_REASON_CHARS = 120
# Type names and canonical tokens only; raw provider messages are forbidden.
_ALLOWED_ERROR_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:.-"
)


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def build_answer_validation_audit(
    *,
    candidate_answer: str,
    published_answer: str,
    phases: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one server-owned audit for a completed research-backed turn."""
    normalized_phases: dict[str, dict[str, Any]] = {}
    for name, detail in phases.items():
        if name not in _KNOWN_PHASES:
            continue
        model_calls = _bounded_nonnegative(detail.get("model_calls"))
        outcome = _canonical_outcome(detail.get("outcome"))
        if outcome is None:
            continue
        normalized_phases[name] = {
            "attempted": True,
            "model_calls": model_calls,
            "attempts": max(0, _bounded_nonnegative(detail.get("attempts"))),
            "outcome": outcome,
            "error_type": _canonical_error_type(detail.get("error_type")),
        }
    return {
        "schema_version": ANSWER_VALIDATION_AUDIT_SCHEMA,
        "candidate_answer_sha256": sha256_text(candidate_answer),
        "learner_answer_sha256": sha256_text(published_answer),
        "phases": normalized_phases,
    }


def normalize_answer_validation_audit_for_turn(
    raw: Any, assistant_message: str
) -> dict[str, Any] | None:
    """Normalize a stored audit against the assistant message actually kept.

    Returns ``None`` when nothing trustworthy exists (legacy turns and client
    fabrications collapse to no audit rather than to a forged one).  Field
    values are rebuilt from bounded whitelisted inputs only.
    """
    if not isinstance(raw, Mapping):
        return None
    if raw.get("schema_version") != ANSWER_VALIDATION_AUDIT_SCHEMA:
        return None
    candidate_sha = str(raw.get("candidate_answer_sha256") or "").strip()
    if not _is_sha256(candidate_sha):
        return None
    phases: dict[str, dict[str, Any]] = {}
    raw_phases = raw.get("phases")
    if isinstance(raw_phases, Mapping):
        for name, detail in raw_phases.items():
            if name not in _KNOWN_PHASES or len(phases) >= _MAX_PHASES:
                continue
            if not isinstance(detail, Mapping):
                continue
            model_calls = _bounded_nonnegative(detail.get("model_calls"))
            outcome = _canonical_outcome(detail.get("outcome"))
            if outcome is None:
                continue
            phases[name] = {
                "attempted": True,
                "model_calls": model_calls,
                "attempts": max(
                    0, min(_bounded_nonnegative(detail.get("attempts")), model_calls)
                ),
                "outcome": outcome,
                "error_type": _canonical_error_type(detail.get("error_type")),
            }
    return {
        "schema_version": ANSWER_VALIDATION_AUDIT_SCHEMA,
        "candidate_answer_sha256": candidate_sha,
        "learner_answer_sha256": sha256_text(assistant_message),
        "phases": phases,
    }


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _bounded_nonnegative(value: Any) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def _canonical_outcome(value: Any) -> str | None:
    candidate = str(value or "").strip()
    return candidate if candidate in _KNOWN_OUTCOMES else None


def _canonical_error_type(value: Any) -> str:
    candidate = str(value or "").strip()
    if not candidate:
        return ""
    if len(candidate) > _MAX_REASON_CHARS or not all(
        char in _ALLOWED_ERROR_CHARS for char in candidate
    ):
        return "unavailable"
    return candidate
