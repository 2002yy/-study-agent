from __future__ import annotations

import json
from pathlib import Path

from tools.run_research_quality_harness_closure import close_harness

FIXTURES = Path(__file__).parent / "fixtures" / "research_quality"
DOCS = Path(__file__).resolve().parents[1] / "docs" / "research_quality"
SEMANTIC = DOCS / "P0_LIVE_SEMANTIC_EVAL.json"
OBSERVATION = DOCS / "P0_LIVE_OBSERVATION.json"
MANUAL_AUDIT = FIXTURES / "live_candidate_manual_audit.json"


def test_harness_closure_produces_complete_truth_separated_artifacts(tmp_path) -> None:
    output = tmp_path / "v2.json"
    classification = tmp_path / "cls.json"
    artifact, cls = close_harness(
        semantic_path=SEMANTIC,
        observation_path=OBSERVATION,
        manual_audit_path=MANUAL_AUDIT,
        output_path=output,
        classification_path=classification,
    )
    cases = artifact["cases"]
    assert len(cases) == 10
    for case in cases:
        assert case["retrieval_funnel"] is not None, case["case_id"]
        assert case["transcript"] is not None, case["case_id"]
        assert case["typed_failure_reason"] is not None, case["case_id"]
        assert case["stop_reason"] in {
            "projection_completed",
            "projection_exhausted_no_fallback",
        }
        funnel = case["retrieval_funnel"]
        for key in (
            "attempted_queries",
            "returned_candidate_count",
            "production_worth_reading_candidate_count",
            "benchmark_relevant_candidate_count",
            "manual_answer_relevant_candidate_count",
            "manual_topic_only_candidate_count",
            "manual_off_target_candidate_count",
            "source_role_fit_candidate_count",
            "scheduled_read_count",
            "successful_read_count",
            "projected_document_count",
            "eligible_evidence_count",
        ):
            assert key in funnel, (case["case_id"], key)
    assert artifact["summary"]["harness_status"] == "PASS / COMPLETE"
    assert artifact["summary"]["logical_calls"] == 14
    assert artifact["summary"]["external_call_attempts"] == 17
    assert artifact["summary"]["failed_attempts"] == 5
    assert artifact["summary"]["projected_documents"] == 4

    unavailable = [c for c in cases if c["projection_status"] == "unavailable"]
    assert len(unavailable) == 2
    for case in unavailable:
        assert case["transcript"]["queries"], case["case_id"]
        assert case["typed_failure_reason"].startswith(
            "claim_projection_unavailable"
        )
        assert case["stop_reason"] == "projection_exhausted_no_fallback"

    counts = cls["taxonomy_counts"]
    assert counts["NO_ANSWER_RELEVANT_CANDIDATE"] == 7
    assert counts["BENCHMARK_MATCH_FALSE_NEGATIVE"] == 0
    assert counts["CLAIM_PROJECTION_UNAVAILABLE"] == 2
    assert counts["COMPLETED_WITH_EVIDENCE"] == 1
    assert counts["QUERY_UNDERSPECIFIED"] == 0
    assert counts["PROVIDER_RECALL_MISS"] == 0
    assert sum(counts.values()) == 10

    candidate_rows = cls["candidate_audit_rows"]
    assert len(candidate_rows) == 50
    assert sum(row["production_worth_reading"] for row in candidate_rows) == 50
    assert sum(row["benchmark_surface_match"] for row in candidate_rows) == 10
    assert sum(
        row["manual_audit_label"] == "ANSWER_RELEVANT" for row in candidate_rows
    ) == 5
    assert sum(row["manual_audit_label"] == "TOPIC_ONLY" for row in candidate_rows) == 10
    assert sum(row["manual_audit_label"] == "OFF_TARGET" for row in candidate_rows) == 35


