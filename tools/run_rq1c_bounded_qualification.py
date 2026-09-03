"""Run the RQ1-C bounded-preset live holdout qualification.

The runner intentionally knows only the runtime manifest (id/category/question).
Evaluation rubric/gold is a separate file and is never imported or accepted as a
runner argument. Each case drives the production active Claim Engine through a
throwaway SQLite database. The artifact stores bounded public metadata, hashes
research queries, and never stores page bodies or credentials.

The current production research run is evidence-only. Until a production chat
synthesis surface is captured, every case records an explicit unavailable answer
surface; the independent evaluator must therefore fail closed rather than grade
an Evidence Brief as though it were a learner-facing final answer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

from src.application.active_research_runtime import (  # noqa: E402
    ACTIVE_RESEARCH_BRIEF_KEY,
    ACTIVE_RESEARCH_METRICS_KEY,
)
from src.application.research_web_lookup_dispatch import (  # noqa: E402
    ClaimEngineDispatchWebLookupService,
)
from src.domain.runtime_entities import WebLookupRun  # noqa: E402
from src.infrastructure.sqlite.database import RuntimeDatabase  # noqa: E402
from src.repositories.web_lookup_repository import WebLookupRepository  # noqa: E402
from src.web.research.contracts import ResearchBudget, build_research_state  # noqa: E402
from src.web.research.state import attach_claim_engine_state  # noqa: E402

MANIFEST_SCHEMA_VERSION = "rq1c-bounded-holdout-manifest-v1"
ARTIFACT_SCHEMA_VERSION = "rq1c-bounded-qualification-runtime-v1"
DEFAULT_MANIFEST = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "research_quality"
    / "rq1c_bounded_holdout_manifest.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "research_quality" / "RQ1C_BOUNDED_QUALIFICATION_RUNTIME.json"
)
_ALLOWED_CASE_KEYS = {"id", "category", "question"}
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_text(value: str) -> str:
    normalized = " ".join(value.split()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _git_sha() -> str:
    configured = str(os.getenv("GITHUB_SHA") or "").strip().lower()
    if _HEX40.fullmatch(configured):
        return configured
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    value = completed.stdout.strip().lower()
    return value if _HEX40.fullmatch(value) else ""


def _load_manifest(path: Path) -> tuple[dict[str, str], ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported RQ1-C runtime manifest schema")
    if set(raw) != {"schema_version", "cases"}:
        raise ValueError("runtime manifest may contain only schema_version and cases")
    records = raw.get("cases")
    if not isinstance(records, list) or len(records) != 12:
        raise ValueError("RQ1-C bounded gate requires exactly 12 holdout cases")
    seen: set[str] = set()
    result: list[dict[str, str]] = []
    for record in records:
        if not isinstance(record, dict) or set(record) != _ALLOWED_CASE_KEYS:
            raise ValueError("runtime case may contain only id/category/question")
        case_id = str(record.get("id") or "").strip()
        category = str(record.get("category") or "").strip()
        question = str(record.get("question") or "").strip()
        if not case_id or case_id in seen or not category or not question:
            raise ValueError("invalid or duplicate RQ1-C runtime case")
        if len(question) > 2000:
            raise ValueError(f"RQ1-C question too long: {case_id}")
        seen.add(case_id)
        result.append({"id": case_id, "category": category, "question": question})
    return tuple(result)


def _active_context(reference_date: str) -> dict[str, Any]:
    state = build_research_state(
        mode="active",
        questions=(),
        claims=(),
        evidence=(),
        evidence_links=(),
        source_clusters=(),
        gaps=(),
        conflict_gaps=(),
        budget=ResearchBudget(
            max_candidates=20,
            max_reads=8,
            soft_timeout_seconds=45,
            hard_timeout_seconds=60,
            max_total_chars=16000,
        ),
        reference_date=reference_date,
        known_evidence_ids=(),
    )
    return attach_claim_engine_state(
        {
            "source_truth_version": 2,
            "run_attempt": 0,
            "external_data_policy": {"web_allowed": True, "reason": "allowed"},
        },
        state,
        known_evidence_ids=(),
    )


def _bounded(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _bounded_sequence(value: Any, *, item_limit: int, max_items: int) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [
        text
        for item in value[:max_items]
        if (text := _bounded(item, item_limit))
    ]


def _bounded_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _provider_audit(query_attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for attempt in query_attempts:
        query = str(attempt.get("query") or "")
        audit = attempt.get("provider_audit")
        outcomes: list[dict[str, Any]] = []
        if isinstance(audit, Mapping) and isinstance(audit.get("provider_outcomes"), list):
            for outcome in audit["provider_outcomes"]:
                if not isinstance(outcome, Mapping):
                    continue
                outcomes.append(
                    {
                        "provider": _bounded(outcome.get("provider"), 80),
                        "status": _bounded(outcome.get("status"), 80),
                        "reason": _bounded(outcome.get("reason"), 160),
                        "attempts": _bounded_int(outcome.get("attempts")),
                        "result_count": _bounded_int(outcome.get("result_count")),
                    }
                )
        provider_source = (
            audit.get("providers_attempted")
            if isinstance(audit, Mapping)
            else attempt.get("providers_attempted")
        )
        rows.append(
            {
                "query_sha256": _sha256_text(query) if query else "",
                "providers_attempted": _bounded_sequence(
                    provider_source,
                    item_limit=80,
                    max_items=12,
                ),
                "provider_outcomes": outcomes,
            }
        )
    return rows


def _source_rows(selected_sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in selected_sources:
        if not isinstance(source, Mapping):
            continue
        item = source.get("item")
        if not isinstance(item, Mapping):
            item = {}
        assessment = source.get("assessment")
        if not isinstance(assessment, Mapping):
            assessment = {}
        statuses: set[str] = set()
        extraction = source.get("extraction")
        if isinstance(extraction, Mapping):
            if status := _bounded(extraction.get("status"), 80):
                statuses.add(status)
        extractions = source.get("extractions")
        if isinstance(extractions, Mapping):
            for detail in extractions.values():
                if isinstance(detail, Mapping):
                    if status := _bounded(detail.get("status"), 80):
                        statuses.add(status)
        rows.append(
            {
                "candidate_id": _bounded(source.get("candidate_id"), 160),
                "title": _bounded(item.get("title"), 300),
                "url": _bounded(item.get("url"), 1600),
                "source": _bounded(item.get("source"), 160),
                "published_at": _bounded(item.get("published_at"), 80),
                "read_status": _bounded(source.get("read_status"), 80),
                "source_role": _bounded(assessment.get("source_role"), 80),
                "cluster_id": _bounded(
                    assessment.get("source_cluster_id") or assessment.get("cluster_id"),
                    160,
                ),
                "extraction_statuses": sorted(statuses),
            }
        )
    return rows


def _evidence_rows(brief: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = brief.get("eligible_evidence")
    if not isinstance(raw, list):
        return []
    rows: list[dict[str, Any]] = []
    for evidence in raw:
        if not isinstance(evidence, Mapping):
            continue
        strength = evidence.get("strength")
        if not isinstance(strength, (int, float)):
            strength = None
        rows.append(
            {
                "evidence_id": _bounded(
                    evidence.get("evidence_id") or evidence.get("id"), 160
                ),
                "claim_id": _bounded(evidence.get("claim_id"), 160),
                "relation": _bounded(evidence.get("relation"), 80),
                "strength": strength,
                "source_role": _bounded(evidence.get("source_role"), 80),
                "source_cluster_id": _bounded(
                    evidence.get("source_cluster_id") or evidence.get("cluster_id"),
                    160,
                ),
                "url": _bounded(
                    evidence.get("url") or evidence.get("source_url"), 1600
                ),
                "title": _bounded(
                    evidence.get("title") or evidence.get("source_title"), 300
                ),
                "published_at": _bounded(evidence.get("published_at"), 80),
                "locator": _bounded(evidence.get("locator"), 1000),
                "anchored_spans": _bounded_sequence(
                    evidence.get("anchored_spans"), item_limit=600, max_items=8
                ),
                "caveats": _bounded_sequence(
                    evidence.get("caveats"), item_limit=300, max_items=8
                ),
            }
        )
    return rows


def _brief_projection(brief: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": _bounded(brief.get("schema_version"), 100),
        "gate_reasons": _bounded_sequence(
            brief.get("gate_reasons"), item_limit=300, max_items=20
        ),
        "eligible_evidence": _evidence_rows(brief),
        "open_gap_ids": _bounded_sequence(
            brief.get("open_gap_ids"), item_limit=160, max_items=50
        ),
        "unresolved_conflict_count": (
            len(brief.get("unresolved_conflicts"))
            if isinstance(brief.get("unresolved_conflicts"), list)
            else 0
        ),
    }


def _observed_read_count(
    metrics: Mapping[str, Any], runtime: Mapping[str, Any]
) -> int:
    if "read_count" in metrics:
        return _bounded_int(metrics.get("read_count"))
    read_outcomes = runtime.get("read_outcomes")
    if not isinstance(read_outcomes, list):
        return 0
    return sum(
        isinstance(item, Mapping) and item.get("status") == "success"
        for item in read_outcomes
    )


def _cluster_ids(
    source_rows: list[dict[str, Any]], evidence_rows: list[dict[str, Any]]
) -> list[str]:
    values = {
        str(value)
        for value in (
            *[row.get("cluster_id") for row in source_rows],
            *[row.get("source_cluster_id") for row in evidence_rows],
        )
        if value
    }
    return sorted(values)


def _unavailable_answer_surface() -> dict[str, Any]:
    return {
        "status": "unavailable",
        "source": "none",
        "text": "",
        "content_sha256": "",
        "reason": "production_final_answer_not_captured",
    }


def _run_case(
    *,
    case: Mapping[str, str],
    repository: WebLookupRepository,
    service: ClaimEngineDispatchWebLookupService,
    reference_date: str,
) -> dict[str, Any]:
    started = time.monotonic()
    case_id = case["id"]
    run = repository.create(
        WebLookupRun(
            id=f"rq1c_{case_id}",
            query=case["question"],
            stage="planned",
            status="pending",
            research_context=_active_context(reference_date),
            max_items=5,
        )
    )
    try:
        completed = service.execute(run.id, raise_on_error=False)
    except Exception as exc:  # qualification records unexpected runtime failures
        return {
            "case_id": case_id,
            "category": case["category"],
            "question": case["question"],
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "runner_error_type": type(exc).__name__,
            "run": None,
            "answer": _unavailable_answer_surface(),
            "budget_contract_violations": [],
        }

    elapsed = round(time.monotonic() - started, 3)
    context = completed.research_context
    runtime = context.get("claim_engine_runtime")
    if not isinstance(runtime, Mapping):
        runtime = {}
    brief = context.get(ACTIVE_RESEARCH_BRIEF_KEY)
    if not isinstance(brief, Mapping):
        brief = {}
    metrics = context.get(ACTIVE_RESEARCH_METRICS_KEY)
    if not isinstance(metrics, Mapping):
        metrics = {}
    candidates = runtime.get("candidates")
    candidate_count = len(candidates) if isinstance(candidates, list) else 0
    model_calls = runtime.get("model_calls")
    model_call_count = len(model_calls) if isinstance(model_calls, list) else 0
    read_outcomes = runtime.get("read_outcomes")
    read_attempt_count = len(read_outcomes) if isinstance(read_outcomes, list) else 0
    read_count = _observed_read_count(metrics, runtime)
    selected_sources = [
        item for item in completed.selected_sources if isinstance(item, dict)
    ]
    source_rows = _source_rows(selected_sources)
    brief_projection = _brief_projection(brief)
    evidence_rows = brief_projection["eligible_evidence"]
    cluster_ids = _cluster_ids(source_rows, evidence_rows)
    violations: list[str] = []
    if candidate_count > 20:
        violations.append("candidate_budget_exceeded")
    if read_count > 8:
        violations.append("read_budget_exceeded")
    if model_call_count > 6:
        violations.append("model_call_budget_exceeded")
    if elapsed > 60:
        violations.append("hard_timeout_exceeded")

    return {
        "case_id": case_id,
        "category": case["category"],
        "question": case["question"],
        "reference_date": reference_date,
        "elapsed_seconds": elapsed,
        "runner_error_type": "",
        "run": {
            "status": completed.status,
            "provider_status": completed.provider_status,
            "stop_reason": completed.stop_reason,
            "stage": completed.stage,
        },
        "answer": _unavailable_answer_surface(),
        "search": {
            "attempt_count": len(completed.query_attempts),
            "audits": _provider_audit(completed.query_attempts),
        },
        "budget_observed": {
            "candidate_count": candidate_count,
            "read_count": read_count,
            "read_attempt_count": read_attempt_count,
            "model_call_count": model_call_count,
            "elapsed_seconds": elapsed,
        },
        "budget_contract_violations": violations,
        "sources": source_rows,
        "cluster_ids": cluster_ids,
        "gate": {
            "status": _bounded(brief.get("gate_status"), 80),
            "open_critical_claim_ids": _bounded_sequence(
                brief.get("open_critical_claim_ids"), item_limit=160, max_items=50
            ),
            "conditional_wording_required": brief.get(
                "conditional_wording_required"
            ),
        },
        "brief": brief_projection,
        "metrics": dict(metrics),
    }


def run_qualification(*, manifest_path: Path, output_path: Path) -> dict[str, Any]:
    load_dotenv(REPO_ROOT / ".env")
    cases = _load_manifest(manifest_path)
    git_sha = _git_sha()
    if not git_sha:
        raise RuntimeError("RQ1-C runtime qualification requires an exact git head")
    manifest_bytes = manifest_path.read_bytes()
    reference_date = datetime.now(timezone.utc).date().isoformat()
    artifact: dict[str, Any] = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "git_sha": git_sha,
        "started_at": _utc_now(),
        "completed_at": None,
        "manifest": {
            "path": str(manifest_path.relative_to(REPO_ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "case_count": len(cases),
        },
        "leakage_contract": {
            "runtime_case_keys": sorted(_ALLOWED_CASE_KEYS),
            "rubric_loaded_by_runner": False,
            "stores_page_bodies": False,
            "stores_research_query_text": False,
            "captures_production_final_answer": False,
        },
        "configured_budget": {
            "max_candidates": 20,
            "max_reads": 8,
            "max_model_calls": 6,
            "soft_timeout_seconds": 45,
            "hard_timeout_seconds": 60,
        },
        "cases": [],
        "summary": {},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="rq1c_bounded_qualification_")
    try:
        database = RuntimeDatabase(Path(tmp) / "qualification.sqlite")
        repository = WebLookupRepository(database)
        service = ClaimEngineDispatchWebLookupService(repository)
        for index, case in enumerate(cases, start=1):
            record = _run_case(
                case=case,
                repository=repository,
                service=service,
                reference_date=reference_date,
            )
            artifact["cases"].append(record)
            output_path.write_text(
                json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                f"[{index}/{len(cases)}] {case['id']}: "
                f"status={(record.get('run') or {}).get('status', 'runner_error')} · "
                f"elapsed={record['elapsed_seconds']}s",
                flush=True,
            )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    records = artifact["cases"]
    artifact["completed_at"] = _utc_now()
    artifact["summary"] = {
        "case_count": len(records),
        "runner_error_cases": sum(1 for item in records if item["runner_error_type"]),
        "budget_violation_cases": sum(
            1 for item in records if item.get("budget_contract_violations")
        ),
        "reviewable_answer_cases": sum(
            1
            for item in records
            if isinstance(item.get("answer"), Mapping)
            and item["answer"].get("status") == "available"
        ),
        "completed_runs": sum(
            1 for item in records if (item.get("run") or {}).get("status") == "completed"
        ),
        "partial_runs": sum(
            1 for item in records if (item.get("run") or {}).get("status") == "partial"
        ),
        "failed_runs": sum(
            1 for item in records if (item.get("run") or {}).get("status") == "failed"
        ),
        "qualification_decision": "NEEDS_INDEPENDENT_REVIEW",
    }
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    artifact = run_qualification(
        manifest_path=args.manifest.resolve(),
        output_path=args.output.resolve(),
    )
    print(json.dumps(artifact["summary"], ensure_ascii=False, sort_keys=True))
    structural_ok = (
        artifact["summary"]["case_count"] == 12
        and artifact["summary"]["runner_error_cases"] == 0
    )
    return 0 if structural_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
