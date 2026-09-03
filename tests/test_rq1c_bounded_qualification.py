from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tools.evaluate_rq1c_bounded_qualification import evaluate
from tools.run_rq1c_bounded_qualification import _load_manifest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "research_quality"
MANIFEST = FIXTURE_DIR / "rq1c_bounded_holdout_manifest.json"
RUBRIC = FIXTURE_DIR / "rq1c_bounded_holdout_rubric.json"
REQUIRED_PROBES = (
    "provider_timeout_retry",
    "user_cancellation",
    "provider_http_429",
    "provider_http_503",
    "unreadable_page",
    "duplicate_republication",
)
TEST_GIT_SHA = "a" * 40


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def _rubric() -> dict[str, object]:
    return json.loads(RUBRIC.read_text(encoding="utf-8"))


def _runtime(case_ids: list[str]) -> dict[str, object]:
    return {
        "schema_version": "rq1c-bounded-qualification-runtime-v1",
        "git_sha": TEST_GIT_SHA,
        "leakage_contract": {
            "runtime_case_keys": ["id", "category", "question"],
            "rubric_loaded_by_runner": False,
            "stores_page_bodies": False,
            "stores_research_query_text": False,
        },
        "cases": [
            {
                "case_id": case_id,
                "runner_error_type": "",
                "budget_contract_violations": [],
                "search": {"audits": [{"query_sha256": "a" * 64}]},
            }
            for case_id in case_ids
        ],
    }


def _review(case_ids: list[str], runtime_path: Path) -> dict[str, object]:
    return {
        "schema_version": "rq1c-bounded-independent-review-v1",
        "runtime_artifact_sha256": hashlib.sha256(runtime_path.read_bytes()).hexdigest(),
        "cases": [
            {
                "case_id": case_id,
                "truthfulness": "pass",
                "quality": "pass" if index < 10 else "fail",
                "hard_failures": [],
            }
            for index, case_id in enumerate(case_ids)
        ],
    }


def _protocol(
    runtime_path: Path,
    *,
    failed_probe: str | None = None,
    probe_ids: tuple[str, ...] = REQUIRED_PROBES,
) -> dict[str, object]:
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    return {
        "schema_version": "rq1c-bounded-protocol-probes-v1",
        "git_sha": runtime["git_sha"],
        "runtime_artifact_sha256": hashlib.sha256(runtime_path.read_bytes()).hexdigest(),
        "leakage_contract": {
            "stores_generated_query_text": False,
            "stores_page_bodies": False,
            "stores_raw_provider_errors": False,
        },
        "probes": [
            {
                "id": probe_id,
                "status": "fail" if probe_id == failed_probe else "pass",
            }
            for probe_id in probe_ids
        ],
    }


def _evaluate_fixture_set(
    tmp_path: Path,
    *,
    runtime: dict[str, object] | None = None,
    failed_probe: str | None = None,
) -> dict[str, object]:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime_value = runtime or _runtime(case_ids)
    runtime_path = tmp_path / "runtime.json"
    review_path = tmp_path / "review.json"
    protocol_path = tmp_path / "protocol.json"
    output_path = tmp_path / "report.json"
    _write_json(runtime_path, runtime_value)
    _write_json(review_path, _review(case_ids, runtime_path))
    _write_json(protocol_path, _protocol(runtime_path, failed_probe=failed_probe))
    return evaluate(
        runtime_path=runtime_path,
        rubric_path=RUBRIC,
        review_path=review_path,
        protocol_path=protocol_path,
        output_path=output_path,
    )


def test_runtime_manifest_is_exactly_twelve_gold_free_cases() -> None:
    cases = _load_manifest(MANIFEST)

    assert len(cases) == 12
    assert len({case["id"] for case in cases}) == 12
    assert all(set(case) == {"id", "category", "question"} for case in cases)


def test_runtime_manifest_rejects_evaluation_fields(tmp_path: Path) -> None:
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    payload["cases"][0]["expected_answer"] = "must never enter the runner"
    path = tmp_path / "leaky_manifest.json"
    _write_json(path, payload)

    with pytest.raises(ValueError, match="only id/category/question"):
        _load_manifest(path)


def test_independent_evaluator_can_reach_go_only_after_all_gates(tmp_path: Path) -> None:
    report = _evaluate_fixture_set(tmp_path)

    assert report["decision"] == "GO"
    assert report["inputs"]["git_sha"] == TEST_GIT_SHA  # type: ignore[index]
    assert report["scores"]["truthfulness"] == "12/12"  # type: ignore[index]
    assert report["scores"]["quality"] == "10/12"  # type: ignore[index]
    assert all(report["checks"].values())  # type: ignore[union-attr]


