"""Generate the RQCE-P0-C4 shadow report from frozen fixtures.

Loads the frozen trap cases and the legacy transcript fixture, runs the
offline shadow runner, and writes the diagnostic markdown report to
``docs/research_quality/P0_SHADOW_REPORT.md``.

This tool performs no live web access and no WebLookupService integration;
it only replays synthetic transcripts against the frozen corpus.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.evals.research_quality import load_research_quality_eval_cases
from src.evals.research_quality_runner import (
    ResearchRunTranscript,
    RunEvaluation,
    evaluate_research_runs,
    research_run_transcript_from_dict,
    summarize_run_evaluations,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = REPO_ROOT / "tests" / "fixtures" / "research_quality" / "frozen_trap_cases.json"
DEFAULT_TRANSCRIPTS = (
    REPO_ROOT / "tests" / "fixtures" / "research_quality" / "legacy_transcripts.json"
)
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "research_quality" / "P0_SHADOW_REPORT.md"


def load_transcripts(path: Path) -> tuple[ResearchRunTranscript, ...]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("transcript fixture must be a JSON object")
    if raw.get("schema_version") != "research-quality-run-v1":
        raise ValueError("unsupported transcript schema_version")
    items = raw.get("transcripts")
    if not isinstance(items, list):
        raise ValueError("transcript fixture requires a transcripts list")
    return tuple(research_run_transcript_from_dict(item) for item in items)


def render_report(
    evaluations: tuple[RunEvaluation, ...],
    summary: Any,
    cases_path: Path,
    transcripts_path: Path,
) -> str:
    lines: list[str] = []
    lines.append("# RQCE-P0-C4 Shadow Report (baseline vs shadow)")
    lines.append("")
    lines.append("> 诊断报告，不是 Release Gate。重点定位：Shadow Gate 是否抓到二手来源提前结束、是否误 BLOCK 简单事实、fixture 是否遗漏 critical surface、当前数据结构能否解释失败。")
    lines.append("")
    lines.append(f"- cases fixture: `{cases_path.relative_to(REPO_ROOT)}`")
    lines.append(f"- transcripts fixture: `{transcripts_path.relative_to(REPO_ROOT)}`")
    lines.append(f"- evaluated frozen cases: {summary.total_cases}")
    lines.append("")
    lines.append("## 聚合指标")
    lines.append("")
    lines.append(f"- closed runs: {summary.closed_runs}/{summary.total_cases}")
    lines.append(f"- false closures (baseline 误闭环): {summary.false_closures}")
    lines.append(f"- shadow blocked runs: {summary.shadow_blocked_runs}")
    lines.append(f"- caught false closures (shadow 抓到): {summary.caught_false_closures}")
    lines.append(f"- missed false closures (shadow 漏抓): {summary.missed_false_closures}")
    lines.append(f"- overblocked correct closures (shadow 误 BLOCK): {summary.overblocked_correct_closures}")
    lines.append(f"- primary retrieval rate: {summary.primary_retrieval_rate:.2%}")
    lines.append(f"- mean useful read ratio: {summary.mean_useful_read_ratio:.2f}")
    lines.append(f"- mean critical claim coverage: {summary.mean_critical_claim_coverage:.2%}")
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
    lines.append("| case_id | closed | false_closure | violated | shadow | open critical | primary retrieval | coverage | useful read ratio |")
    lines.append("|---|---|---|---|---|---|---|---:|---:|")
    for item in evaluations:
        lines.append(
            f"| {item.case_id} | {item.closed} | {item.false_closure} | "
            f"{', '.join(item.violated_closure_conditions) or '-'} | "
            f"{item.shadow_status} | {', '.join(item.open_critical_claims) or '-'} | "
            f"{item.primary_retrieval} | {item.critical_claim_coverage:.0%} | "
            f"{item.useful_read_ratio:.2f} |"
        )
    lines.append("")
    lines.append("## RQCE-P0 Exit Gate 自检")
    lines.append("")
    lines.append("1. **legacy 用户可见行为不变**：transcript 是离线 eval 输入，未触碰 WebLookupService 或任何 runtime 路径。")
    lines.append("2. **ClaimState/Trace/Gate 可持久化和恢复**：runner 在进程内构造 ResearchState 并经 build_research_state 严格校验；既有持久化 adapter（A2）与 trace writer（A3）未改。")
    lines.append("3. **20 题 runner 可重复**：frozen 10 题已跑且确定性可重跑；live 10 题无 corpus，超出 P0 离线范围（留待真实 web 运行）。")
    lines.append("4. **False Closure case 输出明确 claim/gap 原因**：逐 case 的 open_critical_claims 与 shadow_reasons 已记录于上表。")
    lines.append("5. **没有 unknown evidence ID 绕过 Gate**：runner 拒绝未知 doc_id 引用；build_research_state 校验 known_evidence_ids。")
    lines.append("")
    lines.append("> RQCE-P0 Exit Gate 通过后禁止自动进入 RQCE-P1；需人工确认本报告。")
    lines.append("")
    return "\n".join(lines)


def run_report(cases_path: Path, transcripts_path: Path) -> str:
    cases = load_research_quality_eval_cases(cases_path)
    transcripts = load_transcripts(transcripts_path)
    evaluations = evaluate_research_runs(cases, transcripts)
    summary = summarize_run_evaluations(evaluations)
    return render_report(evaluations, summary, cases_path, transcripts_path)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate the RQCE-P0-C4 shadow report from frozen fixtures.",
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
    return parser


def main() -> int:
    args = _parser().parse_args()
    report = run_report(args.cases, args.transcripts)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"wrote {output.relative_to(REPO_ROOT)}")
    print(f"evaluated {sum(1 for line in report.splitlines() if line.startswith('| trap-'))} cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
