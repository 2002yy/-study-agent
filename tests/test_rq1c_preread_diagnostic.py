from __future__ import annotations

from tools.run_rq1c_preread_diagnostic import (
    _assessment_summary,
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