def test_review_must_bind_exact_runtime_artifact(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime_path = tmp_path / "runtime.json"
    review_path = tmp_path / "review.json"
    protocol_path = tmp_path / "protocol.json"
    _write_json(runtime_path, _runtime(case_ids))
    review = _review(case_ids, runtime_path)
    review["runtime_artifact_sha256"] = "0" * 64
    _write_json(review_path, review)
    _write_json(protocol_path, _protocol(runtime_path))

    with pytest.raises(ValueError, match="not bound to this runtime artifact"):
        evaluate(
            runtime_path=runtime_path,
            rubric_path=RUBRIC,
            review_path=review_path,
            protocol_path=protocol_path,
            output_path=tmp_path / "report.json",
        )


def test_runtime_git_sha_must_be_exact(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime = _runtime(case_ids)
    runtime["git_sha"] = "not-a-git-sha"
    runtime_path = tmp_path / "runtime.json"
    review_path = tmp_path / "review.json"
    protocol_path = tmp_path / "protocol.json"
    _write_json(runtime_path, runtime)
    _write_json(review_path, _review(case_ids, runtime_path))
    protocol = _protocol(runtime_path)
    protocol["git_sha"] = TEST_GIT_SHA
    _write_json(protocol_path, protocol)

    with pytest.raises(ValueError, match="runtime artifact git_sha"):
        evaluate(
            runtime_path=runtime_path,
            rubric_path=RUBRIC,
            review_path=review_path,
            protocol_path=protocol_path,
            output_path=tmp_path / "report.json",
        )


def test_protocol_must_bind_exact_runtime_artifact(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime_path = tmp_path / "runtime.json"
    review_path = tmp_path / "review.json"
    protocol_path = tmp_path / "protocol.json"
    _write_json(runtime_path, _runtime(case_ids))
    _write_json(review_path, _review(case_ids, runtime_path))
    protocol = _protocol(runtime_path)
    protocol["runtime_artifact_sha256"] = "0" * 64
    _write_json(protocol_path, protocol)

    with pytest.raises(ValueError, match="protocol probes are not bound"):
        evaluate(
            runtime_path=runtime_path,
            rubric_path=RUBRIC,
            review_path=review_path,
            protocol_path=protocol_path,
            output_path=tmp_path / "report.json",
        )


def test_protocol_git_sha_must_match_runtime(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime_path = tmp_path / "runtime.json"
    review_path = tmp_path / "review.json"
    protocol_path = tmp_path / "protocol.json"
    _write_json(runtime_path, _runtime(case_ids))
    _write_json(review_path, _review(case_ids, runtime_path))
    protocol = _protocol(runtime_path)
    protocol["git_sha"] = "b" * 40
    _write_json(protocol_path, protocol)

    with pytest.raises(ValueError, match="protocol/runtime git sha mismatch"):
        evaluate(
            runtime_path=runtime_path,
            rubric_path=RUBRIC,
            review_path=review_path,
            protocol_path=protocol_path,
            output_path=tmp_path / "report.json",
        )


def test_protocol_probe_set_is_exact_and_unique(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime_path = tmp_path / "runtime.json"
    review_path = tmp_path / "review.json"
    protocol_path = tmp_path / "protocol.json"
    _write_json(runtime_path, _runtime(case_ids))
    _write_json(review_path, _review(case_ids, runtime_path))

    invalid_sets = (
        REQUIRED_PROBES[:-1],
        (*REQUIRED_PROBES[:-1], REQUIRED_PROBES[0]),
        (*REQUIRED_PROBES, "unexpected_probe"),
    )
    for index, probe_ids in enumerate(invalid_sets):
        _write_json(protocol_path, _protocol(runtime_path, probe_ids=probe_ids))
        with pytest.raises(ValueError, match="protocol probe"):
            evaluate(
                runtime_path=runtime_path,
                rubric_path=RUBRIC,
                review_path=review_path,
                protocol_path=protocol_path,
                output_path=tmp_path / f"report-{index}.json",
            )


def test_runtime_artifact_rejects_plaintext_generated_query(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime = _runtime(case_ids)
    audit = runtime["cases"][0]["search"]["audits"][0]  # type: ignore[index]
    audit["query_text"] = "secret generated query"
    runtime_path = tmp_path / "runtime.json"
    review_path = tmp_path / "review.json"
    protocol_path = tmp_path / "protocol.json"
    _write_json(runtime_path, runtime)
    _write_json(review_path, _review(case_ids, runtime_path))
    _write_json(protocol_path, _protocol(runtime_path))

    with pytest.raises(ValueError, match="leaked generated research query text"):
        evaluate(
            runtime_path=runtime_path,
            rubric_path=RUBRIC,
            review_path=review_path,
            protocol_path=protocol_path,
            output_path=tmp_path / "report.json",
        )


def test_runtime_budget_violation_forces_no_go(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime = _runtime(case_ids)
    first_case = runtime["cases"][0]  # type: ignore[index]
    first_case["budget_contract_violations"] = ["hard_timeout_seconds>60"]

    report = _evaluate_fixture_set(tmp_path, runtime=runtime)

    assert report["decision"] == "NO-GO"
    assert report["checks"]["runtime_budget"] is False  # type: ignore[index]


def test_failed_protocol_probe_forces_no_go(tmp_path: Path) -> None:
    report = _evaluate_fixture_set(tmp_path, failed_probe="provider_http_503")

    assert report["decision"] == "NO-GO"
    assert report["checks"]["protocol_probes"] is False  # type: ignore[index]
