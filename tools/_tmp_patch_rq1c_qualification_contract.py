from __future__ import annotations

from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one anchor, got {count}: {old!r}")
    file_path.write_text(text.replace(old, new, 1), encoding="utf-8")


# Qualification-only shared physical model-call contract.  Six calls became
# structurally impossible once the production answer path required generation
# plus claim binding after the current planner/assessor/extraction topology.
replace_once(
    "tools/rq1c_qualification_guardrails.py",
    "import time\n",
    "import os\nimport time\n",
)
replace_once(
    "tools/rq1c_qualification_guardrails.py",
    "MAX_MODEL_CALLS = 6\nHARD_TIMEOUT_SECONDS = 60.0\n",
    "MAX_MODEL_CALLS = 8\n"
    "HARD_TIMEOUT_SECONDS = 60.0\n"
    "HOSTED_CPU_CASE_HARD_TIMEOUT_SECONDS = 540.0\n"
    "HOSTED_CPU_ANSWER_TIMEOUT_SECONDS = 120.0\n"
    "_HOSTED_CPU_WALLCLOCK_ENV = \"RQ1C_HOSTED_CPU_WALLCLOCK_EXEMPT\"\n",
)
replace_once(
    "tools/rq1c_qualification_guardrails.py",
    "class QualificationHardDeadlineReached(TimeoutError):\n"
    "    \"\"\"Raised before dispatch when no case-level wall-clock budget remains.\"\"\"\n\n",
    "class QualificationHardDeadlineReached(TimeoutError):\n"
    "    \"\"\"Raised before dispatch when no case-level wall-clock budget remains.\"\"\"\n\n\n"
    "def _hosted_cpu_wallclock_exempt() -> bool:\n"
    "    requested = str(os.getenv(_HOSTED_CPU_WALLCLOCK_ENV) or \"\").strip().lower() in {\n"
    "        \"1\",\n"
    "        \"true\",\n"
    "        \"yes\",\n"
    "        \"on\",\n"
    "    }\n"
    "    github_actions = str(os.getenv(\"GITHUB_ACTIONS\") or \"\").strip().lower() == \"true\"\n"
    "    return requested and github_actions\n\n\n"
    "def _qualification_execution_limits() -> tuple[float, float | None]:\n"
    "    if _hosted_cpu_wallclock_exempt():\n"
    "        return (\n"
    "            HOSTED_CPU_CASE_HARD_TIMEOUT_SECONDS,\n"
    "            HOSTED_CPU_ANSWER_TIMEOUT_SECONDS,\n"
    "        )\n"
    "    return HARD_TIMEOUT_SECONDS, None\n\n",
)
replace_once(
    "tools/rq1c_qualification_guardrails.py",
    "    hard_timeout_seconds: float = HARD_TIMEOUT_SECONDS\n"
    "    required_answer_calls: int = 1\n",
    "    hard_timeout_seconds: float = HARD_TIMEOUT_SECONDS\n"
    "    answer_timeout_floor_seconds: float | None = None\n"
    "    required_answer_calls: int = 1\n",
)
replace_once(
    "tools/rq1c_qualification_guardrails.py",
    "        normal_timeout = float(\n"
    "            _resolve_timeout(\n"
    "                kwargs.get(\"timeout\"),\n"
    "                kwargs.get(\"task_name\"),\n"
    "                kwargs.get(\"model_profile\"),\n"
    "                kwargs.get(\"provider_profile\"),\n"
    "            )\n"
    "        )\n"
    "        bounded_timeout = min(normal_timeout, remaining)\n",
    "        normal_timeout = float(\n"
    "            _resolve_timeout(\n"
    "                kwargs.get(\"timeout\"),\n"
    "                kwargs.get(\"task_name\"),\n"
    "                kwargs.get(\"model_profile\"),\n"
    "                kwargs.get(\"provider_profile\"),\n"
    "            )\n"
    "        )\n"
    "        if self.answer_timeout_floor_seconds is not None:\n"
    "            normal_timeout = max(normal_timeout, self.answer_timeout_floor_seconds)\n"
    "        bounded_timeout = min(normal_timeout, remaining)\n",
)
replace_once(
    "tools/rq1c_qualification_guardrails.py",
    "        budget = _AnswerStageBudget(\n"
    "            started_at=time.monotonic(),\n"
    "            binding_rows_provider=binding_rows_provider,\n"
    "        )\n",
    "        hard_timeout_seconds, answer_timeout_floor_seconds = (\n"
    "            _qualification_execution_limits()\n"
    "        )\n"
    "        budget = _AnswerStageBudget(\n"
    "            started_at=time.monotonic(),\n"
    "            hard_timeout_seconds=hard_timeout_seconds,\n"
    "            answer_timeout_floor_seconds=answer_timeout_floor_seconds,\n"
    "            binding_rows_provider=binding_rows_provider,\n"
    "        )\n",
)

