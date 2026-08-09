"""Semantic learning closure over durable P2-D truth.

The service records a user validation attempt only at an explicit semantic closure
boundary. It maps the existing PedagogyEvalRun into durable UnderstandingEvidence
without persisting evaluator confidence or hidden reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.learning_truth import (
    LearningGoal,
    NextStep,
    UnderstandingClaimResult,
    UnderstandingEvidence,
)
from src.pedagogy.evaluation import PedagogyEvalRun
from src.repositories.learning_truth_repository import LearningTruthRepository


_ALLOWED_METHODS = {"explain", "apply", "practice"}


@dataclass(frozen=True)
class LearningSemanticClosureResult:
    goal: LearningGoal
    validation_status: str
    understanding: UnderstandingEvidence | None = None
    claim_results: tuple[UnderstandingClaimResult, ...] = ()
    next_step: NextStep | None = None


class LearningSemanticClosureService:
    """Commit validation evidence and Goal navigation at a semantic section boundary."""

    def __init__(self, repository: LearningTruthRepository) -> None:
        self.repository = repository

    def close(
        self,
        *,
        goal_id: str,
        target_revision_ids: tuple[str, ...] = (),
        method: str = "explain",
        prompt: str = "",
        evaluation_run: PedagogyEvalRun | None = None,
        goal_status: str = "active",
        next_step_text: str = "",
        next_step_primary: bool = True,
        skip_validation: bool = False,
    ) -> LearningSemanticClosureResult:
        if method not in _ALLOWED_METHODS:
            raise ValueError("Unsupported UnderstandingEvidence method")
        if skip_validation:
            if evaluation_run is not None:
                raise ValueError("Skipped validation cannot also provide an evaluation run")
            if target_revision_ids:
                # The revisions remain deliberately unverified. Do not manufacture
                # empty UnderstandingEvidence rows merely because they were targeted.
                target_revision_ids = tuple(dict.fromkeys(target_revision_ids))
            understanding = None
            claim_results: tuple[UnderstandingClaimResult, ...] = ()
            validation_status = "skipped"
        else:
            if evaluation_run is None:
                raise ValueError("Semantic closure requires a PedagogyEvalRun or explicit skip")
            if not 1 <= len(target_revision_ids) <= 3:
                raise ValueError("Semantic closure must validate 1 to 3 Claim revisions")
            if len(set(target_revision_ids)) != len(target_revision_ids):
                raise ValueError("Semantic closure contains duplicate Claim revisions")
            if not prompt.strip():
                raise ValueError("Understanding validation prompt is required")
            mapped_result = _map_evaluation_result(evaluation_run)
            understanding = UnderstandingEvidence(
                method=method,
                prompt=prompt.strip(),
                user_response=evaluation_run.learner_input,
            )
            claim_results = tuple(
                UnderstandingClaimResult(
                    understanding_evidence_id=understanding.id,
                    claim_revision_id=revision_id,
                    result=mapped_result,
                )
                for revision_id in target_revision_ids
            )
            validation_status = mapped_result
            if goal_status == "completed" and mapped_result != "pass":
                raise ValueError(
                    "Learning Goal cannot complete from partial or failed validation"
                )

        next_step = (
            NextStep(
                goal_id=goal_id,
                text=next_step_text.strip(),
                is_primary=next_step_primary,
            )
            if next_step_text.strip()
            else None
        )
        stored_understanding, stored_next_step, goal = self.repository.commit_semantic_closure(
            goal_id=goal_id,
            understanding=understanding,
            results=claim_results,
            goal_status=goal_status,
            next_step=next_step,
        )
        return LearningSemanticClosureResult(
            goal=goal,
            validation_status=validation_status,
            understanding=stored_understanding,
            claim_results=claim_results,
            next_step=stored_next_step,
        )


def _map_evaluation_result(run: PedagogyEvalRun) -> str:
    if run.final_decision == "accept":
        return "pass"
    if run.final_decision == "needs_semantic_review":
        # Evaluator unavailability/ambiguity is not negative mastery evidence.
        return "partial"
    if run.final_decision != "reject":
        return "partial"

    semantic_misconceptions = (
        tuple(run.semantic_result.misconceptions) if run.semantic_result is not None else ()
    )
    deterministic_misconceptions = run.deterministic_result.get("misconceptions", ())
    if semantic_misconceptions or bool(deterministic_misconceptions):
        return "fail"
    return "partial"
