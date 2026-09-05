from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

import tools.rq1c_git_identity as identity


HEAD = "a" * 40
OTHER = "b" * 40


def _completed(stdout: str = HEAD) -> SimpleNamespace:
    return SimpleNamespace(stdout=stdout + "\n")


def test_exact_checkout_sha_uses_git_head_when_ci_sha_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(identity.subprocess, "run", lambda *args, **kwargs: _completed())

    assert identity.exact_checkout_git_sha(Path(".")) == HEAD


def test_exact_checkout_sha_accepts_matching_ci_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_SHA", HEAD)
    monkeypatch.setattr(identity.subprocess, "run", lambda *args, **kwargs: _completed())

    assert identity.exact_checkout_git_sha(Path(".")) == HEAD


def test_exact_checkout_sha_rejects_well_formed_but_stale_ci_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_SHA", OTHER)
    monkeypatch.setattr(identity.subprocess, "run", lambda *args, **kwargs: _completed())

    with pytest.raises(RuntimeError, match="does not match"):
        identity.exact_checkout_git_sha(Path("."))


def test_exact_checkout_sha_rejects_malformed_ci_sha(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_SHA", "not-a-sha")
    monkeypatch.setattr(identity.subprocess, "run", lambda *args, **kwargs: _completed())

    with pytest.raises(RuntimeError, match="not an exact git sha"):
        identity.exact_checkout_git_sha(Path("."))


def test_exact_checkout_sha_rejects_malformed_checkout_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setattr(
        identity.subprocess,
        "run",
        lambda *args, **kwargs: _completed("not-a-checkout-sha"),
    )

    with pytest.raises(RuntimeError, match="checkout HEAD"):
        identity.exact_checkout_git_sha(Path("."))
