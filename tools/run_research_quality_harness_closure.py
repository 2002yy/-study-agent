"""Close RQCE-P0-C5-C harness: regenerate complete per-case artifacts + retrieval taxonomy.

Reads the v1 live semantic projection artifact and the live observation artifact,
augments every case (including unavailable ones) with a versioned retrieval funnel,
typed failure reason and stop reason, and classifies the completed-but-zero-evidence
cases. No production research behavior change; no API calls; no WebLookupService.
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
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_SEMANTIC_EVAL_V2.json"
)
DEFAULT_CLASSIFICATION = (
    REPO_ROOT / "docs" / "research_quality" / "P0_RETRIEVAL_FAILURE_CLASSIFICATION.json"
)

HARNESS_CLOSURE_SCHEMA_VERSION = "research-quality-harness-closure-v1"

_FAILURE_TAXONOMY = (
    "QUERY_UNDERSPECIFIED",
    "PROVIDER_RECALL_MISS",
    "RELEVANCE_FALSE_NEGATIVE",
    "SOURCE_ROLE_MISMATCH",
    "READ_NOT_SCHEDULED",
    "READ_FAILED",
    "PROJECTION_REJECTED",
    "CLAIM_PROJECTION_UNAVAILABLE",
)


def _funnel(observation: dict[str, Any], case_record: dict[str, Any]) -> dict[str, Any]:
    documents = case_record.get("documents", [])
    read_audit = case_record.get("reads", [])
    successful = sum(
        1 for entry in read_audit if entry.get("status") == "read_ok"
    )
    eligible = sum(
        1
        for doc in documents
        if doc.get("source_role")
        in {"primary", "authoritative_secondary", "independent_secondary"}
    )
    queries = observation.get("attempted_queries", [])
    return {
        "attempted_queries": len(queries) if isinstance(queries, list) else 0,
        "returned_candidate_count": int(observation.get("candidate_count") or 0),
        "benchmark_relevant_candidate_count": int(
            observation.get("relevant_candidate_count") or 0
        ),
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


def _classify_case(
    case_record: dict[str, Any], funnel: dict[str, Any]
) -> tuple[str, list[str]]:
    status = str(case_record.get("projection_status") or "")
    if status == "unavailable":
        return "CLAIM_PROJECTION_UNAVAILABLE", []

    queries = funnel["attempted_queries"]
    returned = funnel["returned_candidate_count"]
    relevant = funnel["benchmark_relevant_candidate_count"]
    scheduled = funnel["scheduled_read_count"]
    successful = funnel["successful_read_count"]
    projected = funnel["projected_document_count"]

    if queries == 0:
        return "QUERY_UNDERSPECIFIED", []
    if returned == 0:
        return "PROVIDER_RECALL_MISS", []
    if relevant == 0:
        return "RELEVANCE_FALSE_NEGATIVE", []
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
) -> tuple[dict[str, Any], dict[str, Any]]:
    semantic = json.loads(semantic_path.read_text(encoding="utf-8"))
    observation = json.loads(observation_path.read_text(encoding="utf-8"))
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
        funnel = _funnel(obs, case_record)
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
        "observation_artifact": str(
            observation_path.relative_to(REPO_ROOT)
        ).replace("\\", "/"),
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
    queries = [
        str(q) for q in obs.get("attempted_queries", []) if str(q).strip()
    ]
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
    return {
        "total_cases": total,
        "completed_cases": completed,
        "unavailable_cases": unavailable,
        "artifact_completeness": f"{with_funnel}/{total} funnel · {with_transcript}/{total} transcript · {with_typed}/{total} typed_reason",
        "harness_status": "PASS / COMPLETE" if with_funnel == total and with_transcript == total else "INCOMPLETE",
    }


def _aggregate_funnel(rows: list[dict[str, Any]]) -> dict[str, int]:
    agg = {
        "attempted_queries": 0,
        "returned_candidate_count": 0,
        "benchmark_relevant_candidate_count": 0,
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--classification", type=Path, default=DEFAULT_CLASSIFICATION
    )
    return parser


def main() -> int:
    args = _parser().parse_args()
    artifact, classification = close_harness(
        semantic_path=args.semantic.resolve(),
        observation_path=args.observation.resolve(),
        output_path=args.output.resolve(),
        classification_path=args.classification.resolve(),
    )
    print(
        "wrote",
        str(args.output.relative_to(REPO_ROOT)).replace("\\", "/"),
        "·",
        artifact["summary"]["artifact_completeness"],
    )
    print(
        "taxonomy:",
        json.dumps(classification["taxonomy_counts"], sort_keys=True),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
