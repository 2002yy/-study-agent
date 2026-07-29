from __future__ import annotations

from pathlib import Path

from src.domain.answer_claims import answer_content_hash
from src.rag.answer_claim_eval import (
    deterministic_gold_payload,
    load_answer_claim_eval_cases,
)
from src.rag.answer_claim_provider_replay import evaluate_recorded_provider_answer_claims

FIXTURE = Path("tests/fixtures/rag_eval/answer_cases.json")


def _provider_report() -> dict:
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
                "status": "completed",
                "candidate": {
                    "answer": answer,
                    "refused": payload.refused,
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
        "answer_quality": {"answerability_accuracy": 1.0},
        "scope": {
            "case_ids": [row["case_id"] for row in results],
            "full_gold_suite": True,
        },
        "results": results,
    }


def _evaluate(report: dict) -> dict:
    return evaluate_recorded_provider_answer_claims(
        cases=load_answer_claim_eval_cases(FIXTURE),
        provider_report=report,
        provider_report_fingerprint="recording-sha256",
    )


def test_recorded_answer_line_breaks_are_preserved_in_snapshot_identity():
    report = _provider_report()
    row = report["results"][0]
    original = row["candidate"]["answer"]
    row["candidate"]["answer"] = f"first line\n{original}\nlast line"

    evaluated = _evaluate(report)
    result = next(item for item in evaluated["results"] if item["case_id"] == row["case_id"])

    assert result["final_answer"] == row["candidate"]["answer"]
    assert result["snapshot"]["answer_hash"] == answer_content_hash(
        row["candidate"]["answer"]
    )


def test_empty_recorded_refusal_becomes_invalid_case_without_aborting_suite():
    report = _provider_report()
    row = next(
        item for item in report["results"] if item["case_id"] == "unanswerable_gpu"
    )
    row["candidate"]["answer"] = ""

    evaluated = _evaluate(report)
    quality_row = next(
        item
        for item in evaluated["quality"]["results"]
        if item["case_id"] == "unanswerable_gpu"
    )

    assert evaluated["status"] == "completed"
    assert quality_row["schema_valid"] is False
    assert "structured claims require a final answer" in quality_row["parse_error"]
    assert quality_row["claim_f1"] is None
