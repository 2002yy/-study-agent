"""Record-only evaluation for structured AnswerClaim producers.

This evaluator reuses the checked-in RAG K1 answer cases. It measures a
producer's structured claim output without changing production chat prompts,
writing ChatTurns, or inferring claims from natural-language answers.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

from src.domain.answer_claims import (
    AnswerClaimSnapshotV1,
    answer_content_hash,
    build_answer_claim_snapshot,
    deterministic_claim_id,
)

ANSWER_CLAIM_EVAL_SCHEMA_VERSION = 1
ANSWER_CLAIM_EVALUATOR_VERSION = "answer-claim-evaluator-v1"


@dataclass(frozen=True)
class AnswerClaimExpectedClaim:
    claim_id: str
    match_terms: tuple[str, ...]
    kind: str
    support_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnswerClaimEvalCase:
    case_id: str
    question: str
    answerable: bool
    expected_claims: tuple[AnswerClaimExpectedClaim, ...]
    known_evidence_ids: tuple[str, ...]
    forbidden_claim_terms: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnswerClaimProducerInput:
    case_id: str
    question: str
    final_answer: str
    known_evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AnswerClaimProducerOutput:
    refused: bool
    claims: tuple[dict[str, Any], ...]
    claim_links: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "refused": self.refused,
            "claims": [dict(claim) for claim in self.claims],
            "claim_links": [dict(link) for link in self.claim_links],
        }


class AnswerClaimProducer(Protocol):
    producer_id: str
    producer_version: str

    def produce(self, request: AnswerClaimProducerInput) -> dict[str, Any]:
        ...


@dataclass(frozen=True)
class ParsedAnswerClaimCandidate:
    case_id: str
    final_answer: str
    refused: bool | None
    snapshot: AnswerClaimSnapshotV1 | None
    parse_error: str = ""

    @property
    def schema_valid(self) -> bool:
        return self.snapshot is not None and not self.parse_error


@dataclass(frozen=True)
class AnswerClaimEvalResult:
    case_id: str
    schema_valid: bool
    parse_error: str
    answerability_correct: bool | None
    claim_precision: float | None
    claim_recall: float | None
    claim_f1: float | None
    kind_accuracy: float | None
    claim_coverage: float | None
    unsupported_claim_rate: float | None
    link_precision: float | None
    link_recall: float | None
    link_f1: float | None
    refusal_leakage: bool | None
    forbidden_claim_leakage: bool | None
    matched_claim_ids: tuple[str, ...] = ()
    missing_claim_ids: tuple[str, ...] = ()
    unsupported_claim_texts: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": self.case_id,
            "schema_valid": self.schema_valid,
            "parse_error": self.parse_error,
            "answerability_correct": self.answerability_correct,
            "claim_precision": self.claim_precision,
            "claim_recall": self.claim_recall,
            "claim_f1": self.claim_f1,
            "kind_accuracy": self.kind_accuracy,
            "claim_coverage": self.claim_coverage,
            "unsupported_claim_rate": self.unsupported_claim_rate,
            "link_precision": self.link_precision,
            "link_recall": self.link_recall,
            "link_f1": self.link_f1,
            "refusal_leakage": self.refusal_leakage,
            "forbidden_claim_leakage": self.forbidden_claim_leakage,
            "matched_claim_ids": list(self.matched_claim_ids),
            "missing_claim_ids": list(self.missing_claim_ids),
            "unsupported_claim_texts": list(self.unsupported_claim_texts),
        }


@dataclass(frozen=True)
class AnswerClaimEvalSummary:
    total_cases: int
    schema_valid_cases: int
    schema_parse_rate: float
    answerability_accuracy: float | None
    mean_claim_precision: float | None
    mean_claim_recall: float | None
    mean_claim_f1: float | None
    mean_kind_accuracy: float | None
    mean_claim_coverage: float | None
    mean_unsupported_claim_rate: float | None
    mean_link_precision: float | None
    mean_link_recall: float | None
    mean_link_f1: float | None
    refusal_leakage_rate: float | None
    forbidden_claim_leakage_rate: float | None
    invalid_case_ids: tuple[str, ...]
    results: tuple[AnswerClaimEvalResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_cases": self.total_cases,
            "schema_valid_cases": self.schema_valid_cases,
            "schema_parse_rate": self.schema_parse_rate,
            "answerability_accuracy": self.answerability_accuracy,
            "mean_claim_precision": self.mean_claim_precision,
            "mean_claim_recall": self.mean_claim_recall,
            "mean_claim_f1": self.mean_claim_f1,
            "mean_kind_accuracy": self.mean_kind_accuracy,
            "mean_claim_coverage": self.mean_claim_coverage,
            "mean_unsupported_claim_rate": self.mean_unsupported_claim_rate,
            "mean_link_precision": self.mean_link_precision,
            "mean_link_recall": self.mean_link_recall,
            "mean_link_f1": self.mean_link_f1,
            "refusal_leakage_rate": self.refusal_leakage_rate,
            "forbidden_claim_leakage_rate": self.forbidden_claim_leakage_rate,
            "invalid_case_ids": list(self.invalid_case_ids),
            "results": [result.to_dict() for result in self.results],
        }


def load_answer_claim_eval_cases(path: str | Path) -> tuple[AnswerClaimEvalCase, ...]:
    """Project existing RAG K1 answer cases into the v1 claim-eval contract."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    raw_cases = data.get("cases")
    if not isinstance(raw_cases, list):
        raise ValueError("AnswerClaim eval fixture requires a 'cases' list")

    cases: list[AnswerClaimEvalCase] = []
    seen_case_ids: set[str] = set()
    for raw_case in raw_cases:
        if not isinstance(raw_case, dict):
            raise ValueError("AnswerClaim eval case must be an object")
        case_id = _required_text(raw_case.get("id"), "case id")
        if case_id in seen_case_ids:
            raise ValueError(f"duplicate AnswerClaim eval case: {case_id}")
        seen_case_ids.add(case_id)
        question = _required_text(raw_case.get("query"), f"question for {case_id}")
        expected_claims: list[AnswerClaimExpectedClaim] = []
        known_evidence_ids: list[str] = []
        for raw_claim in _list(raw_case.get("expected_claims")):
            if not isinstance(raw_claim, dict):
                raise ValueError(f"expected claim must be an object: {case_id}")
            claim_id = _required_text(raw_claim.get("id"), f"claim id for {case_id}")
            match_terms = _text_tuple(raw_claim.get("match_terms"))
            support_ids = _text_tuple(raw_claim.get("support_sources"))
            if not match_terms:
                raise ValueError(f"expected claim requires match_terms: {claim_id}")
            expected_claims.append(
                AnswerClaimExpectedClaim(
                    claim_id=claim_id,
                    match_terms=match_terms,
                    kind="factual",
                    support_evidence_ids=support_ids,
                )
            )
            known_evidence_ids.extend(support_ids)
        expected_sources = _text_tuple(raw_case.get("expected_sources"))
        known_evidence_ids.extend(expected_sources)
        cases.append(
            AnswerClaimEvalCase(
                case_id=case_id,
                question=question,
                answerable=bool(raw_case.get("answerable", True)),
                expected_claims=tuple(expected_claims),
                known_evidence_ids=_unique(known_evidence_ids),
                forbidden_claim_terms=_text_tuple(raw_case.get("forbidden_terms")),
            )
        )
    return tuple(cases)


