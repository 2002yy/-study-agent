from __future__ import annotations

import json
from pathlib import Path

from tools.run_answer_claim_eval_baseline import compact_summary, run_baseline


FIXTURE = Path("tests/fixtures/rag_eval/answer_cases.json")
SNAPSHOT = Path("tests/fixtures/rag_eval/answer_claim_baseline_v1_summary.json")


def test_answer_claim_baseline_changes_require_explicit_snapshot_update():
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    actual = compact_summary(run_baseline(FIXTURE))

    assert actual == expected


def test_answer_claim_baseline_is_record_only_and_not_a_model_quality_claim():
    report = run_baseline(FIXTURE)

    assert report["gating"] == "record_only"
    assert report["baseline_kind"] == "deterministic_gold_contract_self_test"
    assert report["producer"]["kind"] == "deterministic_fixture"
    assert report["producer"]["quality_claim"] == "evaluator_self_test_only"
    assert report["quality"]["schema_parse_rate"] == 1.0
    assert report["quality"]["invalid_case_ids"] == []
