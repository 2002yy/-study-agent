"""Public response contracts for the read-only learner-model projection."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LearnerClaimStateResponse(BaseModel):
    claim_id: str
    revision_id: str
    claim_kind: str
    understanding_status: str
    validation_result: str


class LearnerEvaluationSummaryResponse(BaseModel):
    run_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    review_required_count: int = 0
    protocols: list[str] = Field(default_factory=list)
    evaluator_versions: list[str] = Field(default_factory=list)


class ConfirmedLearnerPreferenceResponse(BaseModel):
    category: str
    value: str


class LearnerModelSnapshotResponse(BaseModel):
    thread_id: str
    source: str
    goal_id: str = ""
    topic_id: str = ""
    objective: str = ""
    goal_status: str = ""
    claim_states: list[LearnerClaimStateResponse] = Field(default_factory=list)
    unresolved_count: int = 0
    evaluation: LearnerEvaluationSummaryResponse = Field(
        default_factory=LearnerEvaluationSummaryResponse
    )
    confirmed_profile: list[ConfirmedLearnerPreferenceResponse] = Field(
        default_factory=list
    )
