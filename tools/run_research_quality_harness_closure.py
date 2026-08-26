"""Close the RQCE-P0 live harness with truth-preserving retrieval diagnostics.

This tool joins three independent layers without changing production research behavior:
1) raw live search observation (provider results + production source assessment),
2) benchmark surface matching, and
3) an explicit independent manual candidate audit fixture.

The separation matters: a returned result that is not answer-relevant is not a
"relevance false negative" merely because a benchmark matcher rejects it. Only a
manually answer-relevant candidate rejected by the benchmark matcher may be labeled
BENCHMARK_MATCH_FALSE_NEGATIVE.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SEMANTIC = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_SEMANTIC_EVAL.json"
)
DEFAULT_OBSERVATION = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_OBSERVATION.json"
)
DEFAULT_MANUAL_AUDIT = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "research_quality"
    / "live_candidate_manual_audit.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_SEMANTIC_EVAL_V2.json"
)
DEFAULT_CLASSIFICATION = (
    REPO_ROOT / "docs" / "research_quality" / "P0_RETRIEVAL_FAILURE_CLASSIFICATION.json"
)

HARNESS_CLOSURE_SCHEMA_VERSION = "research-quality-harness-closure-v2"
MANUAL_AUDIT_SCHEMA_VERSION = "research-quality-candidate-manual-audit-v1"
_MANUAL_LABELS = {"ANSWER_RELEVANT", "TOPIC_ONLY", "OFF_TARGET"}
_FAILURE_TAXONOMY = (
    "QUERY_UNDERSPECIFIED",
    "PROVIDER_RECALL_MISS",
    "NO_ANSWER_RELEVANT_CANDIDATE",
    "BENCHMARK_MATCH_FALSE_NEGATIVE",
    "SOURCE_ROLE_MISMATCH",
    "READ_NOT_SCHEDULED",
    "READ_FAILED",
    "PROJECTION_REJECTED",
    "CLAIM_PROJECTION_UNAVAILABLE",
)


def _load_manual_audit(path: Path) -> dict[str, list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != MANUAL_AUDIT_SCHEMA_VERSION:
        raise ValueError("unsupported candidate manual audit schema")
    records = raw.get("cases")
    if not isinstance(records, list):
        raise ValueError("candidate manual audit requires cases list")
    result: dict[str, list[str]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("candidate manual audit case must be object")
        case_id = str(record.get("case_id") or "")
        labels = record.get("labels")
        if not case_id or case_id in result or not isinstance(labels, list):
            raise ValueError("invalid or duplicate candidate manual audit case")
        normalized = [str(value or "") for value in labels]
        if any(label not in _MANUAL_LABELS for label in normalized):
            raise ValueError("unknown candidate manual audit label")
        result[case_id] = normalized
    return result


def _candidate_audit_rows(
    observation: dict[str, Any],
    manual_labels: dict[str, list[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen_cases: set[str] = set()
    for case in observation.get("cases", []):
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "")
        candidates = case.get("candidates")
        if not case_id or not isinstance(candidates, list):
            continue
        labels = manual_labels.get(case_id)
        if labels is None or len(labels) != len(candidates):
            raise ValueError(f"manual candidate audit count mismatch: {case_id}")
        seen_cases.add(case_id)
        for index, (candidate, manual_label) in enumerate(zip(candidates, labels), start=1):
            if not isinstance(candidate, dict):
                raise ValueError(f"candidate must be object: {case_id}#{index}")
            rows.append(
                {
                    "case_id": case_id,
                    "candidate_index": index,
                    "title": str(candidate.get("title") or ""),
                    "url": str(candidate.get("url") or ""),
                    "provider_source": str(candidate.get("source") or ""),
                    "production_worth_reading": bool(
                        candidate.get("legacy_worth_reading")
                    ),
                    "production_relevance": float(candidate.get("relevance") or 0.0),
                    "production_directness": str(candidate.get("directness") or ""),
                    "benchmark_surface_match": bool(candidate.get("benchmark_relevant")),
                    "benchmark_overlap_count": int(
                        candidate.get("substantive_overlap_count") or 0
                    ),
                    "manual_audit_label": manual_label,
                }
            )
    missing = set(manual_labels) - seen_cases
    if missing:
        raise ValueError(f"manual candidate audit references unknown cases: {sorted(missing)}")
    return rows


def _candidate_counts(rows: list[dict[str, Any]], case_id: str) -> dict[str, int]:
    scoped = [row for row in rows if row["case_id"] == case_id]
    return {
        "production_worth_reading_candidate_count": sum(
            1 for row in scoped if row["production_worth_reading"]
        ),
        "benchmark_relevant_candidate_count": sum(
            1 for row in scoped if row["benchmark_surface_match"]
        ),
        "manual_answer_relevant_candidate_count": sum(
            1 for row in scoped if row["manual_audit_label"] == "ANSWER_RELEVANT"
        ),
        "manual_topic_only_candidate_count": sum(
            1 for row in scoped if row["manual_audit_label"] == "TOPIC_ONLY"
        ),
        "manual_off_target_candidate_count": sum(
            1 for row in scoped if row["manual_audit_label"] == "OFF_TARGET"
        ),
    }


def _funnel(
    observation: dict[str, Any],
    case_record: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    documents = case_record.get("documents", [])
    read_audit = case_record.get("reads", [])
    successful = sum(1 for entry in read_audit if entry.get("status") == "read_ok")
    eligible = sum(
        1
        for doc in documents
        if doc.get("source_role")
        in {"primary", "authoritative_secondary", "independent_secondary"}
    )
    queries = observation.get("attempted_queries", [])
    case_id = str(case_record.get("case_id") or "")
    counts = _candidate_counts(candidate_rows, case_id)
    return {
        "attempted_queries": len(queries) if isinstance(queries, list) else 0,
        "returned_candidate_count": int(observation.get("candidate_count") or 0),
        **counts,
        "source_role_fit_candidate_count": len(documents),
        "scheduled_read_count": len(read_audit),
        "successful_read_count": successful,
        "projected_document_count": len(documents),
        "eligible_evidence_count": eligible,
    }


def _typed_failure_reason(case_record: dict[str, Any]) -> str:
    base = str(case_record.get("failure_reason") or "")
    audits = case_record.get("external_calls", [])
    if not audits:
        return base
    error_types = sorted(
        {
            str(a.get("error_type") or "")
            for a in audits
            if a.get("status") == "attempted_failed" and a.get("error_type")
        }
    )
    if error_types:
        return f"{base}:{','.join(error_types)}" if base else ",".join(error_types)
    return base


def _retrieval_truth_failure(funnel: dict[str, Any]) -> str | None:
    queries = funnel["attempted_queries"]
    returned = funnel["returned_candidate_count"]
    manual_answer = funnel["manual_answer_relevant_candidate_count"]
    benchmark = funnel["benchmark_relevant_candidate_count"]
    if queries == 0:
        return "QUERY_UNDERSPECIFIED"
    if returned == 0:
        return "PROVIDER_RECALL_MISS"
    if manual_answer == 0:
        return "NO_ANSWER_RELEVANT_CANDIDATE"
    if benchmark == 0:
        return "BENCHMARK_MATCH_FALSE_NEGATIVE"
    return None


def _classify_case(
    case_record: dict[str, Any], funnel: dict[str, Any]
) -> tuple[str, list[str]]:
    retrieval_failure = _retrieval_truth_failure(funnel)
    status = str(case_record.get("projection_status") or "")
    if status == "unavailable":
        secondary = [retrieval_failure] if retrieval_failure else []
        return "CLAIM_PROJECTION_UNAVAILABLE", secondary
    if retrieval_failure:
        return retrieval_failure, []

    scheduled = funnel["scheduled_read_count"]
    successful = funnel["successful_read_count"]
    projected = funnel["projected_document_count"]
    if scheduled == 0:
        return "READ_NOT_SCHEDULED", []
    if successful == 0:
        return "READ_FAILED", []
    if projected == 0:
        return "PROJECTION_REJECTED", []
    return "COMPLETED_WITH_EVIDENCE", []


def close_harness(
    *,
    semantic_path: Path,
    observation_path: Path,
    output_path: Path,
    classification_path: Path,
    manual_audit_path: Path = DEFAULT_MANUAL_AUDIT,
) -> tuple[dict[str, Any], dict[str, Any]]:
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
    manual_labels = _load_manual_audit(manual_audit_path)
    candidate_rows = _candidate_audit_rows(observation, manual_labels)
    obs_by_id = {
        str(c.get("case_id")): c
        for c in observation.get("cases", [])
        if isinstance(c, dict) and c.get("case_id")
    }

    cases: list[dict[str, Any]] = []
    classification_rows: list[dict[str, Any]] = []
    for case_record in semantic.get("cases", []):
        case_id = str(case_record.get("case_id") or "")
        obs = obs_by_id.get(case_id, {})
        funnel = _funnel(obs, case_record, candidate_rows)
        typed = _typed_failure_reason(case_record)
        stop = (
            "projection_completed"
            if case_record.get("projection_status") == "completed"
            else "projection_exhausted_no_fallback"
        )
        transcript = case_record.get("transcript")
        if transcript is None:
            transcript = _transcript_from_obs(case_record, obs)
        augmented = dict(case_record)
        augmented["retrieval_funnel"] = funnel
        augmented["typed_failure_reason"] = typed
        augmented["stop_reason"] = stop
        augmented["transcript"] = transcript
        cases.append(augmented)

        primary, secondary = _classify_case(augmented, funnel)
        classification_rows.append(
            {
                "case_id": case_id,
                "projection_status": case_record.get("projection_status"),
                "primary_failure_type": primary,
                "secondary_failure_types": secondary,
                "funnel": funnel,
                "typed_failure_reason": typed,
                "stop_reason": stop,
            }
        )

    artifact = dict(semantic)
    artifact["schema_version"] = HARNESS_CLOSURE_SCHEMA_VERSION
    artifact["derived_from"] = {
        "semantic_artifact": str(semantic_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "observation_artifact": str(observation_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "manual_candidate_audit": str(manual_audit_path.relative_to(REPO_ROOT)).replace("\\", "/"),
    }
    artifact["cases"] = cases
    artifact["summary"] = _summary(cases)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    taxonomy_counts: dict[str, int] = {t: 0 for t in _FAILURE_TAXONOMY}
    taxonomy_counts["COMPLETED_WITH_EVIDENCE"] = 0
    for row in classification_rows:
        taxonomy_counts[row["primary_failure_type"]] = (
            taxonomy_counts.get(row["primary_failure_type"], 0) + 1
        )
    classification = {
        "schema_version": HARNESS_CLOSURE_SCHEMA_VERSION,
        "derived_from": artifact["derived_from"],
        "rows": classification_rows,
        "candidate_audit_rows": candidate_rows,
        "taxonomy_counts": taxonomy_counts,
        "funnel_aggregate": _aggregate_funnel(classification_rows),
    }
    classification_path.parent.mkdir(parents=True, exist_ok=True)
    classification_path.write_text(
        json.dumps(classification, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact, classification


def _transcript_from_obs(
    case_record: dict[str, Any], obs: dict[str, Any]
) -> dict[str, Any]:
    queries = [str(q) for q in obs.get("attempted_queries", []) if str(q).strip()]
    return {
        "case_id": case_record.get("case_id"),
        "reference_date": case_record.get("reference_date"),
        "queries": queries,
        "searches": max(1, len(queries)),
        "reads": [],
        "cited_doc_ids": [],
        "addressed_claim_surfaces": [],
        "question_surface": case_record.get("question", ""),
        "projected_claims": case_record.get("projected_claims", []),
        "projected_claim_evidence": [],
        "llm_calls": len(case_record.get("external_calls", [])),
        "elapsed_seconds": float(obs.get("elapsed_seconds") or 0.0),
        "closed": str(obs.get("search_status") or "") == "ok",
    }


def _summary(cases: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(cases)
    completed = sum(1 for c in cases if c.get("projection_status") == "completed")
    unavailable = sum(1 for c in cases if c.get("projection_status") == "unavailable")
    with_funnel = sum(1 for c in cases if c.get("retrieval_funnel") is not None)
    with_transcript = sum(1 for c in cases if c.get("transcript") is not None)
    with_typed = sum(1 for c in cases if c.get("typed_failure_reason") is not None)
    attempts = [
        call
        for case in cases
        for call in case.get("external_calls", [])
        if isinstance(call, dict)
    ]
    logical_ids = {
        str(call.get("logical_call_id") or "")
        for call in attempts
        if str(call.get("logical_call_id") or "")
    }
    return {
        "total_cases": total,
        "completed_cases": completed,
        "unavailable_cases": unavailable,
        "logical_calls": len(logical_ids),
        "external_call_attempts": len(attempts),
        "failed_attempts": sum(
            1 for call in attempts if call.get("status") == "attempted_failed"
        ),
        "projected_documents": sum(len(case.get("documents", [])) for case in cases),
        "artifact_completeness": f"{with_funnel}/{total} funnel · {with_transcript}/{total} transcript · {with_typed}/{total} typed_reason",
        "harness_status": "PASS / COMPLETE"
        if with_funnel == total and with_transcript == total
        else "INCOMPLETE",
    }


def _aggregate_funnel(rows: list[dict[str, Any]]) -> dict[str, int]:
    agg = {
        "attempted_queries": 0,
        "returned_candidate_count": 0,
        "production_worth_reading_candidate_count": 0,
        "benchmark_relevant_candidate_count": 0,
        "manual_answer_relevant_candidate_count": 0,
        "manual_topic_only_candidate_count": 0,
        "manual_off_target_candidate_count": 0,
        "source_role_fit_candidate_count": 0,
        "scheduled_read_count": 0,
        "successful_read_count": 0,
        "projected_document_count": 0,
        "eligible_evidence_count": 0,
    }
    for row in rows:
        funnel = row.get("funnel", {})
        for key in agg:
            agg[key] += int(funnel.get(key, 0))
    return agg


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--semantic", type=Path, default=DEFAULT_SEMANTIC)
    parser.add_argument("--observation", type=Path, default=DEFAULT_OBSERVATION)
    parser.add_argument("--manual-audit", type=Path, default=DEFAULT_MANUAL_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--classification", type=Path, default=DEFAULT_CLASSIFICATION)
    return parser


def main() -> int:
    args = _parser().parse_args()
    artifact, classification = close_harness(
        semantic_path=args.semantic.resolve(),
        observation_path=args.observation.resolve(),
        manual_audit_path=args.manual_audit.resolve(),
        output_path=args.output.resolve(),
        classification_path=args.classification.resolve(),
    )
    print(
        "wrote",
        str(args.output.relative_to(REPO_ROOT)).replace("\\", "/"),
        "·",
        artifact["summary"]["artifact_completeness"],
    )
    print("taxonomy:", json.dumps(classification["taxonomy_counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
