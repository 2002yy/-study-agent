"""Run the RQCE-P0 live cases through the real configured web gateway.

The artifact intentionally records only bounded operational metadata (queries,
providers, public URLs, titles, and read outcomes). It stores no page bodies,
credentials, or model output, and it never exposes eval gold beyond the public
question used as search input.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402

from src.evals.research_quality import load_research_quality_eval_cases  # noqa: E402
from src.web.source_assessment import assess_sources  # noqa: E402
from src.web.tool_gateway import GeneralWebGateway  # noqa: E402

DEFAULT_CASES = (
    REPO_ROOT / "tests" / "fixtures" / "research_quality" / "live_trap_cases.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_OBSERVATION.json"
LIVE_OBSERVATION_SCHEMA_VERSION = "research-quality-live-observation-v1"
_TOKEN_PATTERN = re.compile(r"[a-z0-9][a-z0-9.+-]*", re.IGNORECASE)
_STOPWORDS = {
    "a",
    "about",
    "according",
    "and",
    "are",
    "be",
    "before",
    "current",
    "currently",
    "did",
    "do",
    "does",
    "exact",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "most",
    "of",
    "official",
    "or",
    "published",
    "publicly",
    "the",
    "their",
    "them",
    "to",
    "what",
    "when",
    "which",
    "why",
    "will",
    "with",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _bounded_text(value: Any, limit: int) -> str:
    return " ".join(str(value or "").split())[:limit]


def _substantive_tokens(value: Any) -> set[str]:
    return {
        token.casefold()
        for token in _TOKEN_PATTERN.findall(str(value or ""))
        if token.casefold() not in _STOPWORDS and len(token) > 1
    }


def _candidate(record: dict[str, Any], *, question: str) -> dict[str, Any]:
    item = record.get("item") if isinstance(record.get("item"), dict) else {}
    assessment = (
        record.get("assessment") if isinstance(record.get("assessment"), dict) else {}
    )
    candidate_surface = " ".join(
        str(item.get(key) or "") for key in ("title", "url", "snippet")
    )
    overlap = _substantive_tokens(question) & _substantive_tokens(candidate_surface)
    return {
        "title": _bounded_text(item.get("title") or item.get("name"), 500),
        "url": _bounded_text(item.get("url"), 2000),
        "source": _bounded_text(item.get("source"), 200),
        "relevance": float(assessment.get("relevance") or 0.0),
        "directness": _bounded_text(assessment.get("directness"), 100),
        "legacy_worth_reading": bool(assessment.get("worth_reading")),
        "substantive_overlap_count": len(overlap),
        "benchmark_relevant": len(overlap) >= 2,
    }


def _read_observation(
    gateway: GeneralWebGateway,
    candidate: dict[str, Any],
    *,
    max_chars: int,
) -> dict[str, Any]:
    started = time.monotonic()
    try:
        payload = gateway.read(candidate["url"], max_chars=max_chars)
    except Exception as exc:
        return {
            "url": candidate["url"],
            "ok": False,
            "error_type": type(exc).__name__,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
    content = str(payload.get("content") or "")
    return {
        "url": _bounded_text(payload.get("url") or candidate["url"], 2000),
        "ok": bool(payload.get("ok")) and bool(content.strip()),
        "content_chars": len(content),
        "backend": _bounded_text(payload.get("backend"), 100),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def run_live_observation(
    *,
    cases_path: Path,
    output_path: Path,
    max_results: int,
    max_reads: int,
    max_chars: int,
    selected_case_ids: set[str] | None = None,
) -> dict[str, Any]:
    load_dotenv(REPO_ROOT / ".env")
    cases = load_research_quality_eval_cases(cases_path)
    if any(case.mode != "live" for case in cases):
        raise ValueError("live observation accepts only mode=live cases")
    if selected_case_ids:
        cases = tuple(case for case in cases if case.id in selected_case_ids)
        missing = selected_case_ids - {case.id for case in cases}
        if missing:
            raise ValueError(f"unknown live case ids: {', '.join(sorted(missing))}")

    gateway = GeneralWebGateway()
    artifact: dict[str, Any] = {
        "schema_version": LIVE_OBSERVATION_SCHEMA_VERSION,
        "started_at": _utc_now(),
        "completed_at": None,
        "cases_fixture": str(cases_path.relative_to(REPO_ROOT)).replace("\\", "/"),
        "case_count": len(cases),
        "cases": [],
        "summary": {},
        "scope": {
            "stores_page_bodies": False,
            "uses_model_synthesis": False,
            "produces_shadow_decision": False,
            "records_legacy_worth_reading": True,
            "reads_only_benchmark_relevant_candidates": True,
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for index, case in enumerate(cases, start=1):
        started = time.monotonic()
        search = gateway.search_detailed(
            case.gold.question,
            max_results=max_results,
        )
        raw_results = [
            item for item in search.get("results", []) if isinstance(item, dict)
        ]
        assessed, _rejected = assess_sources(
            raw_results,
            canonical_query=case.gold.question,
        )
        candidates = [
            _candidate(record, question=case.gold.question)
            for record in assessed
            if str(record.get("item", {}).get("url") or "").strip()
        ]
        relevant_candidates = [item for item in candidates if item["benchmark_relevant"]]
        reads = [
            _read_observation(gateway, item, max_chars=max_chars)
            for item in relevant_candidates[:max_reads]
        ]
        record = {
            "case_id": case.id,
            "category": case.category,
            "question": case.gold.question,
            "search_status": _bounded_text(search.get("status"), 100),
            "search_reason": _bounded_text(search.get("reason"), 200),
            "attempted_queries": [
                _bounded_text(value, 500)
                for value in search.get("attempted_queries", [])
            ],
            "providers_attempted": [
                _bounded_text(value, 100)
                for value in search.get("providers_attempted", [])
            ],
            "provider_errors": [
                _bounded_text(value, 300) for value in search.get("provider_errors", [])
            ],
            "candidate_count": len(candidates),
            "relevant_candidate_count": len(relevant_candidates),
            "candidates": candidates,
            "read_attempt_count": len(reads),
            "read_success_count": sum(1 for item in reads if item["ok"]),
            "reads": reads,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        artifact["cases"].append(record)
        output_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(
            f"[{index}/{len(cases)}] {case.id}: {record['search_status']} · "
            f"candidates={record['candidate_count']} · "
            f"relevant={record['relevant_candidate_count']} · "
            f"reads={record['read_success_count']}/{record['read_attempt_count']}",
            flush=True,
        )

    records = artifact["cases"]
    artifact["completed_at"] = _utc_now()
    artifact["summary"] = {
        "search_ok_cases": sum(1 for item in records if item["search_status"] == "ok"),
        "cases_with_candidates": sum(1 for item in records if item["candidate_count"] > 0),
        "cases_with_relevant_candidates": sum(
            1 for item in records if item["relevant_candidate_count"] > 0
        ),
        "cases_with_successful_read": sum(
            1 for item in records if item["read_success_count"] > 0
        ),
        "total_candidates": sum(item["candidate_count"] for item in records),
        "total_relevant_candidates": sum(
            item["relevant_candidate_count"] for item in records
        ),
        "total_read_attempts": sum(item["read_attempt_count"] for item in records),
        "total_successful_reads": sum(item["read_success_count"] for item in records),
    }
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return artifact


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--max-reads", type=int, default=3)
    parser.add_argument("--max-chars", type=int, default=6000)
    return parser


def main() -> int:
    args = _parser().parse_args()
    artifact = run_live_observation(
        cases_path=args.cases.resolve(),
        output_path=args.output.resolve(),
        max_results=max(1, min(args.max_results, 12)),
        max_reads=max(0, min(args.max_reads, 8)),
        max_chars=max(500, min(args.max_chars, 20000)),
        selected_case_ids=set(args.case) or None,
    )
    print(json.dumps(artifact["summary"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
