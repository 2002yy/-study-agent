from __future__ import annotations

import pytest
from fastapi import HTTPException

import src.api.routes.session_routes as session_routes
from src.application.learning_revalidation import RevalidationResult


class FakeRevalidationService:
    def __init__(self, behavior: str) -> None:
        self.behavior = behavior
        self.calls: list[tuple[str, str]] = []

    def revalidate(self, thread_id: str, claim_id: str) -> RevalidationResult:
        self.calls.append((thread_id, claim_id))
        if self.behavior == "ok":
            return RevalidationResult(
                outcome="revalidated",
                claim_id=claim_id,
                revision_id="rev-2",
                head_commit="h" * 40,
                freshness_status="current",
            )
        if self.behavior == "no_convergence":
            return RevalidationResult(
                outcome="no_convergence",
                claim_id=claim_id,
                unresolved_reason="ambiguous_owner",
            )
        if self.behavior == "not_found":
            raise ValueError("claim_not_found")
        raise ValueError("no_active_goal")


def test_revalidate_route_commits_new_revision(monkeypatch):
    service = FakeRevalidationService("ok")
    monkeypatch.setattr(
        session_routes,
        "get_learning_revalidation_service",
        lambda: service,
    )
    result = session_routes.revalidate_claim("thread-1", "claim-1", service)

    assert result["outcome"] == "revalidated"
    assert result["claim_id"] == "claim-1"
    assert result["revision_id"] == "rev-2"
    assert result["freshness_status"] == "current"
    assert service.calls == [("thread-1", "claim-1")]


def test_revalidate_route_no_convergence_returns_unresolved(monkeypatch):
    service = FakeRevalidationService("no_convergence")
    monkeypatch.setattr(
        session_routes,
        "get_learning_revalidation_service",
        lambda: service,
    )
    result = session_routes.revalidate_claim("thread-1", "claim-1", service)

    assert result["outcome"] == "no_convergence"
    assert result["unresolved_reason"] == "ambiguous_owner"
    assert result["revision_id"] == ""


def test_revalidate_route_missing_claim_is_404(monkeypatch):
    service = FakeRevalidationService("not_found")
    monkeypatch.setattr(
        session_routes,
        "get_learning_revalidation_service",
        lambda: service,
    )
    with pytest.raises(HTTPException) as exc_info:
        session_routes.revalidate_claim("thread-1", "claim-1", service)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "claim_not_found"


def test_revalidate_route_no_active_goal_is_409(monkeypatch):
    service = FakeRevalidationService("no_goal")
    monkeypatch.setattr(
        session_routes,
        "get_learning_revalidation_service",
        lambda: service,
    )
    with pytest.raises(HTTPException) as exc_info:
        session_routes.revalidate_claim("thread-1", "claim-1", service)

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "no_active_goal"