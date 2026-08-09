"""Commit durable learning outcomes after evidence convergence.

This service does not decide user mastery. It only turns an already-worthy durable
assertion into a source-backed Claim revision, or preserves unsupported uncertainty
as a LearningHypothesis when no qualified Primary Evidence exists.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.application.learning_source_evidence import EvidenceConvergenceResult
from src.domain.learning_truth import (
    ClaimRevision,
    ClaimRevisionBundle,
    LearningClaim,
    LearningHypothesis,
)
from src.repositories.learning_truth_repository import LearningTruthRepository


_DURABLE_CLAIM_KINDS = {
    "mechanism",
    "boundary",
    "invariant",
    "decision_relevant_fact",
}
_HYPOTHESIS_REASONS = {
    "missing_source",
    "ambiguous_owner",
    "insufficient_evidence",
    "external_dependency",
    "provider_unavailable",
}
_EXISTING_REVISION_REASONS = {"revalidated", "meaning_changed"}


@dataclass(frozen=True)
class LearningOutcomeCommitResult:
    outcome: str
    claim: LearningClaim | None = None
    revision: ClaimRevisionBundle | None = None
    hypothesis: LearningHypothesis | None = None


class LearningOutcomeCommitService:
    """Single application boundary for Claim-or-Hypothesis durable outcomes."""

    def __init__(self, repository: LearningTruthRepository) -> None:
        self.repository = repository

    def commit(
        self,
        *,
        topic_id: str,
        goal_id: str,
        claim_text: str,
        claim_kind: str,
        convergence: EvidenceConvergenceResult,
        scope: str = "project",
        existing_claim_id: str | None = None,
        revision_reason: str | None = None,
        unresolved_reason: str | None = None,
    ) -> LearningOutcomeCommitResult:
        text = " ".join(str(claim_text or "").split())
        if not text:
            raise ValueError("Durable learning assertion text is required")
        if claim_kind not in _DURABLE_CLAIM_KINDS:
            raise ValueError("Unsupported durable learning claim kind")
        if scope not in {"project", "general"}:
            raise ValueError("Unsupported learning claim scope")

        topic = self.repository.get_topic(topic_id)
        if topic is None:
            raise ValueError(f"Learning topic not found: {topic_id}")
        goal = self.repository.get_goal(goal_id)
        if goal is None:
            raise ValueError(f"Learning goal not found: {goal_id}")
        if goal.topic_id != topic_id:
            raise ValueError("Learning goal belongs to another topic")

        if not convergence.claim_ready or convergence.primary is None:
            if existing_claim_id is not None:
                raise ValueError("Cannot revise an existing Claim without Primary Evidence")
            if revision_reason is not None:
                raise ValueError("Hypothesis outcome cannot have a Claim revision reason")
            reason = _hypothesis_reason(
                unresolved_reason or convergence.unresolved_reason
            )
            hypothesis = self.repository.create_hypothesis(
                LearningHypothesis(
                    topic_id=topic_id,
                    goal_id=goal_id,
                    text=text,
                    unresolved_reason=reason,
                )
            )
            return LearningOutcomeCommitResult(
                outcome="hypothesis",
                hypothesis=hypothesis,
            )

        primary_commit = convergence.primary.source.commit_sha
        bindings = convergence.bindings
        if existing_claim_id is None:
            if revision_reason not in {None, "initial"}:
                raise ValueError("New Claim must use the initial revision reason")
            claim = LearningClaim(
                topic_id=topic_id,
                scope=scope,
                claim_kind=claim_kind,
            )
            revision = ClaimRevision(
                claim_id=claim.id,
                claim_text=text,
                source_commit=primary_commit,
                reason="initial",
            )
            bundle = self.repository.commit_new_claim(
                claim,
                revision,
                bindings,
                goal_id=goal_id,
            )
            return LearningOutcomeCommitResult(
                outcome="claim",
                claim=claim,
                revision=bundle,
            )

        existing_claim = self.repository.get_claim(existing_claim_id)
        if existing_claim is None:
            raise ValueError(f"Learning claim not found: {existing_claim_id}")
        if existing_claim.topic_id != topic_id:
            raise ValueError("Existing Claim belongs to another topic")
        if existing_claim.scope != scope:
            raise ValueError("Existing Claim scope does not match requested scope")
        if existing_claim.claim_kind != claim_kind:
            raise ValueError("Existing Claim kind does not match requested kind")
        if revision_reason not in _EXISTING_REVISION_REASONS:
            raise ValueError(
                "Existing Claim revision requires explicit revalidated or meaning_changed reason"
            )

        revision = ClaimRevision(
            claim_id=existing_claim.id,
            claim_text=text,
            source_commit=primary_commit,
            reason=revision_reason,
        )
        bundle = self.repository.commit_revision(
            revision,
            bindings,
            goal_id=goal_id,
        )
        return LearningOutcomeCommitResult(
            outcome="claim",
            claim=existing_claim,
            revision=bundle,
        )


def _hypothesis_reason(raw: str) -> str:
    reason = str(raw or "").strip()
    if reason in _HYPOTHESIS_REASONS:
        return reason
    return "insufficient_evidence"
