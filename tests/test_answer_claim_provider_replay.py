from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.rag.answer_claim_eval import (
    deterministic_gold_payload,
    load_answer_claim_eval_cases,
)
from src.rag.answer_claim_provider_replay import (
    evaluate_recorded_provider_answer_claims,
    load_provider_report,
)

FIXTURE = Path("tests/fixtures/rag_eval/answer_cases.json")


def _perfect_provider_report() -> dict:
    cases = load_answer_claim_eval_cases(FIXTURE)
    results = []
    for case in cases:
        answer, payload = deterministic_gold_payload(case)
        sources_by_claim: dict[str, list[str]] = {
            claim["id"]: [] for claim in payload.claims
        }
        for link in payload.claim_links:
            sources_by_claim[link["claim_id"]].append(link["evidence_id"])
        results.append(
            {
                "case_id": case.case_id,
                "query": case.question,
                "status": "completed",
                "candidate": {
                    "answer": answer,
                    "refused": payload.refused,
                    "cited_sources": sorted(
                        {
                            source
                            for sources in sources_by_claim.values()
                            for source in sources
                        }
                    ),
                    "assertions": [
                        {
                            "text": claim["text"],
                            "cited_sources": sources_by_claim[claim["id"]],
                        }
                        for claim in payload.claims
                    ],
                },
            }
        )
    return {
        "schema_version": 1,
        "replay_kind": "real_provider",
        "status": "completed",
        "corpus_fingerprint": "corpus-v1",
        "prompt_template_fingerprint": "prompt-v1",
        "provider": {
            "provider_profile": "test-provider",
            "model_name": "test-model",
            "endpoint_fingerprint": "endpoint-v1",
        },
        "cases": len(results),
        "completed_cases": len(results),
        "failed_cases": [],
        "latency": {"total_seconds": 12.0, "mean_seconds": 1.2},
        "usage": {
            "complete": True,
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "total_tokens": 1500,
        },
        "answer_quality": {"answerability_accuracy": 1.0},
        "scope": {
            "case_ids": [row["case_id"] for row in results],
            "full_gold_suite": True,
        },
        "results": results,
    }


def _evaluate(report: dict, *, cost_cny: float | None = None) -> dict:
    return evaluate_recorded_provider_answer_claims(
        cases=load_answer_claim_eval_cases(FIXTURE),
        provider_report=report,
        provider_report_fingerprint="recording-sha256",
        run_label="stability-run-1",
        cost_cny=cost_cny,
    )


def test_complete_real_provider_recording_scores_through_strict_claim_contract():
    report = _evaluate(_perfect_provider_report(), cost_cny=1.25)

    assert report["evaluation_kind"] == "answer_claim_recorded_provider"
    assert report["replay_kind"] == "real_provider"
    assert report["gating"] == "record_only"
    assert report["status"] == "completed"
    assert report["run_label"] == "stability-run-1"
    assert report["cost"] == {
        "currency": "CNY",
        "amount": 1.25,
        "source": "operator_supplied",
    }
    assert report["producer"]["source"] == "provider_structured_assertions"
    assert report["producer"]["quality_claim"] == "recorded_real_provider_only"
    assert report["quality"]["schema_parse_rate"] == 1.0
    assert report["quality"]["answerability_accuracy"] == 1.0
    assert report["quality"]["mean_claim_f1"] == 1.0
    assert report["quality"]["mean_link_f1"] == 1.0
    assert report["quality"]["refusal_leakage_rate"] == 0.0
    assert report["boundaries"] == {
        "provider_called": False,
        "natural_language_claim_inference": False,
        "chat_turn_written": False,
        "committed_truth_changed": False,
        "production_prompt_changed": False,
    }
    first_snapshot = report["results"][0]["snapshot"]
    assert first_snapshot["claims"][0]["source"] == "provider_structured"


def test_unknown_provider_citation_is_invalid_without_fabricated_quality_score():
    source = _perfect_provider_report()
    source["results"][0]["candidate"]["assertions"][0]["cited_sources"] = [
        "unknown.md"
    ]

    report = _evaluate(source)

    assert report["quality"]["schema_parse_rate"] == 0.9
    assert report["quality"]["invalid_case_ids"] == ["clean_requests_session"]
    result = next(
        row
        for row in report["quality"]["results"]
        if row["case_id"] == "clean_requests_session"
    )
    assert result["schema_valid"] is False
    assert "unknown evidence id" in result["parse_error"]
    assert result["claim_f1"] is None
    assert result["link_f1"] is None


def test_unanswerable_leakage_from_recorded_provider_is_reported():
    source = _perfect_provider_report()
    row = next(
        item for item in source["results"] if item["case_id"] == "unanswerable_gpu"
    )
    row["candidate"] = {
        "answer": "The required GPU is Model X.",
        "refused": False,
        "cited_sources": [],
        "assertions": [
            {"text": "The required GPU is Model X.", "cited_sources": []}
        ],
    }

    report = _evaluate(source)
    result = next(
        item
        for item in report["quality"]["results"]
        if item["case_id"] == "unanswerable_gpu"
    )

    assert result["schema_valid"] is True
    assert result["answerability_correct"] is False
    assert result["refusal_leakage"] is True
    assert result["unsupported_claim_rate"] == 1.0


def test_synthetic_or_incomplete_source_report_is_rejected():
    synthetic = _perfect_provider_report()
    synthetic["replay_kind"] = "synthetic_test"
    with pytest.raises(ValueError, match="real_provider provenance"):
        _evaluate(synthetic)

    incomplete = _perfect_provider_report()
    incomplete["status"] = "partial_failure"
    with pytest.raises(ValueError, match="completed Provider report"):
        _evaluate(incomplete)


def test_recorded_case_set_and_declared_counts_must_match_fixture():
    missing = _perfect_provider_report()
    missing["results"].pop()
    missing["cases"] -= 1
    missing["completed_cases"] -= 1
    with pytest.raises(ValueError, match="case set mismatch"):
        _evaluate(missing)

    bad_count = _perfect_provider_report()
    bad_count["completed_cases"] -= 1
    with pytest.raises(ValueError, match="case counts"):
        _evaluate(bad_count)


def test_provider_report_loader_fingerprints_exact_recording_bytes(tmp_path: Path):
    path = tmp_path / "provider.json"
    path.write_text(
        json.dumps(_perfect_provider_report(), ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report, fingerprint = load_provider_report(path)

    assert report["replay_kind"] == "real_provider"
    assert len(fingerprint) == 64
    assert fingerprint == load_provider_report(path)[1]