def parse_answer_claim_producer_output(
    *,
    case: AnswerClaimEvalCase,
    final_answer: str,
    payload: Any,
    producer_id: str,
) -> ParsedAnswerClaimCandidate:
    """Strictly parse a producer payload; invalid output receives no quality score."""

    try:
        raw = _object(payload)
        if raw is not payload:
            raise ValueError("producer output must be a JSON object")
        refused = raw.get("refused")
        if not isinstance(refused, bool):
            raise ValueError("producer output requires boolean 'refused'")
        raw_claims = raw.get("claims")
        raw_links = raw.get("claim_links")
        if not isinstance(raw_claims, list) or not isinstance(raw_links, list):
            raise ValueError("producer output requires 'claims' and 'claim_links' lists")
        snapshot = build_answer_claim_snapshot(
            answer=final_answer,
            claims=tuple(_object(claim) for claim in raw_claims),
            claim_links=tuple(_object(link) for link in raw_links),
            known_evidence_ids=case.known_evidence_ids,
            producer=producer_id,
            status="validated",
        )
        return ParsedAnswerClaimCandidate(
            case_id=case.case_id,
            final_answer=final_answer,
            refused=refused,
            snapshot=snapshot,
        )
    except (TypeError, ValueError) as exc:
        return ParsedAnswerClaimCandidate(
            case_id=case.case_id,
            final_answer=final_answer,
            refused=None,
            snapshot=None,
            parse_error=f"{type(exc).__name__}: {exc}",
        )


