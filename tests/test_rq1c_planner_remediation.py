from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from tools.rq1c_qualification_guardrails import _planner_observability
from tools.run_rq1c_planner_diagnostic import classify_planner_failure


def test_planner_observability_projects_only_safe_attempt_metadata() -> None:
    run = SimpleNamespace(
        research_context={
            "claim_engine_runtime": {
                "model_calls": [
                    {
                        "purpose": "research_claim_planning",
                        "attempt": 1,
                        "status": "attempt_failed",
                        "error_type": "ValueError",
                        "finish_reason": "stop",
                        "input_tokens": 512,
                        "output_tokens": 93,
                        "total_tokens": 605,
                        "elapsed_seconds": 4.125,
                        "response_text": "must never escape",
                        "prompt": "must never escape",
                    },
                    {
                        "purpose": "candidate_assessment",
                        "attempt": 1,
                        "status": "completed",
                    },
                ]
            }
        }
    )

    projection = _planner_observability(run)

    assert projection == {
        "attempt_count": 1,
        "attempts": [
            {
                "attempt": 1,
                "status": "attempt_failed",
                "error_type": "ValueError",
                "finish_reason": "stop",
                "input_tokens": 512,
                "output_tokens": 93,
                "total_tokens": 605,
                "elapsed_seconds": 4.125,
            }
        ],
        "stores_raw_model_text": False,
    }
    encoded = json.dumps(projection)
    assert "must never escape" not in encoded
    assert "response_text" not in encoded
    assert "prompt" not in encoded


def test_planner_observability_handles_missing_runtime() -> None:
    assert _planner_observability(None) == {
        "attempt_count": 0,
        "attempts": [],
        "stores_raw_model_text": False,
    }


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (json.JSONDecodeError("bad", "{", 0), "json_decode"),
        (TimeoutError("timed out"), "timeout"),
        (ValueError("question anchor must be copied from user question"), "anchor_not_verbatim"),
        (ValueError("runtime claim plan contains duplicate anchors"), "duplicate_anchor"),
        (ValueError("invalid claim kind"), "invalid_kind"),
        (ValueError("invalid evidence policy profile"), "invalid_policy_profile"),
        (TypeError("runtime claim must be an object"), "semantic_schema"),
    ],
)
def test_classify_planner_failure_uses_stable_safe_taxonomy(
    exc: BaseException, expected: str
) -> None:
    assert classify_planner_failure(exc) == expected
