from __future__ import annotations

from typing import Any, cast

import pytest

from src.web.research.state import load_claim_engine_state
from tools.run_rq1c_bounded_qualification_core import _active_context
from tools.run_rq1c_preread_diagnostic import (
    DIAGNOSTIC_ASSESSOR_TIMEOUT_CAP_SECONDS,
    DIAGNOSTIC_HARD_TIMEOUT_SECONDS,
    DIAGNOSTIC_MODEL_TIMEOUT_CAP_SECONDS,
    DIAGNOSTIC_SOFT_TIMEOUT_SECONDS,
    _diagnostic_active_context,
    _diagnostic_runtime_factory,
    _DiagnosticReadGateway,
    _assessment_summary,
    _assessor_failure_summary,
    _read_failure_summary,
)


def test_assessment_summary_exposes_counts_without_candidate_identity() -> None:
    summary = _assessment_summary(
        {
            "claim_engine_assessments": {
                "claim-secret": [
                    {
                        "candidate": {
                            "id": "candidate-secret",
                            "title": "private title",
                            "canonical_url": "https://private.example/item",
                        },
                        "eligibility": "lead_only",
                        "reason_codes": ["primary_required", "semantic_topic_only"],
                        "assessment": {
                            "relevance": "topic_only",
                            "source_role": "independent_secondary",
                            "expected_gain_signals": ["new_provenance_lead"],
                        },
                    }
                ]
            }
        }
    )

    assert summary == {
        "ranked_candidate_count": 1,
        "eligibility_counts": {"lead_only": 1},
        "relevance_counts": {"topic_only": 1},
        "source_role_counts": {"independent_secondary": 1},
        "reason_code_counts": {
            "primary_required": 1,
            "semantic_topic_only": 1,
        },
        "gain_signal_counts": {"new_provenance_lead": 1},
        "stores_candidate_identity": False,
    }
    serialized = str(summary)
    assert "candidate-secret" not in serialized
    assert "private title" not in serialized
    assert "private.example" not in serialized


def test_read_failure_summary_exposes_safe_counts_without_candidate_identity() -> None:
    summary = _read_failure_summary(
        {
            "read_outcomes": [
                {"candidate_id": "secret", "status": "failed", "error_code": "read_failed"}
            ],
            "failures": [
                {
                    "phase": "reading",
                    "item_id": "secret",
                    "code": "read_failed",
                    "detail": "private response body",
                    "exception_type": "TimeoutError",
                }
            ],
        }
    )

    assert summary == {
        "outcome_error_code_counts": {"read_failed": 1},
        "failure_code_counts": {"read_failed": 1},
        "exception_type_counts": {"TimeoutError": 1},
        "stores_candidate_identity": False,
        "stores_failure_detail": False,
    }
    assert "secret" not in str(summary)
    assert "private response body" not in str(summary)



def test_assessor_failure_summary_splits_safe_compact_domains() -> None:
    summary = _assessor_failure_summary(
        [
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentRelevanceCodeError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentSourceRoleCodeError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentGainSignalCodeError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentGainSignalDuplicateError"},
            {"purpose": "research_candidate_assessment", "error_type": "CompactAssessmentDomainError"},
            {"purpose": "research_candidate_assessment", "error_type": "TimeoutError"},
            {"purpose": "research_evidence_extraction", "error_type": "CompactAssessmentRelevanceCodeError"},
        ]
    )
    assert summary == {
        "failure_category_counts": {
            "compact_code_duplicate": 1,
            "compact_code_gain_signal": 1,
            "compact_code_relevance": 1,
            "compact_code_source_role": 1,
            "expanded_domain": 1,
        },
        "stores_candidate_identity": False,
        "stores_failure_detail": False,
    }


class _ReaderStub:
    def read(self, url: str, *, max_chars: int = 6000):
        del max_chars
        if url.endswith("exception"):
            raise TimeoutError("private timeout detail")
        if url.endswith("empty"):
            return {"ok": True, "content": "   ", "url": "private-empty"}
        if url.endswith("known-negative"):
            return {
                "ok": False,
                "error": "private upstream detail",
                "error_code": "timeout",
                "url": "private-known",
            }
        return {
            "ok": False,
            "error": "private upstream detail",
            "error_code": "private-upstream-code",
            "url": "private-unknown",
        }


def test_diagnostic_reader_classifies_failures_without_storing_content_or_identity() -> None:
    reader = _DiagnosticReadGateway(_ReaderStub())
    with pytest.raises(TimeoutError):
        reader.read("https://secret.example/exception")
    assert reader.read("https://secret.example/empty")["ok"] is True
    assert reader.read("https://secret.example/known-negative")["ok"] is False
    assert reader.read("https://secret.example/other-negative")["ok"] is False
    summary = reader.summary()
    assert summary == {
        "failure_category_counts": {
            "empty_content": 1,
            "exception": 1,
            "gateway_negative_result": 2,
        },
        "provider_code_counts": {"other": 1, "timeout": 1},
        "stores_candidate_identity": False,
        "stores_failure_detail": False,
        "stores_page_content": False,
    }
    serialized = str(summary)
    assert "secret.example" not in serialized
    assert "private upstream detail" not in serialized
    assert "private-upstream-code" not in serialized


def _state(context: dict[str, Any]):
    loaded = load_claim_engine_state(context, known_evidence_ids=())
    assert loaded.available
    assert loaded.state is not None
    return loaded.state


def test_diagnostic_wall_clock_override_preserves_business_budgets() -> None:
    production = _state(_active_context("2026-09-05"))
    diagnostic = _state(_diagnostic_active_context("2026-09-05"))

    assert diagnostic.budget.max_candidates == production.budget.max_candidates == 20
    assert diagnostic.budget.max_reads == production.budget.max_reads == 8
    assert diagnostic.budget.max_total_chars == 16000
    assert diagnostic.budget.max_total_chars == production.budget.max_total_chars
    assert production.budget.soft_timeout_seconds == 45
    assert production.budget.hard_timeout_seconds == 60
    assert diagnostic.budget.soft_timeout_seconds == DIAGNOSTIC_SOFT_TIMEOUT_SECONDS
    assert diagnostic.budget.hard_timeout_seconds == DIAGNOSTIC_HARD_TIMEOUT_SECONDS


def test_diagnostic_runtime_uses_nonqualification_timeout_caps() -> None:
    runtime = _diagnostic_runtime_factory(
        cast(Any, object()),
        cast(Any, object()),
    )

    assert runtime.model_timeout_cap_seconds == DIAGNOSTIC_MODEL_TIMEOUT_CAP_SECONDS
    assert (
        runtime.claim_planner.model_gateway._timeout_seconds  # noqa: SLF001
        == DIAGNOSTIC_MODEL_TIMEOUT_CAP_SECONDS
    )
    assert (
        runtime.candidate_assessor.model_gateway._timeout_seconds  # noqa: SLF001
        == DIAGNOSTIC_MODEL_TIMEOUT_CAP_SECONDS
    )
    assert (
        runtime.candidate_assessor.timeout_cap_seconds
        == DIAGNOSTIC_ASSESSOR_TIMEOUT_CAP_SECONDS
    )