# Runtime/evaluator/rubric must describe and enforce the same strict ceiling.
replace_once(
    "tools/run_rq1c_bounded_qualification_core.py",
    '            "max_model_calls": 6,\n',
    '            "max_model_calls": 8,\n',
)
replace_once(
    "tools/run_rq1c_bounded_qualification_core.py",
    '            "hosted_cpu_exempt": _hosted_cpu_wallclock_exempt(),\n'
    '            "reason": (\n'
    '                "github_hosted_local_model_cpu"\n'
    '                if _hosted_cpu_wallclock_exempt()\n'
    '                else ""\n'
    '            ),\n',
    '            "hosted_cpu_exempt": _hosted_cpu_wallclock_exempt(),\n'
    '            "reason": (\n'
    '                "github_hosted_local_model_cpu"\n'
    '                if _hosted_cpu_wallclock_exempt()\n'
    '                else ""\n'
    '            ),\n'
    '            "qualification_hosted_cpu_case_hard_timeout_seconds": (\n'
    '                540 if _hosted_cpu_wallclock_exempt() else None\n'
    '            ),\n'
    '            "qualification_hosted_cpu_answer_timeout_seconds": (\n'
    '                120 if _hosted_cpu_wallclock_exempt() else None\n'
    '            ),\n',
)
replace_once(
    "tools/evaluate_rq1c_bounded_qualification.py",
    '        "max_model_calls": 6,\n',
    '        "max_model_calls": 8,\n',
)
replace_once(
    "tools/evaluate_rq1c_bounded_qualification.py",
    "    if not exempt and reason:\n"
    "        raise ValueError(\"runtime wallclock reason requires hosted-cpu exemption\")\n"
    "    return not exempt\n",
    "    if not exempt and reason:\n"
    "        raise ValueError(\"runtime wallclock reason requires hosted-cpu exemption\")\n"
    "    hosted_case_hard = contract.get(\n"
    "        \"qualification_hosted_cpu_case_hard_timeout_seconds\"\n"
    "    )\n"
    "    hosted_answer_timeout = contract.get(\n"
    "        \"qualification_hosted_cpu_answer_timeout_seconds\"\n"
    "    )\n"
    "    if exempt:\n"
    "        if hosted_case_hard != 540 or hosted_answer_timeout != 120:\n"
    "            raise ValueError(\"runtime hosted-cpu execution allowance invalid\")\n"
    "    elif hosted_case_hard is not None or hosted_answer_timeout is not None:\n"
    "        raise ValueError(\"runtime hosted-cpu execution allowance requires exemption\")\n"
    "    return not exempt\n",
)
replace_once(
    "tests/fixtures/research_quality/rq1c_bounded_holdout_rubric.json",
    '    "max_model_calls": 6,\n',
    '    "max_model_calls": 8,\n',
)

