from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION_IMPL = REPO_ROOT / "tools" / "run_rq1c_bounded_qualification_impl.py"
PROTOCOL_IMPL = REPO_ROOT / "tools" / "run_rq1c_protocol_probes_impl.py"
MANIFEST = (
    REPO_ROOT
    / "tests"
    / "fixtures"
    / "research_quality"
    / "rq1c_bounded_holdout_manifest.json"
)
_STALE_SHA = "0" * 40
_GIT_MISMATCH = "GITHUB_SHA does not match the checked-out RQ1-C qualification HEAD"


def _stale_sha_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GITHUB_SHA"] = _STALE_SHA
    return env


def test_direct_qualification_impl_execution_cannot_bypass_guard(tmp_path: Path) -> None:
    output = tmp_path / "runtime.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(QUALIFICATION_IMPL),
            "--manifest",
            str(MANIFEST),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        env=_stale_sha_env(),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode != 0
    assert _GIT_MISMATCH in completed.stderr
    assert not output.exists()


def test_direct_protocol_impl_execution_cannot_bypass_exact_head_guard(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "runtime.json"
    output = tmp_path / "protocol.json"
    runtime.write_text(
        json.dumps(
            {
                "schema_version": "rq1c-bounded-qualification-runtime-v1",
                "cases": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(PROTOCOL_IMPL),
            "--runtime",
            str(runtime),
            "--output",
            str(output),
        ],
        cwd=REPO_ROOT,
        env=_stale_sha_env(),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert completed.returncode != 0
    assert _GIT_MISMATCH in completed.stderr
    assert not output.exists()
