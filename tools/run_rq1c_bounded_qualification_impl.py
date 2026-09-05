"""Non-bypassable compatibility facade for the RQ1-C qualification core.

The large core remains byte-identical to the previously reviewed runner, but it
is no longer a directly executable qualification entry point. Guard wiring
patches this facade, and direct script execution delegates back to the public
strictly bounded entry point.
"""

from __future__ import annotations

import json
from typing import Any

from tools import run_rq1c_bounded_qualification_core as _core

REPO_ROOT = _core.REPO_ROOT
DEFAULT_MANIFEST = _core.DEFAULT_MANIFEST
DEFAULT_OUTPUT = _core.DEFAULT_OUTPUT

_evidence_rows = _core._evidence_rows
_load_manifest = _core._load_manifest
_observed_read_count = _core._observed_read_count
_provider_audit = _core._provider_audit
_source_rows = _core._source_rows
_unavailable_answer_surface = _core._unavailable_answer_surface
_answer_stage_model_calls = _core._answer_stage_model_calls
_production_answer_surface = _core._production_answer_surface
_production_chat_command = _core._production_chat_command
_active_context = _core._active_context
_parser = _core._parser

_git_sha = _core._git_sha
_build_chat_service = _core._build_chat_service
_CORE_RUN_CASE = _core._run_case


def _run_case(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Run the immutable core case using the facade's currently patched builder."""
    original_builder = _core._build_chat_service
    _core._build_chat_service = _build_chat_service
    try:
        return _CORE_RUN_CASE(*args, **kwargs)
    finally:
        _core._build_chat_service = original_builder


def run_qualification(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Propagate guard hooks into the immutable core for one qualification run."""
    original_git_sha = _core._git_sha
    original_run_case = _core._run_case
    _core._git_sha = _git_sha
    _core._run_case = _run_case
    try:
        return _core.run_qualification(*args, **kwargs)
    finally:
        _core._git_sha = original_git_sha
        _core._run_case = original_run_case


def main() -> int:
    args = _parser().parse_args()
    artifact = run_qualification(
        manifest_path=args.manifest.resolve(),
        output_path=args.output.resolve(),
    )
    print(json.dumps(artifact["summary"], ensure_ascii=False, sort_keys=True))
    structural_ok = (
        artifact["summary"]["case_count"] == 12
        and artifact["summary"]["runner_error_cases"] == 0
        and artifact["summary"]["budget_violation_cases"] == 0
        and artifact["summary"]["reviewable_answer_cases"] == 12
    )
    return 0 if structural_ok else 2


def __getattr__(name: str) -> Any:
    return getattr(_core, name)


if __name__ == "__main__":
    from tools.run_rq1c_bounded_qualification import main as guarded_main

    raise SystemExit(guarded_main())
