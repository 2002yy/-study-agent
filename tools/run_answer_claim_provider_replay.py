from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.rag.answer_claim_eval import load_answer_claim_eval_cases
from src.rag.answer_claim_provider_replay import (
    evaluate_recorded_provider_answer_claims,
    load_provider_report,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate Provider-authored K1e assertions through the record-only "
            "AnswerClaim contract without calling a Provider or writing ChatTurns."
        )
    )
    parser.add_argument(
        "--provider-report",
        default="output/rag-provider-replay.json",
        help="Completed real-provider K1e replay report.",
    )
    parser.add_argument(
        "--fixture",
        default="tests/fixtures/rag_eval/answer_cases.json",
        help="Fixed AnswerClaim/K1 answer-quality fixture.",
    )
    parser.add_argument(
        "--output",
        default="output/answer-claim-provider-replay.json",
        help="Record-only AnswerClaim evaluation report.",
    )
    parser.add_argument(
        "--run-label",
        default="",
        help="Optional operator label used to distinguish repeated stability runs.",
    )
    parser.add_argument(
        "--cost-cny",
        type=float,
        default=None,
        help="Optional operator-supplied billed cost in CNY; never inferred.",
    )
    return parser


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def compact_summary(report: dict[str, Any]) -> dict[str, Any]:
    quality = dict(report["quality"])
    quality.pop("results", None)
    return {
        "evaluation_kind": report["evaluation_kind"],
        "replay_kind": report["replay_kind"],
        "gating": report["gating"],
        "status": report["status"],
        "run_label": report["run_label"],
        "source_report": report["source_report"],
        "cost": report["cost"],
        "producer": report["producer"],
        "cases": report["cases"],
        "quality": quality,
        "boundaries": report["boundaries"],
    }


def main() -> int:
    args = _parser().parse_args()
    if args.cost_cny is not None and args.cost_cny < 0:
        raise ValueError("--cost-cny must be non-negative")

    cases = load_answer_claim_eval_cases(Path(args.fixture))
    provider_report, report_fingerprint = load_provider_report(args.provider_report)
    report = evaluate_recorded_provider_answer_claims(
        cases=cases,
        provider_report=provider_report,
        provider_report_fingerprint=report_fingerprint,
        run_label=args.run_label,
        cost_cny=args.cost_cny,
    )
    _write_report(Path(args.output), report)
    print(json.dumps(compact_summary(report), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
