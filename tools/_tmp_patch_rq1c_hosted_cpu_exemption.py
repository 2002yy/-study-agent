from __future__ import annotations

from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"missing patch anchor: {label}")
    return text.replace(old, new, 1)


def patch_core() -> None:
    path = Path("tools/run_rq1c_bounded_qualification_core.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(text, "import json\nimport re\n", "import json\nimport os\nimport re\n", "core import os")
    text = replace_once(
        text,
        "from src.application.active_research_runtime import (  # noqa: E402\n    ACTIVE_RESEARCH_BRIEF_KEY,\n    ACTIVE_RESEARCH_METRICS_KEY,\n)\n",
        "from src.application.active_research_runtime import (  # noqa: E402\n    ACTIVE_RESEARCH_BRIEF_KEY,\n    ACTIVE_RESEARCH_METRICS_KEY,\n    ActiveResearchRuntimeExecutor,\n)\n",
        "core runtime executor import",
    )
    text = replace_once(
        text,
        "from src.web.research.state import attach_claim_engine_state  # noqa: E402\n",
        "from src.web.research.state import attach_claim_engine_state  # noqa: E402\nfrom src.web.research.model_gateway import ResearchModelGateway  # noqa: E402\n",
        "core model gateway import",
    )
    text = replace_once(
        text,
        '_ANSWER_PHASES = ("answer_generation", "answer_claim_binding")\n\n\ndef _utc_now() -> str:\n',
        '_ANSWER_PHASES = ("answer_generation", "answer_claim_binding")\n'
        '_HOSTED_CPU_WALLCLOCK_ENV = "RQ1C_HOSTED_CPU_WALLCLOCK_EXEMPT"\n'
        '_HOSTED_CPU_SOFT_TIMEOUT_SECONDS = 240\n'
        '_HOSTED_CPU_HARD_TIMEOUT_SECONDS = 300\n'
        '_HOSTED_CPU_MODEL_TIMEOUT_SECONDS = 120.0\n\n\n'
        'def _hosted_cpu_wallclock_exempt() -> bool:\n'
        '    requested = str(os.getenv(_HOSTED_CPU_WALLCLOCK_ENV) or "").strip().lower() in {\n'
        '        "1",\n'
        '        "true",\n'
        '        "yes",\n'
        '        "on",\n'
        '    }\n'
        '    github_actions = str(os.getenv("GITHUB_ACTIONS") or "").strip().lower() == "true"\n'
        '    return requested and github_actions\n\n\n'
        'def _utc_now() -> str:\n',
        "core hosted constants",
    )
    text = replace_once(
        text,
        'def _active_context(reference_date: str) -> dict[str, Any]:\n'
        '    state = build_research_state(\n',
        'def _active_context(reference_date: str) -> dict[str, Any]:\n'
        '    wallclock_exempt = _hosted_cpu_wallclock_exempt()\n'
        '    state = build_research_state(\n',
        "core active context flag",
    )
    text = replace_once(
        text,
        '            soft_timeout_seconds=45,\n'
        '            hard_timeout_seconds=60,\n',
        '            soft_timeout_seconds=(\n'
        '                _HOSTED_CPU_SOFT_TIMEOUT_SECONDS if wallclock_exempt else 45\n'
        '            ),\n'
        '            hard_timeout_seconds=(\n'
        '                _HOSTED_CPU_HARD_TIMEOUT_SECONDS if wallclock_exempt else 60\n'
        '            ),\n',
        "core active context wallclock",
    )
    text = replace_once(
        text,
        '    if elapsed > 60:\n        violations.append("hard_timeout_exceeded")\n',
        '    if elapsed > 60 and not _hosted_cpu_wallclock_exempt():\n'
        '        violations.append("hard_timeout_exceeded")\n',
        "core elapsed marker",
    )
    text = replace_once(
        text,
        '_run_case = make_guarded_run_case(\n'
        '    raw_run_case=_run_case,\n'
        '    build_chat_service=_build_chat_service,\n'
        '    binding_rows_provider=research_binding_rows,\n'
        '    answer_stage_model_calls=_answer_stage_model_calls,\n'
        '    exact_git_check=_git_sha,\n'
        ')\n\n\n'
        'def run_qualification(*, manifest_path: Path, output_path: Path) -> dict[str, Any]:\n',
        '_run_case = make_guarded_run_case(\n'
        '    raw_run_case=_run_case,\n'
        '    build_chat_service=_build_chat_service,\n'
        '    binding_rows_provider=research_binding_rows,\n'
        '    answer_stage_model_calls=_answer_stage_model_calls,\n'
        '    exact_git_check=_git_sha,\n'
        ')\n\n\n'
        'def _qualification_active_runtime_factory(\n'
        '    repository: WebLookupRepository,\n'
        '    gateway: Any,\n'
        ') -> ActiveResearchRuntimeExecutor:\n'
        '    if not _hosted_cpu_wallclock_exempt():\n'
        '        return ActiveResearchRuntimeExecutor(repository, gateway)\n'
        '    model_gateway = ResearchModelGateway(\n'
        '        timeout_seconds=_HOSTED_CPU_MODEL_TIMEOUT_SECONDS\n'
        '    )\n'
        '    return ActiveResearchRuntimeExecutor(\n'
        '        repository,\n'
        '        gateway,\n'
        '        model_gateway=model_gateway,\n'
        '        model_timeout_cap_seconds=_HOSTED_CPU_MODEL_TIMEOUT_SECONDS,\n'
        '        candidate_assessment_timeout_cap_seconds=_HOSTED_CPU_MODEL_TIMEOUT_SECONDS,\n'
        '    )\n\n\n'
        'def run_qualification(*, manifest_path: Path, output_path: Path) -> dict[str, Any]:\n',
        "core qualification factory",
    )
    text = replace_once(
        text,
        '        "configured_budget": {\n',
        '        "wallclock_contract": {\n'
        '            "product_soft_timeout_seconds": 45,\n'
        '            "product_hard_timeout_seconds": 60,\n'
        '            "hosted_cpu_exempt": _hosted_cpu_wallclock_exempt(),\n'
        '            "reason": (\n'
        '                "github_hosted_local_model_cpu"\n'
        '                if _hosted_cpu_wallclock_exempt()\n'
        '                else ""\n'
        '            ),\n'
        '        },\n'
        '        "configured_budget": {\n',
        "core artifact contract",
    )
    text = replace_once(
        text,
        '        service = ClaimEngineDispatchWebLookupService(repository)\n',
        '        service = ClaimEngineDispatchWebLookupService(\n'
        '            repository,\n'
        '            active_runtime_factory=_qualification_active_runtime_factory,\n'
        '        )\n',
        "core service construction",
    )
    path.write_text(text, encoding="utf-8")


def patch_evaluator() -> None:
    path = Path("tools/evaluate_rq1c_bounded_qualification.py")
    text = path.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'def _runtime_budget_is_valid(record: Mapping[str, Any], gate: Mapping[str, int]) -> bool:\n',
        'def _runtime_budget_is_valid(\n'
        '    record: Mapping[str, Any],\n'
        '    gate: Mapping[str, int],\n'
        '    *,\n'
        '    wallclock_applicable: bool,\n'
        ') -> bool:\n',
        "evaluator budget signature",
    )
    text = replace_once(
        text,
        '        and model_calls <= gate["max_model_calls"]\n'
        '        and elapsed_seconds <= gate["hard_timeout_seconds"]\n'
        '    )\n\n\n'
        'def _validate_runtime(\n',
        '        and model_calls <= gate["max_model_calls"]\n'
        '        and (\n'
        '            not wallclock_applicable\n'
        '            or elapsed_seconds <= gate["hard_timeout_seconds"]\n'
        '        )\n'
        '    )\n\n\n'
        'def _runtime_wallclock_applicable(runtime: Mapping[str, Any]) -> bool:\n'
        '    contract = runtime.get("wallclock_contract")\n'
        '    if contract is None:\n'
        '        return True\n'
        '    if not isinstance(contract, Mapping):\n'
        '        raise ValueError("runtime wallclock contract must be an object")\n'
        '    if contract.get("product_soft_timeout_seconds") != 45:\n'
        '        raise ValueError("runtime wallclock contract changed product soft timeout")\n'
        '    if contract.get("product_hard_timeout_seconds") != 60:\n'
        '        raise ValueError("runtime wallclock contract changed product hard timeout")\n'
        '    exempt = contract.get("hosted_cpu_exempt")\n'
        '    if not isinstance(exempt, bool):\n'
        '        raise ValueError("runtime hosted-cpu wallclock exemption must be boolean")\n'
        '    reason = str(contract.get("reason") or "")\n'
        '    if exempt and reason != "github_hosted_local_model_cpu":\n'
        '        raise ValueError("runtime hosted-cpu wallclock exemption reason invalid")\n'
        '    if not exempt and reason:\n'
        '        raise ValueError("runtime wallclock reason requires hosted-cpu exemption")\n'
        '    return not exempt\n\n\n'
        'def _validate_runtime(\n',
        "evaluator wallclock contract",
    )
    text = replace_once(
        text,
        '    records = runtime.get("cases")\n'
        '    runtime_ids = set(_case_ids(records))\n',
        '    wallclock_applicable = _runtime_wallclock_applicable(runtime)\n'
        '    records = runtime.get("cases")\n'
        '    runtime_ids = set(_case_ids(records))\n',
        "evaluator runtime wallclock flag",
    )
    text = replace_once(
        text,
        '        if marker_violation or not _runtime_budget_is_valid(record, gate):\n'
        '            budget_violations += 1\n',
        '        if marker_violation or not _runtime_budget_is_valid(\n'
        '            record,\n'
        '            gate,\n'
        '            wallclock_applicable=wallclock_applicable,\n'
        '        ):\n'
        '            budget_violations += 1\n',
        "evaluator budget call",
    )
    path.write_text(text, encoding="utf-8")


