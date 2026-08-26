from __future__ import annotations

import json
from pathlib import Path

from tools.run_research_quality_harness_closure import close_harness

FIXTURES = Path(__file__).parent / "fixtures" / "research_quality"
DOCS = Path(__file__).resolve().parents[1] / "docs" / "research_quality"
SEMANTIC = DOCS / "P0_LIVE_SEMANTIC_EVAL.json"
OBSERVATION = DOCS / "P0_LIVE_OBSERVATION.json"


def test_harness_closure_produces_complete_artifacts(tmp_path) -> None:
    output = tmp_path / "v2.json"
    classification = tmp_path / "cls.json"
    artifact, cls = close_harness(
        semantic_path=SEMANTIC,
        observation_path=OBSERVATION,
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
            "benchmark_relevant_candidate_count",
            "source_role_fit_candidate_count",
            "scheduled_read_count",
            "successful_read_count",
            "projected_document_count",
            "eligible_evidence_count",
        ):
            assert key in funnel, (case["case_id"], key)
    assert artifact["summary"]["harness_status"] == "PASS / COMPLETE"

    unavailable = [c for c in cases if c["projection_status"] == "unavailable"]
    assert len(unavailable) == 2
    for case in unavailable:
        assert case["transcript"]["queries"], case["case_id"]
        assert case["typed_failure_reason"].startswith(
            "claim_projection_unavailable"
        )
        assert case["stop_reason"] == "projection_exhausted_no_fallback"

    counts = cls["taxonomy_counts"]
    assert counts["RELEVANCE_FALSE_NEGATIVE"] == 7
    assert counts["CLAIM_PROJECTION_UNAVAILABLE"] == 2
    assert counts["COMPLETED_WITH_EVIDENCE"] == 1
    assert counts["QUERY_UNDERSPECIFIED"] == 0
    assert counts["PROVIDER_RECALL_MISS"] == 0
    total = sum(counts.values())
    assert total == 10


def test_classification_funnel_matches_observation() -> None:
    output = DOCS.parent / "research_quality" / "_tmp_v2.json"
    classification_path = DOCS.parent / "research_quality" / "_tmp_cls.json"
    try:
        _, cls = close_harness(
            semantic_path=SEMANTIC,
            observation_path=OBSERVATION,
            output_path=output,
            classification_path=classification_path,
        )
        rows = {row["case_id"]: row for row in cls["rows"]}
        simple = rows["trap-simple-factual-live"]
        assert simple["funnel"]["benchmark_relevant_candidate_count"] == 5
        assert simple["funnel"]["successful_read_count"] == 4
        assert simple["funnel"]["projected_document_count"] == 4
        secondary = rows["trap-secondary-only-live"]
        assert secondary["primary_failure_type"] == "RELEVANCE_FALSE_NEGATIVE"
        assert secondary["funnel"]["returned_candidate_count"] == 5
        assert secondary["funnel"]["benchmark_relevant_candidate_count"] == 0
    finally:
        output.unlink(missing_ok=True)
        classification_path.unlink(missing_ok=True)


def test_committed_v2_artifact_is_current() -> None:
    v2_path = DOCS / "P0_LIVE_SEMANTIC_EVAL_V2.json"
    assert v2_path.exists()
    artifact = json.loads(v2_path.read_text(encoding="utf-8"))
    assert artifact["schema_version"] == "research-quality-harness-closure-v1"
    assert artifact["summary"]["harness_status"] == "PASS / COMPLETE"
    classification = json.loads(
        (DOCS / "P0_RETRIEVAL_FAILURE_CLASSIFICATION.json").read_text(
            encoding="utf-8"
        )
    )
    assert classification["taxonomy_counts"]["RELEVANCE_FALSE_NEGATIVE"] == 7
