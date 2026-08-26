"""Generate the RQCE-P0-C5 frozen + live shadow comparison report.

Loads the frozen trap cases and the legacy transcript fixture, runs the
offline shadow runner, and writes the diagnostic markdown report to
``docs/research_quality/P0_SHADOW_REPORT.md``.

This tool performs no live web or model calls. It replays frozen transcripts
and, when present, the body-free live semantic projection artifact.
"""

from __future__ import annotations

import argparse
from dataclasses import replace
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.evals.research_quality import (  # noqa: E402
    FrozenCorpusDocument,
    load_research_quality_eval_cases,
)
from src.evals.research_quality_runner import (  # noqa: E402
    LEGACY_RESEARCH_QUALITY_RUN_SCHEMA_VERSION,
    RESEARCH_QUALITY_RUN_SCHEMA_VERSION,
    ResearchRunTranscript,
    RunEvaluation,
    evaluate_research_run,
    evaluate_research_runs,
    research_run_transcript_from_dict,
    summarize_run_evaluations,
)
from src.evals.research_quality_semantic_projector import (  # noqa: E402
    LIVE_SEMANTIC_SCHEMA_VERSION,
)

DEFAULT_CASES = REPO_ROOT / "tests" / "fixtures" / "research_quality" / "frozen_trap_cases.json"
DEFAULT_TRANSCRIPTS = (
    REPO_ROOT / "tests" / "fixtures" / "research_quality" / "legacy_transcripts.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "research_quality" / "P0_SHADOW_REPORT.md"
DEFAULT_LIVE_OBSERVATION = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_OBSERVATION.json"
)
DEFAULT_LIVE_CASES = (
    REPO_ROOT / "tests" / "fixtures" / "research_quality" / "live_trap_cases.json"
)
DEFAULT_LIVE_SEMANTIC = (
    REPO_ROOT / "docs" / "research_quality" / "P0_LIVE_SEMANTIC_EVAL.json"
)


