"""Run the B5 real-SearXNG active runtime smoke and record the evidence.

Creates a real bounded active Claim Engine run against the local pinned
SearXNG (127.0.0.1:8080) and the configured model provider, executes one
full wave through the production executor, and persists a versioned
artifact recording query/provider/candidates/reads/clusters/Gate/UI
progress per the B5 frozen contract item 12.

Eval-only: uses a throwaway SQLite database; does not touch production
data, does not modify any runtime behavior.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

from src.api.routes.chat_routes import _research_progress  # noqa: E402
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

SMOKE_SCHEMA_VERSION = "research-quality-b5-active-smoke-v2"
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "research_quality" / "B5_ACTIVE_SEARXNG_SMOKE.json"
DEFAULT_QUESTION = (
    "What open-source license does the FastAPI project use?"
)


def _searxng_success(query_attempts: list[dict[str, Any]]) -> bool:
    """H6: prove SearXNG actually returned results, not merely that it was enabled.

    providers_attempted lists every enabled provider regardless of outcome, so
    success must come from the persisted per-provider outcomes.
    """
    for attempt in query_attempts:
        audit = attempt.get("provider_audit")
        if not isinstance(audit, Mapping):
            continue
        outcomes = audit.get("provider_outcomes")
        if not isinstance(outcomes, list):
            continue
        for outcome in outcomes:
            if not isinstance(outcome, Mapping):
                continue
            try:
                result_count = int(outcome.get("result_count") or 0)
            except (TypeError, ValueError):
                result_count = 0
            if (
                outcome.get("provider") == "searxng"
                and outcome.get("status") == "ok"
                and result_count > 0
            ):
                return True
    return False


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
            "external_data_policy": {
                "web_allowed": True,
                "reason": "allowed",
            },
        },
        state,
        known_evidence_ids=(),
    )


def run_smoke(*, question: str, output: Path) -> dict[str, Any]:
    load_dotenv(REPO_ROOT / ".env")
    reference_date = datetime.now(timezone.utc).date().isoformat()
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    import shutil

    tmp = tempfile.mkdtemp(prefix="b5_smoke_")
    try:
        database = RuntimeDatabase(Path(tmp) / "smoke.sqlite")
        repository = WebLookupRepository(database)
        run = repository.create(
            WebLookupRun(
                id="b5_active_searxng_smoke",
                query=question,
                stage="planned",
                status="pending",
                research_context=_active_context(reference_date),
                max_items=5,
            )
        )
        service = ClaimEngineDispatchWebLookupService(repository)
        completed = service.execute(run.id, raise_on_error=True)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    context = completed.research_context
    runtime = context.get("claim_engine_runtime", {})
    brief = context.get(ACTIVE_RESEARCH_BRIEF_KEY, {})
    metrics = context.get(ACTIVE_RESEARCH_METRICS_KEY, {})
    progress = _research_progress(completed)

    # B5-H4: read the persisted provenance field that production actually
    # stores ("providers_attempted") and require SearXNG to be present, so a
    # run served by other providers can never pass as a real-SearXNG smoke.
    providers = sorted(
        {
            provider
            for attempt in completed.query_attempts
            for provider in (attempt.get("providers_attempted") or [])
        }
    )
    searxng_attempted = any(
        "searxng" in (attempt.get("providers_attempted") or [])
        for attempt in completed.query_attempts
    )
    searxng_success = _searxng_success(completed.query_attempts)
    artifact: dict[str, Any] = {
        "schema_version": SMOKE_SCHEMA_VERSION,
        "started_at": started_at,
        "question": question,
        "reference_date": reference_date,
        "searxng_endpoint": "http://127.0.0.1:8080",
        "run": {
            "status": completed.status,
            "provider_status": completed.provider_status,
            "stop_reason": completed.stop_reason,
            "stage": completed.stage,
            "run_attempt": context.get("run_attempt"),
        },
        "search": {
            "query_attempt_count": len(completed.query_attempts),
            "providers": providers,
            "searxng_attempted": searxng_attempted,
            "searxng_success": searxng_success,
            "provider_audits": [
                {
                    "query": attempt.get("query"),
                    "providers_attempted": attempt.get("providers_attempted"),
                    "provider_audit": bool(attempt.get("provider_audit")),
                }
                for attempt in completed.query_attempts
            ],
        },
        "candidates": {
            "count": len(runtime.get("candidates", [])),
            "clusters": sorted(
                {
                    str(item.get("cluster_id") or "")
                    for item in runtime.get("candidates", [])
                    if item.get("cluster_id")
                }
            ),
        },
        "reads": {
            "selected_source_count": len(completed.selected_sources),
            "read_statuses": [
                item.get("read_status") for item in completed.selected_sources
            ],
            "extraction_statuses": [
                (item.get("extraction") or {}).get("status")
                for item in completed.selected_sources
            ],
        },
        "gate": {
            "status": brief.get("gate_status"),
            "eligible_evidence_count": len(brief.get("eligible_evidence", [])),
            "open_critical_claim_ids": brief.get("open_critical_claim_ids"),
            "stop_reason": completed.stop_reason,
            "budget": brief.get("budget"),
        },
        "metrics": metrics,
        "ui_progress": progress,
        "model_calls": {
            "count": len(runtime.get("model_calls", [])),
            "purposes": sorted(
                {
                    str(call.get("purpose") or "")
                    for call in runtime.get("model_calls", [])
                }
            ),
            "inflight_model_call": runtime.get("inflight_model_call"),
            "inflight_external_call": runtime.get("inflight_external_call"),
        },
        "brief_excerpt": {
            "summary": (brief.get("summary") or "")[:500],
            "conditional_wording_required": brief.get(
                "conditional_wording_required"
            ),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> int:
    args = _parser().parse_args()
    artifact = run_smoke(question=args.question, output=args.output.resolve())
    print(
        json.dumps(
            {
                "run": artifact["run"],
                "gate": artifact["gate"]["status"],
                "candidates": artifact["candidates"]["count"],
                "reads": artifact["reads"]["selected_source_count"],
                "clusters": artifact["candidates"]["clusters"],
                "model_calls": artifact["model_calls"]["count"],
                "searxng_attempted": artifact["search"]["searxng_attempted"],
                "searxng_success": artifact["search"]["searxng_success"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    gate = artifact["gate"]["status"]
    provenance_ok = artifact["search"]["searxng_success"] is True
    conditional_ok = (
        artifact["brief_excerpt"]["conditional_wording_required"]
        == (gate != "pass")
    )
    if not provenance_ok:
        print(
            json.dumps(
                {"error": "searxng did not produce a successful result-bearing search"},
                ensure_ascii=False,
            )
        )
    if not conditional_ok:
        print(
            json.dumps(
                {"error": "conditional_wording_required inconsistent with gate"},
                ensure_ascii=False,
            )
        )
    return 0 if gate in {"pass", "partial"} and provenance_ok and conditional_ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
