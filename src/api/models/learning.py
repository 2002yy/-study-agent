"""API models for explicit P2-D durable learning writes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class LearningClaimCommitRequest(BaseModel):
    turn_id: str = Field(min_length=1)
    claim_text: str = Field(min_length=1, max_length=600)
    claim_kind: Literal[
        "mechanism",
        "boundary",
        "invariant",
        "decision_relevant_fact",
    ] = "mechanism"
    scope: Literal["project", "general"] = "project"
    topic_id: str | None = None
    topic_title: str = Field(default="", max_length=160)
    goal_id: str | None = None
    goal_objective: str = Field(default="", max_length=600)


class LearningValidationRequest(BaseModel):
    revision_ids: list[str] = Field(min_length=1, max_length=3)
    turn_id: str | None = None
    method: Literal["explain", "apply", "practice"] = "explain"
    complete_goal: bool = False
    skip_validation: bool = False
    next_step_text: str = Field(default="", max_length=600)
