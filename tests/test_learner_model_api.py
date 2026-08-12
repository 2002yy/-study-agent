from __future__ import annotations

from fastapi.testclient import TestClient

from src.api import app
from src.application.runtime_repository import get_learner_model_service
from src.domain.learner_model import (
    ConfirmedLearnerPreference,
    LearnerClaimState,
    LearnerEvaluationSummary,
    LearnerModelSnapshot,
)


class FakeLearnerModelService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def build(self, thread_id: str) -> LearnerModelSnapshot:
        self.calls.append(thread_id)
        return LearnerModelSnapshot(
            thread_id=thread_id,
            goal_id="goal-api",
            topic_id="topic-api",
            objective="Explain the API boundary",
            goal_status="active",
            claim_states=(
                LearnerClaimState(
                    claim_id="claim-api",
                    revision_id="revision-api",
                    claim_kind="boundary",
                    understanding_status="confirmed",
                    validation_result="pass",
                ),
            ),
            unresolved_count=1,
            evaluation=LearnerEvaluationSummary(
                run_count=2,
                accepted_count=1,
                review_required_count=1,
                protocols=("feynman",),
                evaluator_versions=("pedagogy-eval-v1",),
            ),
            confirmed_profile=(
                ConfirmedLearnerPreference(
                    category="learning_preference",
                    value="先看机制再看结论",
                ),
            ),
        )


def test_learner_model_endpoint_exposes_only_bounded_projection(
    runtime_test_context,
) -> None:
    session = runtime_test_context.session_service.create_session({})
    service = FakeLearnerModelService()
    app.dependency_overrides[get_learner_model_service] = lambda: service
    try:
        response = TestClient(app).get(f"/sessions/{session.id}/learner-model")
    finally:
        app.dependency_overrides.pop(get_learner_model_service, None)

    assert response.status_code == 200
    payload = response.json()
    assert service.calls == [session.id]
    assert payload["source"] == "derived_read_only"
    assert payload["claim_states"][0]["understanding_status"] == "confirmed"
    assert payload["evaluation"] == {
        "run_count": 2,
        "accepted_count": 1,
        "rejected_count": 0,
        "review_required_count": 1,
        "protocols": ["feynman"],
        "evaluator_versions": ["pedagogy-eval-v1"],
    }
    assert payload["confirmed_profile"] == [
        {"category": "learning_preference", "value": "先看机制再看结论"}
    ]
    assert "learner_input" not in str(payload)
    assert "user_response" not in str(payload)
    assert "mastery" not in str(payload)


def test_learner_model_endpoint_rejects_missing_session_before_projection() -> None:
    service = FakeLearnerModelService()
    app.dependency_overrides[get_learner_model_service] = lambda: service
    try:
        response = TestClient(app).get("/sessions/missing/learner-model")
    finally:
        app.dependency_overrides.pop(get_learner_model_service, None)

    assert response.status_code == 404
    assert response.json()["detail"] == "Session not found"
    assert service.calls == []