def evaluate_answer_claim_case(
    case: AnswerClaimEvalCase,
    candidate: ParsedAnswerClaimCandidate,
) -> AnswerClaimEvalResult:
    if candidate.case_id != case.case_id:
        raise ValueError(
            f"AnswerClaim candidate {candidate.case_id!r} does not match case {case.case_id!r}"
        )
    if not candidate.schema_valid or candidate.snapshot is None or candidate.refused is None:
        return AnswerClaimEvalResult(
            case_id=case.case_id,
            schema_valid=False,
            parse_error=candidate.parse_error or "invalid structured claim output",
            answerability_correct=None,
            claim_precision=None,
            claim_recall=None,
            claim_f1=None,
            kind_accuracy=None,
            claim_coverage=None,
            unsupported_claim_rate=None,
            link_precision=None,
            link_recall=None,
            link_f1=None,
            refusal_leakage=None,
            forbidden_claim_leakage=None,
        )

    claims = candidate.snapshot.claims
    expected_by_id = {claim.claim_id: claim for claim in case.expected_claims}
    matched_expected: dict[str, str] = {}
    claim_to_expected: dict[str, str] = {}
    unsupported_claim_texts: list[str] = []
    kind_matches = 0

    for claim in claims:
        matches = [
            expected
            for expected in case.expected_claims
            if expected.claim_id not in matched_expected
            and _claim_matches(claim.text, expected)
        ]
        if not matches:
            unsupported_claim_texts.append(claim.text)
            continue
        expected = matches[0]
        matched_expected[expected.claim_id] = claim.id
        claim_to_expected[claim.id] = expected.claim_id
        kind_matches += int(claim.kind == expected.kind)

    expected_claim_count = len(case.expected_claims)
    matched_count = len(matched_expected)
    claim_precision = _ratio(matched_count, len(claims), empty=1.0 if not case.expected_claims else 0.0)
    claim_recall = _ratio(matched_count, expected_claim_count, empty=1.0)
    claim_f1 = _f1(claim_precision, claim_recall)
    kind_accuracy = _ratio(kind_matches, matched_count, empty=1.0 if not case.expected_claims else 0.0)
    unsupported_claim_rate = _ratio(
        len(unsupported_claim_texts),
        len(claims),
        empty=0.0,
    )

    expected_links = {
        (expected.claim_id, evidence_id)
        for expected in case.expected_claims
        for evidence_id in expected.support_evidence_ids
    }
    actual_links: set[tuple[str, str]] = set()
    for link in candidate.snapshot.claim_links:
        expected_claim_id = claim_to_expected.get(link.claim_id, f"unmatched:{link.claim_id}")
        if link.support_type in {"direct_support", "indirect_support"}:
            actual_links.add((expected_claim_id, link.evidence_id))
    true_links = actual_links & expected_links
    link_precision = _ratio(
        len(true_links),
        len(actual_links),
        empty=1.0 if not expected_links else 0.0,
    )
    link_recall = _ratio(len(true_links), len(expected_links), empty=1.0)
    link_f1 = _f1(link_precision, link_recall)

    forbidden_leakage = any(
        _normalize(term) in _normalize(claim.text)
        for term in case.forbidden_claim_terms
        for claim in claims
    )
    refusal_leakage = (not case.answerable) and (
        not candidate.refused or bool(claims)
    )
    answerability_correct = (
        (case.answerable and not candidate.refused)
        or (not case.answerable and candidate.refused and not claims)
    )
    missing_claim_ids = tuple(
        sorted(set(expected_by_id) - set(matched_expected))
    )

    return AnswerClaimEvalResult(
        case_id=case.case_id,
        schema_valid=True,
        parse_error="",
        answerability_correct=answerability_correct,
        claim_precision=_round(claim_precision),
        claim_recall=_round(claim_recall),
        claim_f1=_round(claim_f1),
        kind_accuracy=_round(kind_accuracy),
        claim_coverage=_round(claim_recall),
        unsupported_claim_rate=_round(unsupported_claim_rate),
        link_precision=_round(link_precision),
        link_recall=_round(link_recall),
        link_f1=_round(link_f1),
        refusal_leakage=refusal_leakage,
        forbidden_claim_leakage=forbidden_leakage,
        matched_claim_ids=tuple(sorted(matched_expected)),
        missing_claim_ids=missing_claim_ids,
        unsupported_claim_texts=tuple(unsupported_claim_texts),
    )


