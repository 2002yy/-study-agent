"""Exact-head wrapper for deterministic RQ1-C protocol probes."""

from __future__ import annotations

from tools import run_rq1c_protocol_probes_impl as _impl
from tools.rq1c_git_identity import exact_checkout_git_sha

REQUIRED_PROBES = _impl.REQUIRED_PROBES


def _git_sha() -> str:
    return exact_checkout_git_sha(_impl.REPO_ROOT)


_impl._git_sha = _git_sha

run_protocol_probes = _impl.run_protocol_probes


def main() -> int:
    return _impl.main()


if __name__ == "__main__":
    raise SystemExit(main())
