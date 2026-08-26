"""Run the authorized RQCE-P0 live semantic projection and audit every call."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from dotenv import load_dotenv  # noqa: E402
from openai import OpenAI  # noqa: E402

from src.evals.research_quality import load_research_quality_eval_cases  # noqa: E402
from src.evals.research_quality_semantic_projector import (  # noqa: E402
    DEFAULT_MAX_PAGE_CHARS,
    DEFAULT_MAX_READS,
    LIVE_SEMANTIC_SCHEMA_VERSION,
    project_live_semantic_case,
)
from src.llm_client import get_provider_settings  # noqa: E402
from src.web.tool_gateway import GeneralWebGateway  # noqa: E402

DEFAULT_CASES = (
    REPO_ROOT / "tests" / "fixtures" / "research_quality" / "live_trap_cases.json"
)
DEFAULT_OBSERVATION = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_OBSERVATION.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_SEMANTIC_EVAL.json"
)


def run_live_semantic_projection(
    *,
    cases_path: Path,
    observation_path: Path,
    output_path: Path,
    selected_case_ids: set[str] | None = None,
    max_reads: int = DEFAULT_MAX_READS,
    max_page_chars: int = DEFAULT_MAX_PAGE_CHARS,
) -> dict[str, Any]:
    load_dotenv(REPO_ROOT / ".env")
    cases = load_research_quality_eval_cases(cases_path)
    if any(case.mode != "live" for case in cases):
        raise ValueError("semantic projection accepts only mode=live cases")
    if selected_case_ids:
        cases = tuple(case for case in cases if case.id in selected_case_ids)
        missing = selected_case_ids - {case.id for case in cases}
        if missing:
            raise ValueError(f"unknown live case ids: {', '.join(sorted(missing))}")

    observation_raw = observation_path.read_text(encoding="utf-8")
    observation = json.loads(observation_raw)
    if not isinstance(observation, dict):
        raise ValueError("live observation must be an object")
    observation_cases = {
        str(item.get("case_id")): item
        for item in observation.get("cases", [])
        if isinstance(item, dict) and str(item.get("case_id") or "")
    }
    missing_observations = {case.id for case in cases} - set(observation_cases)
    if missing_observations:
        raise ValueError(
            "live observation missing cases: "
            + ", ".join(sorted(missing_observations))
        )

    settings = get_provider_settings("deepseek")
    request_timeout_seconds = max(60.0, settings.timeout_seconds)
    client = OpenAI(
        api_key=settings.api_key,
        base_url=settings.base_url,
        timeout=request_timeout_seconds,
        max_retries=0,
    )
    gateway = GeneralWebGateway()

    def complete(messages: list[dict[str, str]]) -> str:
        response = client.chat.completions.create(
            model=settings.pro_model,
            messages=messages,
            temperature=0.0,
            max_tokens=4000,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    def read_page(url: str, limit: int) -> dict[str, Any]:
        return dict(gateway.read(url, max_chars=limit) or {})

    reference_date = _observation_date(observation)
    artifact: dict[str, Any] = {
        "schema_version": LIVE_SEMANTIC_SCHEMA_VERSION,
        "started_at": _utc_now(),
        "completed_at": None,
        "cases_fixture": _relative(cases_path),
        "observation_artifact": _relative(observation_path),
        "observation_sha256": sha256(observation_raw.encode("utf-8")).hexdigest(),
        "provider": "deepseek",
        "model_profile": "pro",
        "model": settings.pro_model,
        "reference_date": reference_date,
        "case_count": len(cases),
        "scope": {
            "eval_only": True,
            "stores_page_bodies": False,
            "stores_prompts": False,
            "stores_raw_model_output": False,
            "sends_eval_gold": False,
            "sends_chat_memory_local_files_or_attachments": False,
            "max_reads_per_case": max(0, min(int(max_reads), DEFAULT_MAX_READS)),
            "max_page_chars": max(
                500, min(int(max_page_chars), DEFAULT_MAX_PAGE_CHARS)
            ),
            "sdk_hidden_retries": 0,
            "application_attempts_per_logical_call": 2,
            "request_timeout_seconds": request_timeout_seconds,
            "keyword_relation_fallback": False,
        },
        "cases": [],
        "summary": {},
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for index, case in enumerate(cases, start=1):
        observed = observation_cases[case.id]
        if str(observed.get("question") or "") != case.gold.question:
            raise ValueError(f"observation question drift for {case.id}")
        result = project_live_semantic_case(
            case_id=case.id,
            question=case.gold.question,
            reference_date=reference_date,
            observation=observed,
            read_page=read_page,
            complete=complete,
            provider="deepseek",
            model=settings.pro_model,
            max_reads=max_reads,
            max_page_chars=max_page_chars,
        )
        artifact["cases"].append(result)
        _write_checkpoint(output_path, artifact)
        print(
            f"[{index}/{len(cases)}] {case.id}: {result['projection_status']} · "
            f"calls={len(result['external_calls'])} · "
            f"documents={len(result['documents'])}",
            flush=True,
        )

    records = artifact["cases"]
    calls = [call for record in records for call in record["external_calls"]]
    artifact["completed_at"] = _utc_now()
    artifact["summary"] = {
        "completed_cases": sum(
            1 for record in records if record["projection_status"] == "completed"
        ),
        "unavailable_cases": sum(
            1 for record in records if record["projection_status"] == "unavailable"
        ),
        "logical_calls": len({call["logical_call_id"] for call in calls}),
        "external_call_attempts": len(calls),
        "failed_attempts": sum(
            1 for call in calls if call["status"] == "attempted_failed"
        ),
        "projected_documents": sum(len(record["documents"]) for record in records),
    }
    _write_checkpoint(output_path, artifact)
    return artifact


def _write_checkpoint(path: Path, artifact: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _observation_date(observation: dict[str, Any]) -> str:
    completed = str(observation.get("completed_at") or "")
    if len(completed) >= 10:
        return completed[:10]
    return datetime.now(timezone.utc).date().isoformat()


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--observation", type=Path, default=DEFAULT_OBSERVATION)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--max-reads", type=int, default=DEFAULT_MAX_READS)
    parser.add_argument("--max-page-chars", type=int, default=DEFAULT_MAX_PAGE_CHARS)
    return parser


def main() -> int:
    args = _parser().parse_args()
    artifact = run_live_semantic_projection(
        cases_path=args.cases.resolve(),
        observation_path=args.observation.resolve(),
        output_path=args.output.resolve(),
        selected_case_ids=set(args.case) or None,
        max_reads=max(0, min(args.max_reads, DEFAULT_MAX_READS)),
        max_page_chars=max(
            500, min(args.max_page_chars, DEFAULT_MAX_PAGE_CHARS)
        ),
    )
    print(json.dumps(artifact["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if artifact["summary"]["unavailable_cases"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
