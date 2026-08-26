from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from src.evals.research_quality import (
    load_research_quality_eval_cases,
)
from src.evals.research_quality_runner import (
    ResearchRunTranscript,
    RunReadRecord,
    evaluate_research_run,
    evaluate_research_runs,
    research_run_transcript_from_dict,
    research_run_transcript_to_dict,
    summarize_run_evaluations,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "research_quality"


def _load_case(case_id: str):
    for case in load_research_quality_eval_cases(
        FIXTURES_DIR / "frozen_trap_cases.json"
    ):
        if case.id == case_id:
            return case
    raise AssertionError(f"case not found: {case_id}")


def _transcript(
    case_id: str,
    *,
    reads: tuple[tuple[str, str, bool], ...] = (),
    cited: tuple[str, ...] = (),
    addressed: tuple[str, ...] = (),
    closed: bool = True,
    reference_date: str = "2026-08-01",
) -> ResearchRunTranscript:
    return ResearchRunTranscript(
        case_id=case_id,
        reference_date=reference_date,
        queries=("initial query",),
        searches=1,
        reads=tuple(
            RunReadRecord(doc_id=doc_id, outcome=outcome, extraction_eligible=eligible)
            for doc_id, outcome, eligible in reads
        ),
        cited_doc_ids=cited,
        addressed_claim_surfaces=addressed,
        llm_calls=2,
        elapsed_seconds=10.0,
        closed=closed,
    )


def test_runner_catches_secondary_only_false_closure() -> None:
    case = _load_case("trap-secondary-only-frozen")
    transcript = _transcript(
        case.id,
        reads=(("blog-secondary-1", "success", True),),
        cited=("blog-secondary-1",),
        addressed=(
            "StreamQueue supports a specific maximum message size published by the vendor.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure
    assert "primary_not_read" in evaluation.violated_closure_conditions
    assert evaluation.primary_retrieval is False
    assert evaluation.shadow_would_block
    assert evaluation.legacy_would_stop_but_shadow_blocked
    assert evaluation.critical_claim_coverage == 1.0
    assert evaluation.independent_cluster_count == 1


def test_runner_allows_correct_primary_read_closure() -> None:
    case = _load_case("trap-secondary-only-frozen")
    transcript = _transcript(
        case.id,
        reads=(
            ("vendor-spec", "success", True),
            ("blog-secondary-1", "success", True),
        ),
        cited=("vendor-spec", "blog-secondary-1"),
        addressed=(
            "StreamQueue supports a specific maximum message size published by the vendor.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure is False
    assert evaluation.primary_retrieval is True
    assert evaluation.useful_read_ratio == 1.0
    assert evaluation.shadow_would_pass
    assert evaluation.shadow_status == "pass"


def test_runner_detects_duplicate_cluster_trap() -> None:
    case = _load_case("trap-duplicate-source-frozen")
    transcript = _transcript(
        case.id,
        reads=(
            ("wire-a", "success", True),
            ("wire-b", "success", True),
            ("wire-c", "success", True),
        ),
        cited=("wire-a", "wire-b", "wire-c"),
        addressed=(
            "The recall was confirmed by a countable number of independently originated reports.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure
    assert "independent_sources_below_minimum" in evaluation.violated_closure_conditions
    assert evaluation.independent_cluster_count == 1
    assert evaluation.shadow_would_block


def test_runner_detects_stale_primary_trap() -> None:
    case = _load_case("trap-old-primary-frozen")
    transcript = _transcript(
        case.id,
        reads=(("old-primary", "success", True),),
        cited=("old-primary",),
        addressed=(
            "The gateway's currently supported TLS versions are published.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure
    assert "freshness_unmet" in evaluation.violated_closure_conditions


def test_runner_detects_conflicting_primary_trap() -> None:
    case = _load_case("trap-conflicting-primary-frozen")
    transcript = _transcript(
        case.id,
        reads=(("primary-v9", "success", True),),
        cited=("primary-v9",),
        addressed=(
            "The vendor publishes a definitive concurrency limit.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure
    assert "conflict_unresolved" in evaluation.violated_closure_conditions


def test_runner_unanswerable_closure_is_false_closure() -> None:
    case = _load_case("trap-unanswerable-frozen")
    transcript = _transcript(
        case.id,
        reads=(("speculation-thread", "success", True),),
        cited=("speculation-thread",),
        addressed=(
            "The committee's final decision has not been announced and cannot be verified before the announcement.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure
    assert "question_unverifiable" in evaluation.violated_closure_conditions
    assert evaluation.shadow_would_block
    assert evaluation.legacy_would_stop_but_shadow_blocked


def test_runner_unanswerable_not_closed_is_correct() -> None:
    case = _load_case("trap-unanswerable-frozen")
    transcript = _transcript(
        case.id,
        reads=(("speculation-thread", "success", True),),
        cited=(),
        addressed=(),
        closed=False,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure is False
    assert evaluation.violated_closure_conditions == ()


def test_runner_simple_factual_correct_path_not_overblocked() -> None:
    case = _load_case("trap-simple-factual-frozen")
    transcript = _transcript(
        case.id,
        reads=(("project-history", "success", True),),
        cited=("project-history",),
        addressed=(
            "The library's initial public release year is documented.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure is False
    assert evaluation.shadow_would_pass is False or evaluation.shadow_status == "pass"
    assert evaluation.shadow_would_block is False


def test_runner_simple_factual_snippet_only_is_violation() -> None:
    case = _load_case("trap-simple-factual-frozen")
    transcript = _transcript(
        case.id,
        reads=(),
        cited=("project-history",),
        addressed=(
            "The library's initial public release year is documented.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure
    assert "snippet_only_evidence" in evaluation.violated_closure_conditions


def test_runner_closed_without_citations_flagged() -> None:
    case = _load_case("trap-simple-factual-frozen")
    transcript = _transcript(
        case.id,
        reads=(),
        cited=(),
        addressed=(
            "The library's initial public release year is documented.",
        ),
        closed=True,
    )
    evaluation = evaluate_research_run(case, transcript)
    assert evaluation.false_closure
    assert "no_cited_evidence" in evaluation.violated_closure_conditions


def test_runner_transcript_round_trip_and_validation() -> None:
    payload: dict[str, Any] = {
        "case_id": "trap-simple-factual-frozen",
        "reference_date": "2026-08-01",
        "queries": ["q1", "q2"],
        "searches": 2,
        "reads": [
            {"doc_id": "project-history", "outcome": "success", "extraction_eligible": True}
        ],
        "cited_doc_ids": ["project-history"],
        "addressed_claim_surfaces": [
            "The library's initial public release year is documented."
        ],
        "llm_calls": 3,
        "elapsed_seconds": 12.5,
        "closed": True,
    }
    transcript = research_run_transcript_from_dict(deepcopy(payload))
    assert transcript.queries == ("q1", "q2")
    restored = research_run_transcript_from_dict(
        json.loads(json.dumps(research_run_transcript_to_dict(transcript)))
    )
    assert restored == transcript

    bad = deepcopy(payload)
    bad["unknown_field"] = 1
    with pytest.raises(ValueError, match="unknown .* field"):
        research_run_transcript_from_dict(bad)

    bad_date = deepcopy(payload)
    bad_date["reference_date"] = "2026/08/01"
    with pytest.raises(ValueError, match="ISO-8601"):
        research_run_transcript_from_dict(bad_date)

    bad_read = deepcopy(payload)
    bad_read["reads"] = [
        {"doc_id": "project-history", "outcome": "maybe", "extraction_eligible": True}
    ]
    with pytest.raises(ValueError):
        research_run_transcript_from_dict(bad_read)

    dup_read = deepcopy(payload)
    dup_read["reads"] = [
        {"doc_id": "project-history", "outcome": "success", "extraction_eligible": True},
        {"doc_id": "project-history", "outcome": "failed", "extraction_eligible": True},
    ]
    with pytest.raises(ValueError, match="duplicate"):
        research_run_transcript_from_dict(dup_read)


def test_runner_rejects_unknown_doc_references() -> None:
    case = _load_case("trap-simple-factual-frozen")
    transcript = _transcript(
        case.id,
        reads=(("ghost-doc", "success", True),),
        cited=("ghost-doc",),
    )
    with pytest.raises(ValueError, match="unknown doc id"):
        evaluate_research_run(case, transcript)

    mismatch = _transcript("trap-secondary-only-frozen", closed=False)
    with pytest.raises(ValueError, match="does not match"):
        evaluate_research_run(case, mismatch)


def test_runner_batch_and_summary() -> None:
    secondary_case = _load_case("trap-secondary-only-frozen")
    simple_case = _load_case("trap-simple-factual-frozen")
    good = _transcript(
        secondary_case.id,
        reads=(("vendor-spec", "success", True),),
        cited=("vendor-spec",),
        addressed=(
            "StreamQueue supports a specific maximum message size published by the vendor.",
        ),
        closed=True,
    )
    bad = _transcript(
        simple_case.id,
        reads=(),
        cited=("project-history",),
        addressed=(),
        closed=True,
    )
    evaluations = evaluate_research_runs(
        [secondary_case, simple_case], [good, bad]
    )
    with pytest.raises(ValueError, match="duplicate transcript"):
        evaluate_research_runs([secondary_case], [good, good])
    summary = summarize_run_evaluations(evaluations)
    assert summary.total_cases == 2
    assert summary.false_closures == 1
    assert summary.caught_false_closures == 1
    assert summary.missed_false_closures == 0
    assert summary.overblocked_correct_closures == 0
    assert summary.primary_retrieval_rate == 0.5
    payload = summary.to_dict()
    assert payload["total_cases"] == 2


def test_runner_summary_empty_is_safe() -> None:
    summary = summarize_run_evaluations(())
    assert summary.total_cases == 0
    assert summary.mean_useful_read_ratio == 0.0
