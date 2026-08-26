from __future__ import annotations

import json
from typing import Any

from src.evals.research_quality_runner import research_run_transcript_from_dict
from src.evals.research_quality_semantic_projector import (
    project_live_semantic_case,
)


def _claim_response() -> str:
    return json.dumps(
        {
            "schema_version": "research-claim-projection-v1",
            "claims": [
                {
                    "surface": "The current official value is published.",
                    "kind": "factual",
                    "priority": "critical",
                    "evidence_policy_profile": "current_fact",
                    "max_age_days": 365,
                    "requires_dated_evidence": True,
                }
            ],
        }
    )


def _evidence_response() -> str:
    return json.dumps(
        {
            "schema_version": "research-evidence-projection-v1",
            "source_role": "primary",
            "publisher_cluster": "example-project",
            "published_at": "2026-08-20",
            "relations": [
                {
                    "claim_index": 0,
                    "relation": "supports",
                    "strength": 0.94,
                    "reason_codes": ["direct_statement", "current_value"],
                }
            ],
        }
    )


def _observation(*, relevant: bool = True) -> dict[str, Any]:
    return {
        "search_status": "ok",
        "attempted_queries": ["public benchmark question"],
        "candidates": [
            {
                "title": "Official documentation",
                "url": "https://example.test/docs",
                "benchmark_relevant": relevant,
            }
        ],
    }


def _reader(url: str, limit: int) -> dict[str, Any]:
    return {
        "ok": True,
        "url": url,
        "content": "Official statement " + ("x" * (limit + 200)),
        "backend": "fake",
    }


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            nested
            for item in value.values()
            for nested in _all_keys(item)
        }
    if isinstance(value, list):
        return {nested for item in value for nested in _all_keys(item)}
    return set()


def test_semantic_projection_is_bounded_audited_and_body_free() -> None:
    responses = iter([_claim_response(), _evidence_response()])
    sent_messages: list[list[dict[str, str]]] = []

    def complete(messages: list[dict[str, str]]) -> str:
        sent_messages.append(messages)
        return next(responses)

    result = project_live_semantic_case(
        case_id="live-1",
        question="What is the current official value?",
        reference_date="2026-08-26",
        observation=_observation(),
        read_page=_reader,
        complete=complete,
        provider="deepseek",
        model="deepseek-pro",
        max_reads=8,
        max_page_chars=12_000,
        now=lambda: "2026-08-26T00:00:00Z",
    )

    assert result["projection_status"] == "completed"
    assert len(sent_messages) == 2
    assert len(json.loads(sent_messages[1][1]["content"])["public_web_content"]) == 12_000
    assert len(result["external_calls"]) == 2
    assert result["external_calls"][1]["data_counts"]["public_web_content_chars"] == 12_000
    assert result["external_calls"][1]["status"] == "completed"
    assert result["external_calls"][1]["response_sha256"]
    assert "content" not in _all_keys(result)
    assert "messages" not in _all_keys(result)
    assert "raw_model_output" not in _all_keys(result)

    transcript = research_run_transcript_from_dict(result["transcript"])
    assert transcript.closed is True
    assert transcript.llm_calls == 2
    assert transcript.projected_claim_evidence[0].relation == "supports"


def test_semantic_projection_retries_once_and_audits_both_attempts() -> None:
    responses = iter(["not-json", _claim_response()])

    result = project_live_semantic_case(
        case_id="live-retry",
        question="What is the current official value?",
        reference_date="2026-08-26",
        observation={
            "search_status": "ok",
            "attempted_queries": ["query"],
            "candidates": [],
        },
        read_page=_reader,
        complete=lambda _messages: next(responses),
        provider="deepseek",
        model="deepseek-pro",
        now=lambda: "2026-08-26T00:00:00Z",
    )

    assert result["projection_status"] == "completed"
    assert [item["status"] for item in result["external_calls"]] == [
        "attempted_failed",
        "completed",
    ]
    assert [item["attempt"] for item in result["external_calls"]] == [1, 2]
    assert len({item["logical_call_id"] for item in result["external_calls"]}) == 1


def test_semantic_projection_fails_closed_without_keyword_fallback() -> None:
    result = project_live_semantic_case(
        case_id="live-failed",
        question="What is the current official value?",
        reference_date="2026-08-26",
        observation=_observation(),
        read_page=_reader,
        complete=lambda _messages: "{}",
        provider="deepseek",
        model="deepseek-pro",
        now=lambda: "2026-08-26T00:00:00Z",
    )

    assert result["projection_status"] == "unavailable"
    assert result["failure_reason"] == "claim_projection_unavailable"
    assert result["typed_failure_reason"].startswith("claim_projection_unavailable")
    assert result["stop_reason"] == "projection_exhausted_no_fallback"
    assert result["transcript"] is not None
    assert result["transcript"]["question_surface"]
    assert result["retrieval_funnel"]["attempted_queries"] == 1
    assert len(result["external_calls"]) == 2
    assert all(item["status"] == "attempted_failed" for item in result["external_calls"])


def test_irrelevant_candidates_are_never_read_or_sent() -> None:
    read_calls: list[str] = []

    def reader(url: str, _limit: int) -> dict[str, Any]:
        read_calls.append(url)
        return _reader(url, 1000)

    result = project_live_semantic_case(
        case_id="live-no-read",
        question="What is the current official value?",
        reference_date="2026-08-26",
        observation=_observation(relevant=False),
        read_page=reader,
        complete=lambda _messages: _claim_response(),
        provider="deepseek",
        model="deepseek-pro",
        now=lambda: "2026-08-26T00:00:00Z",
    )

    assert result["projection_status"] == "completed"
    assert read_calls == []
    assert len(result["external_calls"]) == 1
    assert result["documents"] == []
