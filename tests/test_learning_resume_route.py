from __future__ import annotations

import pytest
from fastapi import HTTPException

import src.api.routes.session_routes as session_routes


class FakeResumeService:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.calls: list[dict] = []

    def build(self, session_id: str, **kwargs) -> dict:
        self.calls.append({"session_id": session_id, **kwargs})
        return self.responses.pop(0)


class FakeSessionService:
    def __init__(self, detail: dict | None = None) -> None:
        self.detail = detail
        self.calls: list[str] = []

    def get_session(self, session_id: str) -> dict | None:
        self.calls.append(session_id)
        return self.detail


def test_durable_resume_route_does_not_replay_session_history(monkeypatch):
    resume_service = FakeResumeService(
        [
            {
                "source": "durable",
                "status": "active",
                "goal": {"goal_id": "goal-1"},
                "claims": [],
            }
        ]
    )
    session_service = FakeSessionService(detail={"navigation": {"objective": "legacy"}})
    monkeypatch.setattr(
        session_routes,
        "get_learning_resume_service",
        lambda: resume_service,
    )

    result = session_routes.get_learning_resume(  # type: ignore[arg-type]
        "thread-1",
        session_service,
    )

    assert result["source"] == "durable"
    assert session_service.calls == []
    assert resume_service.calls == [{"session_id": "thread-1"}]


def test_legacy_resume_route_uses_existing_navigation_projection_only_as_fallback(monkeypatch):
    resume_service = FakeResumeService(
        [
            {"source": "legacy_fallback", "status": "empty"},
            {
                "source": "legacy_fallback",
                "status": "legacy",
                "goal": {"objective": "legacy objective"},
                "claims": [],
            },
        ]
    )
    session_service = FakeSessionService(
        detail={
            "navigation": {
                "objective": "legacy objective",
                "confirmed_points": ["legacy point"],
            }
        }
    )
    monkeypatch.setattr(
        session_routes,
        "get_learning_resume_service",
        lambda: resume_service,
    )

    result = session_routes.get_learning_resume(  # type: ignore[arg-type]
        "legacy-thread",
        session_service,
    )

    assert result["source"] == "legacy_fallback"
    assert session_service.calls == ["legacy-thread"]
    assert resume_service.calls == [
        {"session_id": "legacy-thread"},
        {
            "session_id": "legacy-thread",
            "legacy_navigation": {
                "objective": "legacy objective",
                "confirmed_points": ["legacy point"],
            },
        },
    ]


def test_missing_legacy_session_returns_404(monkeypatch):
    resume_service = FakeResumeService(
        [{"source": "legacy_fallback", "status": "empty"}]
    )
    session_service = FakeSessionService(detail=None)
    monkeypatch.setattr(
        session_routes,
        "get_learning_resume_service",
        lambda: resume_service,
    )

    with pytest.raises(HTTPException) as exc_info:
        session_routes.get_learning_resume(  # type: ignore[arg-type]
            "missing-thread",
            session_service,
        )

    assert exc_info.value.status_code == 404
    assert session_service.calls == ["missing-thread"]