def test_taxonomy_does_not_call_off_target_results_false_negatives(tmp_path) -> None:
    output = tmp_path / "v2.json"
    classification_path = tmp_path / "cls.json"
    _, cls = close_harness(
        semantic_path=SEMANTIC,
        observation_path=OBSERVATION,
        manual_audit_path=MANUAL_AUDIT,
        output_path=output,
        classification_path=classification_path,
    )
    rows = {row["case_id"]: row for row in cls["rows"]}

    secondary = rows["trap-secondary-only-live"]
    assert secondary["primary_failure_type"] == "NO_ANSWER_RELEVANT_CANDIDATE"
    assert secondary["funnel"]["returned_candidate_count"] == 5
    assert secondary["funnel"]["production_worth_reading_candidate_count"] == 5
    assert secondary["funnel"]["benchmark_relevant_candidate_count"] == 0
    assert secondary["funnel"]["manual_answer_relevant_candidate_count"] == 0
    assert secondary["funnel"]["manual_off_target_candidate_count"] == 5

    old_primary = rows["trap-old-primary-live"]
    assert old_primary["primary_failure_type"] == "NO_ANSWER_RELEVANT_CANDIDATE"
    assert old_primary["funnel"]["manual_topic_only_candidate_count"] == 5

    simple = rows["trap-simple-factual-live"]
    assert simple["primary_failure_type"] == "COMPLETED_WITH_EVIDENCE"
    assert simple["funnel"]["benchmark_relevant_candidate_count"] == 5
    assert simple["funnel"]["manual_answer_relevant_candidate_count"] == 5
    assert simple["funnel"]["successful_read_count"] == 4
    assert simple["funnel"]["projected_document_count"] == 4


def test_unavailable_projection_preserves_retrieval_secondary_reason(tmp_path) -> None:
    output = tmp_path / "v2.json"
    classification_path = tmp_path / "cls.json"
    _, cls = close_harness(
        semantic_path=SEMANTIC,
        observation_path=OBSERVATION,
        manual_audit_path=MANUAL_AUDIT,
        output_path=output,
        classification_path=classification_path,
    )
    rows = {row["case_id"]: row for row in cls["rows"]}
    duplicate = rows["trap-duplicate-source-live"]
    assert duplicate["primary_failure_type"] == "CLAIM_PROJECTION_UNAVAILABLE"
    assert duplicate["secondary_failure_types"] == [
        "NO_ANSWER_RELEVANT_CANDIDATE"
    ]
    unanswerable = rows["trap-unanswerable-live"]
    assert unanswerable["primary_failure_type"] == "CLAIM_PROJECTION_UNAVAILABLE"
    assert unanswerable["secondary_failure_types"] == [
        "NO_ANSWER_RELEVANT_CANDIDATE"
    ]
    assert unanswerable["funnel"]["benchmark_relevant_candidate_count"] == 5
    assert unanswerable["funnel"]["manual_topic_only_candidate_count"] == 5


def test_committed_truth_fix_artifacts_are_current() -> None:
    v2_path = DOCS / "P0_LIVE_SEMANTIC_EVAL_V2.json"
    assert v2_path.exists()
    artifact = json.loads(v2_path.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == "research-quality-harness-closure-v2"
    assert artifact["summary"]["harness_status"] == "PASS / COMPLETE"
    assert artifact["summary"]["logical_calls"] == 14
    assert artifact["summary"]["external_call_attempts"] == 17
    assert artifact["summary"]["failed_attempts"] == 5
    assert artifact["summary"]["projected_documents"] == 4

    classification = json.loads(
        (DOCS / "P0_RETRIEVAL_FAILURE_CLASSIFICATION.json").read_text(
            encoding="utf-8"
        )
    )
    counts = classification["taxonomy_counts"]
    assert counts["NO_ANSWER_RELEVANT_CANDIDATE"] == 7
    assert counts["BENCHMARK_MATCH_FALSE_NEGATIVE"] == 0
    assert len(classification["candidate_audit_rows"]) == 50
