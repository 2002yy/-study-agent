"""Public entrypoint for the strictly bounded RQ1-C qualification."""

from __future__ import annotations

from typing import Any

from tools import run_rq1c_bounded_qualification_impl as _impl

# The guard blob is intentionally loaded only after this compatibility alias is
# installed.  Its reviewed entry binding then resolves to the canonical core
# function while all per-case hook lookups still occur through `_impl`.
_impl.Run_qualification = _impl.run_qualification
from tools import run_rq1c_bounded_qualification_guard as _guard  # noqa: E402

MAX_MODEL_CALLS = _guard.MAX_MODEL_CALLS
HARD_TIMEOUT_SECONDS = _guard.HARD_TIMEOUT_SECONDS
QualificationModelBudgetExhausted = _guard.QualificationModelBudgetExhausted
QualificationHardDeadlineReached = _guard.QualificationHardDeadlineReached
_AnswerStageBudget = _guard._AnswerStageBudget
_ResearchBudgetProxy = _guard._ResearchBudgetProxy
_evidence_rows = _guard._evidence_rows
_load_manifest = _guard._load_manifest
_observed_read_count = _guard._observed_read_count
_provider_audit = _guard._provider_audit
_source_rows = _guard._source_rows
_unavailable_answer_surface = _guard._unavailable_answer_surface
_answer_stage_model_calls = _guard._answer_stage_model_calls
_production_answer_surface = _guard._production_answer_surface
_production_chat_command = _guard._production_chat_command
_active_context = _guard._active_context
_git_sha = _guard._git_sha
_parser = _guard._parser

# Keep the test seam on this public module.  The guard calls this proxy, whose
# global lookup observes monkeypatches of `runner._production_chat`.
_production_chat = _guard._production_chat


def _production_chat_proxy(messages: list[dict], **kwargs: Any) -> str:
    return _production_chat(messages, **kwargs)


_guard._production_chat = _production_chat_proxy

run_qualification = _guard.run_qualification


def main() -> int:
    return _guard.main()


if __name__ == "__main__":
    raise SystemExit(main())
