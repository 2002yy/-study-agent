"""Explicit production bridge from completed ChatTurns to durable learning truth.

The browser supplies intent (which turn, which short assertion, which validation
turn), never SourceEvidence identity or pass/fail decisions. Trusted evidence and
PedagogyEvalRun state are reloaded from SQLite on the server.
"""

from __future__ import annotations

from typing import Any, Sequence

from src.application.learning_outcome_commit import LearningOutcomeCommitService
from src.application.learning_resume import LearningResumeService
from src.application.learning_semantic_closure import LearningSemanticClosureService
from src.application.learning_source_evidence import LearningSourceEvidenceService
from src.domain.learning_truth import LearningGoal, LearningTopic
from src.repositories.learning_truth_repository import LearningTruthRepository
from src.repositories.pedagogy_eval_repository import PedagogyEvalRepository
from src.repositories.runtime_repository import RuntimeRepository


class LearningTurnBridgeService:
    """Safe explicit write boundary used by the minimal P2-D learning UI."""

    def __init__(
        self,
        runtime_repository: RuntimeRepository,
        truth_repository: LearningTruthRepository,
        evaluation_repository: PedagogyEvalRepository,
        source_service: LearningSourceEvidenceService,
        outcome_service: LearningOutcomeCommitService,
        semantic_closure_service: LearningSemanticClosureService,
        resume_service: LearningResumeService,
    ) -> None:
        self.runtime_repository = runtime_repository
        self.truth_repository = truth_repository
        self.evaluation_repository = evaluation_repository
        self.source_service = source_service
        self.outcome_service = outcome_service
        self.semantic_closure_service = semantic_closure_service
        self.resume_service = resume_service

    def commit_turn_assertion(
        self,
        *,
        thread_id: str,
        turn_id: str,
        claim_text: str,
        claim_kind: str,
        scope: str = "project",
        topic_id: str | None = None,
        topic_title: str = "",
        goal_id: str | None = None,
        goal_objective: str = "",
    ) -> dict[str, Any]:
        turn = self._require_completed_turn(thread_id, turn_id)
        goal = self._resolve_goal(
            thread_id=thread_id,
            claim_text=claim_text,
            topic_id=topic_id,
            topic_title=topic_title,
            goal_id=goal_id,
            goal_objective=goal_objective,
            scope=scope,
        )
        trace = turn.rag_snapshot.get("web_tools")
        convergence = self.source_service.converge_persisted_tool_trace(trace)
        outcome = self.outcome_service.commit(
            topic_id=goal.topic_id,
            goal_id=goal.id,
            claim_text=claim_text,
            claim_kind=claim_kind,
            convergence=convergence,
            scope=scope,
        )
        return {
            "outcome": outcome.outcome,
            "goal_id": goal.id,
            "claim_id": outcome.claim.id if outcome.claim is not None else "",
            "revision_id": (
                outcome.revision.revision.id if outcome.revision is not None else ""
            ),
            "hypothesis_id": (
                outcome.hypothesis.id if outcome.hypothesis is not None else ""
            ),
            "unresolved_reason": (
                outcome.hypothesis.unresolved_reason
                if outcome.hypothesis is not None
                else ""
            ),
            "resume": self.resume_service.build(thread_id),
        }

    def validate_with_turn(
        self,
        *,
        thread_id: str,
        goal_id: str,
        revision_ids: Sequence[str],
        turn_id: str | None = None,
        method: str = "explain",
        complete_goal: bool = False,
        skip_validation: bool = False,
        next_step_text: str = "",
    ) -> dict[str, Any]:
        self._require_goal_context(thread_id, goal_id)
        evaluation = None
        prompt = ""
        if skip_validation:
            if not complete_goal:
                raise ValueError("Skipping validation is only meaningful when explicitly completing the Goal")
            if turn_id:
                raise ValueError("Skipped validation must not attach a validation turn")
        else:
            if not turn_id:
                raise ValueError("Validation turn id is required")
            turn = self._require_completed_turn(thread_id, turn_id)
            evaluation = self.evaluation_repository.get_by_turn(turn.id)
            if evaluation is None:
                raise ValueError(f"Pedagogy evaluation not found for turn: {turn.id}")
            objective = str(evaluation.objective or "").strip()
            prompt = f"理解验证：{objective}" if objective else "本轮理解验证"

        result = self.semantic_closure_service.close(
            goal_id=goal_id,
            target_revision_ids=tuple(dict.fromkeys(str(item) for item in revision_ids if str(item))),
            method=method,
            prompt=prompt,
            evaluation_run=evaluation,
            goal_status="completed" if complete_goal else "active",
            next_step_text=next_step_text,
            skip_validation=skip_validation,
        )
        return {
            "goal_id": result.goal.id,
            "goal_status": result.goal.status,
            "validation_status": result.validation_status,
            "understanding_id": (
                result.understanding.id if result.understanding is not None else ""
            ),
            "next_step_id": result.next_step.id if result.next_step is not None else "",
            "resume": self.resume_service.build(thread_id),
        }

    def _resolve_goal(
        self,
        *,
        thread_id: str,
        claim_text: str,
        topic_id: str | None,
        topic_title: str,
        goal_id: str | None,
        goal_objective: str,
        scope: str,
    ) -> LearningGoal:
        if goal_id:
            context = self._require_goal_context(thread_id, goal_id)
            goal = self.truth_repository.get_goal(context.goal_id)
            if goal is None:
                raise ValueError(f"Learning Goal not found: {goal_id}")
            return goal

        focused = self.truth_repository.get_focus_goal(thread_id)
        if focused is not None:
            return focused

        if topic_id:
            topic = self.truth_repository.get_topic(topic_id)
            if topic is None:
                raise ValueError(f"Learning Topic not found: {topic_id}")
            if topic.scope != scope:
                raise ValueError("Learning Topic scope does not match requested scope")
        else:
            topic = self.truth_repository.create_topic(
                LearningTopic(
                    title=topic_title.strip() or "源码学习",
                    scope=scope,
                )
            )
        objective = goal_objective.strip() or claim_text.strip()
        if not objective:
            raise ValueError("Learning Goal objective is required")
        goal, _context = self.truth_repository.create_goal_for_thread(
            LearningGoal(topic_id=topic.id, objective=objective),
            thread_id=thread_id,
        )
        return goal

    def _require_goal_context(self, thread_id: str, goal_id: str):
        context = self.truth_repository.get_goal_context(goal_id)
        if context is None:
            raise ValueError(f"Learning Goal has no thread context: {goal_id}")
        if context.thread_id != thread_id:
            raise ValueError("Learning Goal belongs to another session")
        return context

    def _require_completed_turn(self, thread_id: str, turn_id: str):
        turn = self.runtime_repository.get_chat_turn(turn_id)
        if turn is None:
            raise ValueError(f"Chat turn not found: {turn_id}")
        if turn.thread_id != thread_id:
            raise ValueError("Chat turn belongs to another session")
        if turn.status != "completed":
            raise ValueError("Only completed ChatTurns can commit learning truth")
        return turn
