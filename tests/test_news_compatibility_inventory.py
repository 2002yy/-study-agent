from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = (ROOT / "frontend" / "src", ROOT / "src", ROOT / "tests")
TOKENS = (
    "NewsWorkspace",
    "useNewsController",
    "NewsController",
    '"/news/runs',
    "'/news/runs",
    "/news/runs",
    "status_code=410",
    "HTTP_410_GONE",
)
SUFFIXES = {".py", ".ts", ".tsx"}


def test_inventory_news_compatibility_callers() -> None:
    matches: list[str] = []
    for scan_root in SCAN_ROOTS:
        for path in sorted(scan_root.rglob("*")):
            if not path.is_file() or path.suffix not in SUFFIXES:
                continue
            relative = path.relative_to(ROOT).as_posix()
            if relative == "tests/test_news_compatibility_inventory.py":
                continue
            for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
                if any(token in line for token in TOKENS):
                    matches.append(f"{relative}:{line_number}: {line.strip()}")

    pytest.fail("NEWS_COMPATIBILITY_INVENTORY\n" + "\n".join(matches))
