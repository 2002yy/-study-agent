"""Record-only AnswerClaim evaluation over real K1e Provider recordings.

The adapter consumes the structured assertions already returned by the K1e
real-provider prompt. It never infers claims from natural-language answers,
never calls a Provider, and never writes ChatTurns or committed learning truth.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.domain.answer_claims import answer_content_hash, deterministic_claim_id
from src.rag.answer_claim_eval import (
    ANSWER_CLAIM_EVAL_SCHEMA_VERSION,
    ANSWER_CLAIM_EVALUATOR_VERSION,
    AnswerClaimEvalCase,
    AnswerClaimProducerInput,
    evaluate_answer_claim_suite,
    run_answer_claim_producer,
)

ANSWER_CLAIM_PROVIDER_REPLAY_SCHEMA_VERSION = 1
ANSWER_CLAIM_PROVIDER_ADAPTER_VERSION = "k1e-structured-assertion-adapter-v1"
EVALUATION_KIND = "answer_claim_recorded_provider"
GATING = "record_only"


@dataclass(frozen=True)
class RecordedProviderCase:
    case_id: str
    answer: str
    refused: bool
    assertions: tuple[dict[str, Any], ...]


class RecordedProviderAnswerClaimProducer:
    """Adapt Provider-authored K1e assertions into the strict claim contract."""

    def __init__(
        self,
        *,
        recorded_cases: tuple[RecordedProviderCase, ...],
        provider_identity: dict[str, str],
        prompt_template_fingerprint: str,
    ) -> None:
        self._cases = {case.case_id: case for case in recorded_cases}
        profile = provider_identity["provider_profile"]
        model = provider_identity["model_name"]
        self.producer_id = f"recorded-provider:{profile}:{model}"
        self.producer_version = _fingerprint_text(
            ANSWER_CLAIM_PROVIDER_ADAPTER_VERSION,
            prompt_template_fingerprint,
        )

    def produce(self, request: AnswerClaimProducerInput) -> dict[str, Any]:
        recorded = self._cases.get(request.case_id)
        if recorded is None:
            raise ValueError(f"Missing recorded Provider case: {request.case_id}")
        if recorded.answer != request.final_answer:
            raise ValueError(f"Recorded answer mismatch: {request.case_id}")

        answer_hash = answer_content_hash(recorded.answer)
        claims: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []
        for assertion in recorded.assertions:
            text = _required_text(assertion.get("text"), "assertion text")
            claim_id = deterministic_claim_id(
                answer_hash=answer_hash,
                claim_text=text,
            )
            claims.append(
                {
                    "id": claim_id,
                    "text": text,
                    "kind": "factual",
                    "status": "asserted",
                    "source": "provider_structured",
                }
            )
            raw_sources = assertion.get("cited_sources")
            if not isinstance(raw_sources, list):
                raise ValueError("recorded assertion cited_sources must be a list")
            for evidence_id in raw_sources:
                links.append(
                    {
                        "claim_id": claim_id,
                        "evidence_id": _required_text(evidence_id, "evidence id"),
                        "support_type": "direct_support",
                        "confidence": 1.0,
                    }
                )

        return {
            "refused": recorded.refused,
            "claims": claims,
            "claim_links": links,
        }


def evaluate_recorded_provider_answer_claims(
    *,
    cases: tuple[AnswerClaimEvalCase, ...],
    provider_report: dict[str, Any],
    provider_report_fingerprint: str,
    run_label: str = "",
    cost_cny: float | None = None,
) -> dict[str, Any]:
    """Evaluate one complete real-provider K1e report without network access."""

    recorded_cases = _load_recorded_cases(provider_report)
    expected_ids = {case.case_id for case in cases}
    recorded_ids = {case.case_id for case in recorded_cases}
    missing_ids = sorted(expected_ids - recorded_ids)
    extra_ids = sorted(recorded_ids - expected_ids)
    if missing_ids or extra_ids:
        raise ValueError(
            "Recorded Provider case set mismatch: "
            f"missing={missing_ids}, extra={extra_ids}"
        )

    provider_identity = _provider_identity(provider_report)
    prompt_fingerprint = _required_text(
        provider_report.get("prompt_template_fingerprint"),
        "source prompt template fingerprint",
    )
    producer = RecordedProviderAnswerClaimProducer(
        recorded_cases=recorded_cases,
        provider_identity=provider_identity,
        prompt_template_fingerprint=prompt_fingerprint,
    )
    answers = {case.case_id: case.answer for case in recorded_cases}
    candidates = run_answer_claim_producer(
        cases=cases,
        answers=answers,
        producer=producer,
    )
    summary = evaluate_answer_claim_suite(cases, candidates)
    candidate_rows = [
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
    ]

    return {
        "schema_version": ANSWER_CLAIM_PROVIDER_REPLAY_SCHEMA_VERSION,
        "evaluation_kind": EVALUATION_KIND,
        "replay_kind": "real_provider",
        "gating": GATING,
        "status": "completed",
        "run_label": _clean_text(run_label),
        "source_report": {
            "fingerprint_sha256": provider_report_fingerprint,
            "schema_version": provider_report.get("schema_version"),
            "corpus_fingerprint": _required_text(
                provider_report.get("corpus_fingerprint"),
                "source corpus fingerprint",
            ),
            "prompt_template_fingerprint": prompt_fingerprint,
            "provider": provider_identity,
            "latency": provider_report.get("latency"),
            "usage": provider_report.get("usage"),
            "answer_quality": provider_report.get("answer_quality"),
        },
        "cost": {
            "currency": "CNY",
            "amount": cost_cny,
            "source": "operator_supplied" if cost_cny is not None else "not_supplied",
        },
        "producer": {
            "id": producer.producer_id,
            "version": producer.producer_version,
            "adapter_version": ANSWER_CLAIM_PROVIDER_ADAPTER_VERSION,
            "source": "provider_structured_assertions",
            "quality_claim": "recorded_real_provider_only",
        },
        "fingerprints": {
            "evaluator_fingerprint_sha256": _fingerprint_text(
                ANSWER_CLAIM_EVALUATOR_VERSION
            ),
            "adapter_fingerprint_sha256": _fingerprint_text(
                ANSWER_CLAIM_PROVIDER_ADAPTER_VERSION
            ),
            "producer_outputs_fingerprint_sha256": _fingerprint_json(candidate_rows),
        },
        "cases": {
            "total": len(cases),
            "answerable": sum(1 for case in cases if case.answerable),
            "unanswerable": sum(1 for case in cases if not case.answerable),
            "ids": [case.case_id for case in cases],
        },
        "quality": summary.to_dict(),
        "results": candidate_rows,
        "boundaries": {
            "provider_called": False,
            "natural_language_claim_inference": False,
            "chat_turn_written": False,
            "committed_truth_changed": False,
            "production_prompt_changed": False,
        },
        "answer_claim_eval_schema_version": ANSWER_CLAIM_EVAL_SCHEMA_VERSION,
    }


def load_provider_report(path: str | Path) -> tuple[dict[str, Any], str]:
    report_path = Path(path)
    raw = report_path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Provider replay report must be a JSON object")
    return payload, hashlib.sha256(raw).hexdigest()


def _load_recorded_cases(report: dict[str, Any]) -> tuple[RecordedProviderCase, ...]:
    if report.get("replay_kind") != "real_provider":
        raise ValueError("AnswerClaim replay requires real_provider provenance")
    if report.get("status") != "completed":
        raise ValueError("AnswerClaim replay requires a completed Provider report")
    if not isinstance(report.get("answer_quality"), dict):
        raise ValueError("Completed Provider report requires answer_quality")
    scope = _object(report.get("scope"))
    if scope.get("full_gold_suite") is not True:
        raise ValueError("AnswerClaim replay requires the full Provider gold suite")
    failed_cases = report.get("failed_cases")
    if failed_cases != []:
        raise ValueError("Completed Provider report must not contain failed cases")

    raw_results = report.get("results")
    if not isinstance(raw_results, list):
        raise ValueError("Provider replay report requires results")

    recorded: list[RecordedProviderCase] = []
    seen: set[str] = set()
    for row in raw_results:
        raw_row = _object(row)
        case_id = _required_text(raw_row.get("case_id"), "case id")
        if case_id in seen:
            raise ValueError(f"Duplicate recorded Provider case: {case_id}")
        seen.add(case_id)
        if raw_row.get("status") != "completed":
            raise ValueError(f"Recorded Provider case is not completed: {case_id}")
        candidate = _object(raw_row.get("candidate"))
        answer = _recorded_answer(candidate.get("answer"))
        refused = candidate.get("refused")
        assertions = candidate.get("assertions")
        if not isinstance(refused, bool):
            raise ValueError(f"Recorded Provider refusal must be boolean: {case_id}")
        if not isinstance(assertions, list):
            raise ValueError(f"Recorded Provider assertions must be a list: {case_id}")
        recorded.append(
            RecordedProviderCase(
                case_id=case_id,
                answer=answer,
                refused=refused,
                assertions=tuple(_object(assertion) for assertion in assertions),
            )
        )

    declared_cases = report.get("cases")
    completed_cases = report.get("completed_cases")
    if declared_cases != len(recorded) or completed_cases != len(recorded):
        raise ValueError("Provider replay case counts do not match completed results")
    scope_ids = scope.get("case_ids")
    if not isinstance(scope_ids, list) or set(map(str, scope_ids)) != seen:
        raise ValueError("Provider replay scope does not match completed results")
    return tuple(recorded)


def _provider_identity(report: dict[str, Any]) -> dict[str, str]:
    raw = _object(report.get("provider"))
    return {
        "provider_profile": _required_text(
            raw.get("provider_profile"),
            "Provider profile",
        ),
        "model_name": _required_text(raw.get("model_name"), "Provider model name"),
        "endpoint_fingerprint": _required_text(
            raw.get("endpoint_fingerprint"),
            "Provider endpoint fingerprint",
        ),
    }


def _recorded_answer(value: Any) -> str:
    return str(value or "").replace("\r\n", "\n").replace("\r", "\n")


def _fingerprint_json(payload: Any) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _fingerprint_text(*parts: str) -> str:
    return hashlib.sha256("\u0000".join(parts).encode("utf-8")).hexdigest()


def _required_text(value: Any, label: str) -> str:
    text = _clean_text(value)
    if not text:
        raise ValueError(f"Recorded Provider replay requires {label}")
    return text


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}
