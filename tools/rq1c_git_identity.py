"""Exact git identity binding for RQ1-C qualification artifacts."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

_HEX40 = re.compile(r"^[0-9a-f]{40}$")


def exact_checkout_git_sha(repo_root: Path) -> str:
    """Return checkout HEAD and fail closed on a conflicting GITHUB_SHA."""

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("RQ1-C qualification requires a readable git HEAD") from exc

    head = completed.stdout.strip().lower()
    if not _HEX40.fullmatch(head):
        raise RuntimeError("RQ1-C checkout HEAD is not an exact 40-character git sha")

    configured_raw = str(os.getenv("GITHUB_SHA") or "").strip().lower()
    if configured_raw:
        if not _HEX40.fullmatch(configured_raw):
            raise RuntimeError("GITHUB_SHA is present but is not an exact git sha")
        if configured_raw != head:
            raise RuntimeError(
                "GITHUB_SHA does not match the checked-out RQ1-C qualification HEAD"
            )
    return head