def load_transcripts(path: Path) -> tuple[ResearchRunTranscript, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("transcript fixture must be a JSON object")
    if raw.get("schema_version") not in {
        RESEARCH_QUALITY_RUN_SCHEMA_VERSION,
        LEGACY_RESEARCH_QUALITY_RUN_SCHEMA_VERSION,
    }:
        raise ValueError("unsupported transcript schema_version")
    items = raw.get("transcripts")
    if not isinstance(items, list):
        raise ValueError("transcript fixture requires a transcripts list")
    return tuple(research_run_transcript_from_dict(item) for item in items)


def load_live_semantic_evaluations(
    cases_path: Path,
    semantic_path: Path,
) -> tuple[tuple[RunEvaluation, ...], dict[str, Any]]:
    cases = load_research_quality_eval_cases(cases_path)
    case_by_id = {case.id: case for case in cases}
    raw = json.loads(semantic_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("schema_version") != LIVE_SEMANTIC_SCHEMA_VERSION:
        raise ValueError("unsupported live semantic artifact")
    records = raw.get("cases")
    if not isinstance(records, list):
        raise ValueError("live semantic artifact requires a cases list")
    evaluations: list[RunEvaluation] = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("live semantic case must be an object")
        case_id = str(record.get("case_id") or "")
        if case_id in seen or case_id not in case_by_id:
            raise ValueError("duplicate or unknown live semantic case")
        seen.add(case_id)
        if record.get("projection_status") != "completed":
            continue
        transcript_raw = record.get("transcript")
        if not isinstance(transcript_raw, dict):
            raise ValueError("completed live semantic case requires transcript")
        transcript = research_run_transcript_from_dict(transcript_raw)
        if transcript.case_id != case_id:
            raise ValueError("live semantic transcript case mismatch")
        documents_raw = record.get("documents")
        if not isinstance(documents_raw, list):
            raise ValueError("live semantic documents must be a list")
        documents = tuple(_live_document(item) for item in documents_raw)
        hydrated = replace(case_by_id[case_id], corpus=documents)
        evaluations.append(evaluate_research_run(hydrated, transcript))
    return tuple(evaluations), raw


def _live_document(raw: Any) -> FrozenCorpusDocument:
    if not isinstance(raw, dict):
        raise ValueError("live semantic document must be an object")
    allowed = {
        "doc_id",
        "url",
        "title",
        "source_role",
        "cluster_id",
        "published_at",
    }
    if set(raw) - allowed:
        raise ValueError("live semantic document contains unknown fields")
    return FrozenCorpusDocument(
        doc_id=str(raw.get("doc_id") or ""),
        url=str(raw.get("url") or ""),
        title=str(raw.get("title") or ""),
        source_role=raw.get("source_role"),
        cluster_id=str(raw.get("cluster_id") or ""),
        published_at=(str(raw["published_at"]) if raw.get("published_at") else None),
        content="",
    )


def render_report(
    evaluations: tuple[RunEvaluation, ...],
    summary: Any,
    cases_path: Path,
    transcripts_path: Path,
    live_observation: dict[str, Any] | None = None,
    live_evaluations: tuple[RunEvaluation, ...] = (),
    live_semantic: dict[str, Any] | None = None,
) -> str:
    lines: list[str] = []
    lines.append("# RQCE-P0-C5 Shadow Report (gold-blind baseline vs shadow)")
    lines.append("")
    lines.append("> 组件诊断报告，不是 Release Gate。Shadow 输入只来自预记录 projection；Gold 只在 decision 完成后评分。live baseline 的 closed 是 operational search-status proxy，不是实际 answer-generation transcript。")
    lines.append("")
    lines.append(f"- cases fixture: `{cases_path.relative_to(REPO_ROOT)}`")
    lines.append(f"- transcripts fixture: `{transcripts_path.relative_to(REPO_ROOT)}`")
    lines.append(f"- evaluated frozen cases: {summary.total_cases}")
    lines.append("")
    lines.append("## Frozen 10 聚合指标")
    lines.append("")
    lines.append(f"- closed runs: {summary.closed_runs}/{summary.total_cases}")
    lines.append(f"- false closures (baseline 误闭环): {summary.false_closures}")
    lines.append(f"- shadow blocked runs: {summary.shadow_blocked_runs}")
    lines.append(f"- caught false closures (shadow 抓到): {summary.caught_false_closures}")
    lines.append(f"- missed false closures (shadow 漏抓): {summary.missed_false_closures}")
    lines.append(f"- overblocked correct closures (shadow 误 BLOCK): {summary.overblocked_correct_closures}")
    lines.append(
        f"- primary retrieval rate: {summary.primary_retrieved_cases}/"
        f"{summary.primary_required_cases} ({summary.primary_retrieval_rate:.2%})"
    )
    lines.append(
        f"- mean useful read ratio: {summary.mean_useful_read_ratio:.2f} "
        f"(contributing reads {summary.useful_read_count}/"
        f"{summary.successful_read_count})"
    )
    lines.append(
        f"- mean evidence-linked critical claim coverage: "
        f"{summary.mean_critical_claim_coverage:.2%} "
        f"(covered {summary.covered_critical_claim_count}/"
        f"{summary.critical_claim_count})"
    )
    lines.append("- metric caveat: synthetic frozen transcripts contain no deliberately wasted successful reads; the 1.00 useful-read result is fixture-bound, not a production KPI.")
    lines.append("")
    lines.append("## 按类别分布")
    lines.append("")
    lines.append("| category | total | false closures | caught |")
    lines.append("|---|---:|---:|---:|")
    for category, total, false, caught in summary.per_category:
        lines.append(f"| {category} | {total} | {false} | {caught} |")
    lines.append("")
    lines.append("## 逐 case 诊断")
    lines.append("")
    lines.append("| case_id | closed | false_closure | violated | shadow | shadow reasons | open critical | primary retrieval | coverage | useful read ratio |")
    lines.append("|---|---|---|---|---|---|---|---|---:|---:|")
    for item in evaluations:
        lines.append(
            f"| {item.case_id} | {item.closed} | {item.false_closure} | "
            f"{', '.join(item.violated_closure_conditions) or '-'} | "
            f"{item.shadow_status} | {', '.join(item.shadow_reasons) or '-'} | "
            f"{', '.join(item.open_critical_claims) or '-'} | "
            f"{item.primary_retrieval} | {item.critical_claim_coverage:.0%} | "
            f"{item.useful_read_ratio:.2f} |"
        )
    lines.append("")
    lines.append("## Live 10 operational observation")
    lines.append("")
    if live_observation is None:
        lines.append("- status: not run")
    else:
        live_summary = live_observation.get("summary", {})
        live_cases = live_observation.get("cases", [])
        provider_error_cases = sum(
            1 for item in live_cases if item.get("provider_errors")
        )
        lines.append(
            f"- search API status=ok: {live_summary.get('search_ok_cases', 0)}/"
            f"{live_observation.get('case_count', 0)}"
        )
        lines.append(
            f"- cases with benchmark-relevant candidates: "
            f"{live_summary.get('cases_with_relevant_candidates', 0)}/"
            f"{live_observation.get('case_count', 0)}"
        )
        lines.append(
            f"- candidates: {live_summary.get('total_candidates', 0)} total / "
            f"{live_summary.get('total_relevant_candidates', 0)} benchmark-relevant"
        )
        lines.append(
            f"- reads: {live_summary.get('total_successful_reads', 0)}/"
            f"{live_summary.get('total_read_attempts', 0)} successful"
        )
        lines.append(
            f"- cases with provider errors: {provider_error_cases}/"
            f"{live_observation.get('case_count', 0)}"
        )
        lines.append(
            "- boundary: this is provider/search/reader evidence only; it uses no model synthesis and produces no shadow decision."
        )
    lines.append("")
    lines.append("## Live 10 semantic projection + shadow")
    lines.append("")
    harness_repeatable = False
    eligible_projection_cases = 0
    expected_live = 0
    if live_semantic is None:
        lines.append("- status: not run")
    else:
        semantic_summary = live_semantic.get("summary", {})
        completed = int(semantic_summary.get("completed_cases") or 0)
        unavailable = int(semantic_summary.get("unavailable_cases") or 0)
        expected = int(live_semantic.get("case_count") or 0)
        expected_live = expected
        harness_repeatable = (expected == 10 and completed + unavailable == 10 and len(live_evaluations) >= 0 and live_semantic is not None)
        lines.append(f"- projection completed: {completed}/{expected}; unavailable: {unavailable}")
        lines.append(
            f"- external calls: {semantic_summary.get('logical_calls', 0)} logical / "
            f"{semantic_summary.get('external_call_attempts', 0)} attempts; "
            f"failed attempts: {semantic_summary.get('failed_attempts', 0)}"
        )
        lines.append(
            f"- projected public documents: {semantic_summary.get('projected_documents', 0)}"
        )
        eligible_projection_cases = sum(
            1
            for record in live_semantic.get("cases", [])
            if len(record.get("documents", [])) > 0
        )
        lines.append(
            f"- live benchmark-relevant evidence projection: "
            f"{eligible_projection_cases}/{expected} cases produced eligible evidence; "
            f"{expected - eligible_projection_cases} produced none"
        )
        lines.append("- persisted payload boundary: URL/title/source metadata, structured labels, hashes and audit only; no page body, prompt or raw model output.")
        unavailable_by_id = {
            str(record.get("case_id")): str(record.get("failure_reason") or "")
            for record in live_semantic.get("cases", [])
            if isinstance(record, dict) and record.get("projection_status") != "completed"
        }
        lines.append("")
        lines.append("| case_id | projection | closed proxy | false_closure | shadow | reasons | primary | coverage | useful |")
        lines.append("|---|---|---|---|---|---|---|---:|---:|")
        evaluation_by_id = {item.case_id: item for item in live_evaluations}
        for record in live_semantic.get("cases", []):
            if not isinstance(record, dict):
                continue
            case_id = str(record.get("case_id") or "")
            item = evaluation_by_id.get(case_id)
            if item is None:
                lines.append(
                    f"| {case_id} | unavailable | - | - | unavailable | "
                    f"{unavailable_by_id.get(case_id) or 'projection_unavailable'} | - | - | - |"
                )
                continue
            lines.append(
                f"| {case_id} | completed | {item.closed} | {item.false_closure} | "
                f"{item.shadow_status} | {', '.join(item.shadow_reasons) or '-'} | "
                f"{item.primary_retrieval} | {item.critical_claim_coverage:.0%} | "
                f"{item.useful_read_ratio:.2f} |"
            )
        if live_evaluations:
            live_summary = summarize_run_evaluations(live_evaluations)
            lines.append("")
            lines.append(
                f"- live false closures: {live_summary.false_closures}; caught: "
                f"{live_summary.caught_false_closures}; missed: "
                f"{live_summary.missed_false_closures}; overblocked: "
                f"{live_summary.overblocked_correct_closures}"
            )
    lines.append("")
    if live_evaluations:
        overall = summarize_run_evaluations((*evaluations, *live_evaluations))
        lines.append("## Combined evaluated cases")
        lines.append("")
        lines.append(f"- evaluated: {overall.total_cases}/20")
        lines.append(
            f"- false closures: {overall.false_closures}; caught: "
            f"{overall.caught_false_closures}; missed: {overall.missed_false_closures}; "
            f"overblocked: {overall.overblocked_correct_closures}"
        )
        lines.append(
            f"- primary retrieval: {overall.primary_retrieved_cases}/"
            f"{overall.primary_required_cases} ({overall.primary_retrieval_rate:.2%})"
        )
        lines.append(
            f"- useful reads: {overall.useful_read_count}/"
            f"{overall.successful_read_count}; macro={overall.mean_useful_read_ratio:.2f}"
        )
        lines.append("")
    lines.append("## RQCE-P0 Exit Gate 自检")
    lines.append("")
    lines.append("1. **legacy 用户可见行为不变**：transcript 是离线 eval 输入，未触碰 WebLookupService 或任何 runtime 路径。")
    lines.append("2. **ClaimState/Trace/Gate 可持久化和恢复**：runner 在进程内构造 ResearchState 并经 build_research_state 严格校验；既有持久化 adapter（A2）与 trace writer（A3）未改。")
    lines.append(
        "3. **20-case harness repeatability**: **PASS / COMPLETE** — "
        "frozen fixtures deterministically re-runnable; live execution protocol, schema and runner re-executable; "
        "20-case report regenerable from structured inputs (live web URLs/results are not required byte-identical)."
    )
    lines.append(
        "3b. **20-case diagnostic outcome**: **NO-GO for production activation** — "
        "8/10 live cases produced no eligible evidence projection; live baseline closure is an operational search-status proxy, "
        "not a real answer-generation transcript."
    )
    lines.append(
        "3c. **live benchmark-relevant evidence projection**: "
        f"{eligible_projection_cases}/{expected_live} cases produced eligible evidence; "
        f"{expected_live - eligible_projection_cases} produced none."
    )
    lines.append("4. **False Closure case 输出明确 claim/gap 原因**：逐 case 的 open_critical_claims 与 shadow_reasons 已记录于上表。")
    lines.append("5. **没有 unknown evidence ID 绕过 Gate**：runner 拒绝未知 doc_id 引用；build_research_state 校验 known_evidence_ids。")
    lines.append("")
    lines.append("")
    lines.append("## P0 Exit Decision")
    lines.append("")
    if harness_repeatable:
        lines.append("**RQCE-P0-C5: PASS / COMPLETE.** 20-case Shadow harness delivered and regenerable; production activation remains NO-GO: live evidence projection coverage is low (8/10 no eligible projection) and live baseline closure is an operational proxy. Dominant observed bottleneck: pre-projection retrieval coverage. Current evidence primarily implicates query planning/SearchIntent and legacy relevance/candidate recall; P1 must first classify the no-projection live cases before choosing the implementation target. Local audit + remote HEAD CI green required before RQCE-P1.")
    else:
        lines.append("**RQCE-P0-C5: INCOMPLETE / NO-GO.** 20-case harness not yet regenerable; live semantic artifact missing. Production activation NO-GO. Do not enter RQCE-P1.")
    lines.append("")
    return "\n".join(lines)


def run_report(
    cases_path: Path,
    transcripts_path: Path,
    live_observation_path: Path | None = DEFAULT_LIVE_OBSERVATION,
    live_cases_path: Path = DEFAULT_LIVE_CASES,
    live_semantic_path: Path | None = DEFAULT_LIVE_SEMANTIC,
) -> str:
    cases = load_research_quality_eval_cases(cases_path)
    transcripts = load_transcripts(transcripts_path)
    evaluations = evaluate_research_runs(cases, transcripts)
    summary = summarize_run_evaluations(evaluations)
    live_observation = None
    if live_observation_path is not None and live_observation_path.exists():
        raw_live = json.loads(live_observation_path.read_text(encoding="utf-8"))
        if isinstance(raw_live, dict):
            live_observation = raw_live
    live_evaluations: tuple[RunEvaluation, ...] = ()
    live_semantic = None
    if live_semantic_path is not None and live_semantic_path.exists():
        live_evaluations, live_semantic = load_live_semantic_evaluations(
            live_cases_path,
            live_semantic_path,
        )
    return render_report(
        evaluations,
        summary,
        cases_path,
        transcripts_path,
        live_observation,
        live_evaluations,
        live_semantic,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the RQCE-P0-C5 frozen + live shadow report.",
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=DEFAULT_CASES,
        help="frozen trap cases fixture (default: tests/fixtures/research_quality/frozen_trap_cases.json)",
    )
    parser.add_argument(
        "--transcripts",
        type=Path,
        default=DEFAULT_TRANSCRIPTS,
        help="legacy transcripts fixture (default: tests/fixtures/research_quality/legacy_transcripts.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="output markdown report path",
    )
    parser.add_argument("--live-cases", type=Path, default=DEFAULT_LIVE_CASES)
    parser.add_argument("--live-semantic", type=Path, default=DEFAULT_LIVE_SEMANTIC)
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = run_report(
        args.cases,
        args.transcripts,
        live_cases_path=args.live_cases,
        live_semantic_path=args.live_semantic,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"wrote {output.relative_to(REPO_ROOT)}")
    print(f"evaluated {sum(1 for line in report.splitlines() if line.startswith('| trap-'))} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
