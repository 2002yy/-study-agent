from __future__ import annotations

import json
import tempfile
from copy import deepcopy
from pathlib import Path

import pytest

from src.evals.research_quality import load_research_quality_eval_cases
from src.evals.research_quality_runner import (
    RESEARCH_QUALITY_RUN_SCHEMA_VERSION,
    evaluate_research_runs,
    summarize_run_evaluations,
)
from tools.run_research_quality_shadow_report import (
    DEFAULT_CASES,
    DEFAULT_LIVE_OBSERVATION,
    DEFAULT_OUTPUT,
    DEFAULT_TRANSCRIPTS,
    load_transcripts,
    run_report,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "research_quality"
CASES_FILE = FIXTURES_DIR / "frozen_trap_cases.json"
TRANSCRIPTS_FILE = FIXTURES_DIR / "legacy_transcripts.json"


def _load_cases() -> tuple:
    return load_research_quality_eval_cases(CASES_FILE)


def _load_transcripts() -> tuple:
    return load_transcripts(TRANSCRIPTS_FILE)


def test_legacy_transcripts_align_with_frozen_cases() -> None:
    cases = _load_cases()
    transcripts = _load_transcripts()
    assert len(transcripts) == 10
    case_ids = {case.id for case in cases}
    transcript_ids = {transcript.case_id for transcript in transcripts}
    assert transcript_ids == case_ids


def test_shadow_run_executes_for_all_frozen_cases() -> None:
    evaluations = evaluate_research_runs(_load_cases(), _load_transcripts())
    assert len(evaluations) == 10
    assert all(item.closed for item in evaluations)
    false_closures = [item for item in evaluations if item.false_closure]
    assert len(false_closures) >= 7
    summary = summarize_run_evaluations(evaluations)
    assert summary.caught_false_closures >= 3
    assert summary.overblocked_correct_closures == 0
    assert summary.missed_false_closures >= 1


def test_false_closure_cases_carry_explicit_reasons() -> None:
    evaluations = evaluate_research_runs(_load_cases(), _load_transcripts())
    for item in evaluations:
        if item.false_closure:
            assert item.violated_closure_conditions
            if item.shadow_would_block:
                assert (
                    item.open_critical_claims
                    or item.shadow_reasons
                    or "no_cited_evidence" in item.violated_closure_conditions
                )


def test_runner_is_deterministic_and_repeatable() -> None:
    first = evaluate_research_runs(_load_cases(), _load_transcripts())
    second = evaluate_research_runs(_load_cases(), _load_transcripts())
    assert [item.to_dict() for item in first] == [
        item.to_dict() for item in second
    ]


def test_no_unknown_evidence_id_bypasses_gate() -> None:
    cases = _load_cases()
    transcripts = _load_transcripts()
    case_by_id = {case.id: case for case in cases}
    for transcript in transcripts:
        case = case_by_id[transcript.case_id]
        corpus_ids = {document.doc_id for document in case.corpus}
        for record in transcript.reads:
            assert record.doc_id in corpus_ids
        for doc_id in transcript.cited_doc_ids:
            assert doc_id in corpus_ids


def test_transcript_fixture_uses_correct_schema_version() -> None:
    raw = deepcopy(json.loads(TRANSCRIPTS_FILE.read_text(encoding="utf-8")))
    assert raw["schema_version"] == RESEARCH_QUALITY_RUN_SCHEMA_VERSION
    bad = deepcopy(raw)
    bad["schema_version"] = "research-quality-run-v0"
    with pytest.raises(ValueError, match="schema_version"):
        load_transcripts(_write_temp(bad))


def _write_temp(payload: dict) -> Path:
    handle, path = tempfile.mkstemp(suffix=".json")
    import os

    os.close(handle)
    Path(path).write_text(json.dumps(payload), encoding="utf-8")
    return Path(path)


def test_report_generator_produces_nonempty_markdown() -> None:
    report = run_report(CASES_FILE, TRANSCRIPTS_FILE)
    assert report.startswith("# RQCE-P0-C5 Shadow Report")
    assert "聚合指标" in report
    assert "按类别分布" in report
    assert "逐 case 诊断" in report
    assert "RQCE-P0 Exit Gate 自检" in report
    assert "trap-secondary-only-frozen" in report
    assert "trap-unanswerable-frozen" in report
    assert "missed false closures" in report
    assert "Live 10 operational observation" in report
    assert "cases with benchmark-relevant candidates: 2/10" in report


def test_default_paths_match_repo_layout() -> None:
    assert DEFAULT_CASES == CASES_FILE
    assert DEFAULT_TRANSCRIPTS == TRANSCRIPTS_FILE
    assert DEFAULT_OUTPUT.name == "P0_SHADOW_REPORT.md"
    assert DEFAULT_OUTPUT.parent.name == "research_quality"
    assert DEFAULT_LIVE_OBSERVATION.name == "P0_LIVE_OBSERVATION.json"