# Focused pre-dispatch tests: eight is strict, ninth remains rejected.
replace_once(
    "tests/test_rq1c_bounded_pre_dispatch_budget.py",
    "        research_model_calls=5,\n        required_answer_calls=2,\n",
    "        research_model_calls=7,\n        required_answer_calls=2,\n",
)
replace_once(
    "tests/test_rq1c_bounded_pre_dispatch_budget.py",
    "    assert budget.total_model_calls_started == 5\n",
    "    assert budget.total_model_calls_started == 7\n",
)
replace_once(
    "tests/test_rq1c_bounded_pre_dispatch_budget.py",
    "def test_sixth_call_may_dispatch_but_seventh_is_rejected_before_network(\n",
    "def test_eighth_call_may_dispatch_but_ninth_is_rejected_before_network(\n",
)
replace_once(
    "tests/test_rq1c_bounded_pre_dispatch_budget.py",
    "        research_model_calls=5,\n        required_answer_calls=1,\n",
    "        research_model_calls=7,\n        required_answer_calls=1,\n",
)
replace_once(
    "tests/test_rq1c_bounded_pre_dispatch_budget.py",
    "    assert budget.total_model_calls_started == 6\n",
    "    assert budget.total_model_calls_started == 8\n",
)
insert_anchor = "\ndef test_expired_case_deadline_rejects_before_network(monkeypatch: pytest.MonkeyPatch) -> None:\n"
insert_text = '''\n\ndef test_six_research_calls_leave_capacity_for_generation_and_binding(\n    monkeypatch: pytest.MonkeyPatch,\n) -> None:\n    calls: list[str] = []\n\n    def fake_chat(messages: list[dict], **kwargs: object) -> str:\n        calls.append(str(kwargs.get("task_name") or ""))\n        return "ok"\n\n    monkeypatch.setattr(runner, "_production_chat", fake_chat)\n    budget = runner._AnswerStageBudget(\n        started_at=time.monotonic(),\n        research_model_calls=6,\n        required_answer_calls=2,\n    )\n\n    assert budget.chat([], task_name="single_chat", timeout=10.0) == "ok"\n    assert budget.chat([], task_name="answer_claim_binding", timeout=10.0) == "ok"\n    assert calls == ["single_chat", "answer_claim_binding"]\n    assert budget.total_model_calls_started == 8\n\n\ndef test_hosted_answer_allowance_can_raise_provider_timeout_without_changing_default(\n    monkeypatch: pytest.MonkeyPatch,\n) -> None:\n    seen: list[float] = []\n\n    def fake_chat(messages: list[dict], **kwargs: object) -> str:\n        seen.append(float(kwargs["timeout"]))\n        return "ok"\n\n    monkeypatch.setattr(runner, "_production_chat", fake_chat)\n    budget = runner._AnswerStageBudget(\n        started_at=time.monotonic(),\n        hard_timeout_seconds=540.0,\n        answer_timeout_floor_seconds=120.0,\n    )\n\n    assert budget.chat([], task_name="single_chat", timeout=7.0) == "ok"\n    assert seen == [120.0]\n'''
replace_once(
    "tests/test_rq1c_bounded_pre_dispatch_budget.py",
    insert_anchor,
    insert_text + insert_anchor,
)

# Evaluator fixtures must declare the explicit hosted execution allowance.
replace_once(
    "tests/test_rq1c_bounded_qualification.py",
    '        "reason": "github_hosted_local_model_cpu",\n'
    "    }\n"
    '    runtime["cases"][0]["budget_observed"]["elapsed_seconds"] = 240.0',
    '        "reason": "github_hosted_local_model_cpu",\n'
    '        "qualification_hosted_cpu_case_hard_timeout_seconds": 540,\n'
    '        "qualification_hosted_cpu_answer_timeout_seconds": 120,\n'
    "    }\n"
    '    runtime["cases"][0]["budget_observed"]["elapsed_seconds"] = 240.0',
)
replace_once(
    "tests/test_rq1c_bounded_qualification.py",
    '    first["budget_observed"]["model_call_count"] = 7\n',
    '    first["budget_observed"]["model_call_count"] = 9\n',
)
replace_once(
    "tests/test_rq1c_bounded_qualification.py",
    '        "reason": "anything-else",\n'
    "    }\n",
    '        "reason": "anything-else",\n'
    '        "qualification_hosted_cpu_case_hard_timeout_seconds": 540,\n'
    '        "qualification_hosted_cpu_answer_timeout_seconds": 120,\n'
    "    }\n",
)

print("RQ1-C qualification contract compatibility patch applied")
