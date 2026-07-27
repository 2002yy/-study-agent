from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.rag.answer_claim_eval import (
    ANSWER_CLAIM_EVAL_SCHEMA_VERSION,
    ANSWER_CLAIM_EVALUATOR_VERSION,
    AnswerClaimEvalCase,
    AnswerClaimProducerInput,
    deterministic_gold_payload,
    evaluate_answer_claim_suite,
    load_answer_claim_eval_cases,
    run_answer_claim_producer,
)

BASELINE_KIND = "deterministic_gold_contract_self_test"
GATING = "record_only"
PRODUCER_ID = "deterministic-gold-producer"
PRODUCER_VERSION = "v1"


class DeterministicGoldProducer:
    """Perfect synthetic producer used only to prove evaluator correctness."""

    producer_id = PRODUCER_ID
    producer_version = PRODUCER_VERSION

    def __init__(self, cases: tuple[AnswerClaimEvalCase, ...]) -> None:
        self._cases = {case.case_id: case for case in cases}

    def produce(self, request: AnswerClaimProducerInput) -> dict[str, Any]:
        case = self._cases.get(request.case_id)
        if case is None:
            raise ValueError(f"Unknown deterministic AnswerClaim case: {request.case_id}")
        expected_answer, payload = deterministic_gold_payload(case)
        if request.final_answer != expected_answer:
            raise ValueError(f"Deterministic answer mismatch: {request.case_id}")
        return payload.to_dict()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the record-only deterministic AnswerClaim evaluator baseline."
    )
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/rag_eval/answer_cases.json",
        help="Existing RAG K1 answer-quality fixture.",
    )
    parser.add_argument(
        "--output",
        default="answer-claim-eval-baseline.json",
        help="JSON report path.",
    )
    return parser


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _version_fingerprint(*parts: str) -> str:
    material = "\u0000".join(parts).encode("utf-8")
    return _sha256_bytes(material)


def _canonical_json_fingerprint(path: Path) -> str:
    payload = json.loads(path.read_text(encoding="utf-8"))
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(canonical)


def run_baseline(fixture_path: Path) -> dict[str, Any]:
    if not fixture_path.is_file():
        raise FileNotFoundError(f"Missing AnswerClaim eval fixture: {fixture_path}")
    cases = load_answer_claim_eval_cases(fixture_path)
    producer = DeterministicGoldProducer(cases)
    answers = {
        case.case_id: deterministic_gold_payload(case)[0]
        for case in cases
    }
    candidates = run_answer_claim_producer(
        cases=cases,
        answers=answers,
        producer=producer,
    )
    summary = evaluate_answer_claim_suite(cases, candidates)
    payload_fingerprint = _sha256_bytes(
        json.dumps(
            [
                {
                    "case_id": candidate.case_id,
                    "final_answer": candidate.final_answer,
                    "refused": candidate.refused,
                    "snapshot": (
                        candidate.snapshot.to_dict()
                        if candidate.snapshot is not None
                        else None
                    ),
                    "parse_error": candidate.parse_error,
                }
                for candidate in candidates
            ],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return {
        "schema_version": ANSWER_CLAIM_EVAL_SCHEMA_VERSION,
        "baseline_kind": BASELINE_KIND,
        "gating": GATING,
        "fingerprints": {
            "case_fixture_sha256": _canonical_json_fingerprint(fixture_path),
            "evaluator": _version_fingerprint(ANSWER_CLAIM_EVALUATOR_VERSION),
            "producer": _version_fingerprint(PRODUCER_ID, PRODUCER_VERSION),
            "producer_outputs_sha256": payload_fingerprint,
        },
        "producer": {
            "id": producer.producer_id,
            "version": producer.producer_version,
            "kind": "deterministic_fixture",
            "quality_claim": "evaluator_self_test_only",
        },
        "cases": {
            "total": len(cases),
            "answerable": sum(1 for case in cases if case.answerable),
            "unanswerable": sum(1 for case in cases if not case.answerable),
            "ids": [case.case_id for case in cases],
        },
        "quality": summary.to_dict(),
    }


def compact_summary(report: dict[str, Any]) -> dict[str, Any]:
    quality = dict(report["quality"])
    quality.pop("results", None)
    return {
        "schema_version": report["schema_version"],
        "baseline_kind": report["baseline_kind"],
        "gating": report["gating"],
        "fingerprints": report["fingerprints"],
        "producer": report["producer"],
        "cases": report["cases"],
        "quality": quality,
    }


def main() -> int:
    args = _parser().parse_args()
    report = run_baseline(Path(args.fixture))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(compact_summary(report), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