def evaluate_answer_claim_suite(
    cases: tuple[AnswerClaimEvalCase, ...],
    candidates: tuple[ParsedAnswerClaimCandidate, ...],
) -> AnswerClaimEvalSummary:
    candidate_by_id = {candidate.case_id: candidate for candidate in candidates}
    missing = [case.case_id for case in cases if case.case_id not in candidate_by_id]
    if missing:
        raise ValueError(f"Missing AnswerClaim candidates for: {', '.join(missing)}")
    if len(candidate_by_id) != len(candidates):
        raise ValueError("Duplicate AnswerClaim candidates")

    results = tuple(
        evaluate_answer_claim_case(case, candidate_by_id[case.case_id])
        for case in cases
    )
    valid = tuple(result for result in results if result.schema_valid)
    invalid_case_ids = tuple(result.case_id for result in results if not result.schema_valid)
    return AnswerClaimEvalSummary(
        total_cases=len(results),
        schema_valid_cases=len(valid),
        schema_parse_rate=_round(_ratio(len(valid), len(results), empty=0.0)),
        answerability_accuracy=_mean_optional(
            result.answerability_correct for result in valid
        ),
        mean_claim_precision=_mean_optional(result.claim_precision for result in valid),
        mean_claim_recall=_mean_optional(result.claim_recall for result in valid),
        mean_claim_f1=_mean_optional(result.claim_f1 for result in valid),
        mean_kind_accuracy=_mean_optional(result.kind_accuracy for result in valid),
        mean_claim_coverage=_mean_optional(result.claim_coverage for result in valid),
        mean_unsupported_claim_rate=_mean_optional(
            result.unsupported_claim_rate for result in valid
        ),
        mean_link_precision=_mean_optional(result.link_precision for result in valid),
        mean_link_recall=_mean_optional(result.link_recall for result in valid),
        mean_link_f1=_mean_optional(result.link_f1 for result in valid),
        refusal_leakage_rate=_mean_optional(result.refusal_leakage for result in valid),
        forbidden_claim_leakage_rate=_mean_optional(
            result.forbidden_claim_leakage for result in valid
        ),
        invalid_case_ids=invalid_case_ids,
        results=results,
    )


def run_answer_claim_producer(
    *,
    cases: tuple[AnswerClaimEvalCase, ...],
    answers: dict[str, str],
    producer: AnswerClaimProducer,
) -> tuple[ParsedAnswerClaimCandidate, ...]:
    candidates: list[ParsedAnswerClaimCandidate] = []
    for case in cases:
        if case.case_id not in answers:
            raise ValueError(f"Missing final answer for AnswerClaim case: {case.case_id}")
        final_answer = answers[case.case_id]
        request = AnswerClaimProducerInput(
            case_id=case.case_id,
            question=case.question,
            final_answer=final_answer,
            known_evidence_ids=case.known_evidence_ids,
        )
        try:
            payload = producer.produce(request)
        except Exception as exc:
            candidates.append(
                ParsedAnswerClaimCandidate(
                    case_id=case.case_id,
                    final_answer=final_answer,
                    refused=None,
                    snapshot=None,
                    parse_error=f"producer_failed:{type(exc).__name__}",
                )
            )
            continue
        candidates.append(
            parse_answer_claim_producer_output(
                case=case,
                final_answer=final_answer,
                payload=payload,
                producer_id=producer.producer_id,
            )
        )
    return tuple(candidates)


def deterministic_gold_payload(
    case: AnswerClaimEvalCase,
) -> tuple[str, AnswerClaimProducerOutput]:
    """Generate a perfect synthetic contract candidate for evaluator self-tests."""

    if not case.answerable:
        answer = "The available evidence is insufficient to answer this question."
        return answer, AnswerClaimProducerOutput(refused=True, claims=(), claim_links=())

    claim_texts = tuple(" ".join(claim.match_terms) for claim in case.expected_claims)
    answer = ". ".join(claim_texts)
    answer_hash = answer_content_hash(answer)
    claims: list[dict[str, Any]] = []
    links: list[dict[str, Any]] = []
    for expected, text in zip(case.expected_claims, claim_texts, strict=True):
        claim_id = deterministic_claim_id(answer_hash=answer_hash, claim_text=text)
        claims.append(
            {
                "id": claim_id,
                "text": text,
                "kind": expected.kind,
                "status": "asserted",
                "source": "application_supplied",
            }
        )
        links.extend(
            {
                "claim_id": claim_id,
                "evidence_id": evidence_id,
                "support_type": "direct_support",
                "confidence": 1.0,
            }
            for evidence_id in expected.support_evidence_ids
        )
    return answer, AnswerClaimProducerOutput(
        refused=False,
        claims=tuple(claims),
        claim_links=tuple(links),
    )


def _claim_matches(text: str, expected: AnswerClaimExpectedClaim) -> bool:
    normalized = _normalize(text)
    return bool(expected.match_terms) and all(
        _normalize(term) in normalized for term in expected.match_terms
    )


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def _required_text(value: Any, label: str) -> str:
    text = " ".join(str(value or "").split())
    if not text:
        raise ValueError(f"AnswerClaim eval requires {label}")
    return text


def _text_tuple(value: Any) -> tuple[str, ...]:
    return _unique(str(item) for item in _list(value) if str(item).strip())


def _unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value.strip() for value in values if value.strip()))


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ratio(numerator: int, denominator: int, *, empty: float) -> float:
    return numerator / denominator if denominator else empty


def _f1(precision: float, recall: float) -> float:
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _round(value: float) -> float:
    return round(value, 6)


def _mean_optional(values: Iterable[float | bool | None]) -> float | None:
    present = [float(value) for value in values if value is not None]
    return _round(sum(present) / len(present)) if present else None