def patch_tests() -> None:
    path = Path("tests/test_rq1c_bounded_qualification.py")
    text = path.read_text(encoding="utf-8")
    anchor = 'def test_failed_protocol_probe_forces_no_go(tmp_path: Path) -> None:\n'
    insertion = '''def test_wallclock_budget_is_enforced_by_default(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime = _runtime(case_ids)
    runtime["cases"][0]["budget_observed"]["elapsed_seconds"] = 61.0  # type: ignore[index]

    report = _evaluate_fixture_set(tmp_path, runtime=runtime)

    assert report["decision"] == "NO-GO"
    assert report["checks"]["runtime_budget"] is False  # type: ignore[index]


def test_hosted_cpu_exemption_skips_only_wallclock_budget(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime = _runtime(case_ids)
    runtime["wallclock_contract"] = {
        "product_soft_timeout_seconds": 45,
        "product_hard_timeout_seconds": 60,
        "hosted_cpu_exempt": True,
        "reason": "github_hosted_local_model_cpu",
    }
    runtime["cases"][0]["budget_observed"]["elapsed_seconds"] = 240.0  # type: ignore[index]

    report = _evaluate_fixture_set(tmp_path, runtime=runtime)

    assert report["decision"] == "GO"
    assert report["checks"]["runtime_budget"] is True  # type: ignore[index]

    runtime["cases"][0]["budget_observed"]["candidate_count"] = 21  # type: ignore[index]
    report = _evaluate_fixture_set(tmp_path, runtime=runtime)
    assert report["decision"] == "NO-GO"
    assert report["checks"]["runtime_budget"] is False  # type: ignore[index]


def test_hosted_cpu_exemption_requires_exact_bounded_contract(tmp_path: Path) -> None:
    rubric = _rubric()
    case_ids = [str(case["id"]) for case in rubric["cases"]]  # type: ignore[index]
    runtime = _runtime(case_ids)
    runtime["wallclock_contract"] = {
        "product_soft_timeout_seconds": 45,
        "product_hard_timeout_seconds": 60,
        "hosted_cpu_exempt": True,
        "reason": "anything-else",
    }

    with pytest.raises(ValueError, match="exemption reason invalid"):
        _evaluate_fixture_set(tmp_path, runtime=runtime)


'''
    text = replace_once(text, anchor, insertion + anchor, "test insertion")
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    patch_core()
    patch_evaluator()
    patch_tests()
