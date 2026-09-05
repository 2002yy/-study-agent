"""Non-bypassable compatibility facade for deterministic RQ1-C protocol probes."""

from __future__ import annotations

import json
from typing import Any

from tools import run_rq1c_protocol_probes_core as _core

REPO_ROOT = _core.REPO_ROOT
REQUIRED_PROBES = _core.REQUIRED_PROBES
DEFAULT_RUNTIME = _core.DEFAULT_RUNTIME
DEFAULT_OUTPUT = _core.DEFAULT_OUTPUT
_parser = _core._parser
_git_sha = _core._git_sha


def run_protocol_probes(*args: Any, **kwargs: Any) -> dict[str, Any]:
    original_git_sha = _core._git_sha
    _core._git_sha = _git_sha
    try:
        return _core.run_protocol_probes(*args, **kwargs)
    finally:
        _core._git_sha = original_git_sha


def main() -> int:
    args = _parser().parse_args()
    artifact = run_protocol_probes(
        runtime_path=args.runtime.resolve(),
        output_path=args.output.resolve(),
    )
    print(json.dumps(artifact["summary"], ensure_ascii=False, sort_keys=True))
    return 0 if not artifact["summary"]["failed"] else 2


def __getattr__(name: str) -> Any:
    return getattr(_core, name)


if __name__ == "__main__":
    from tools.run_rq1c_protocol_probes import main as guarded_main

    raise SystemExit(guarded_main())
