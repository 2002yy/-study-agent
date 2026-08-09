from __future__ import annotations

from src.application.learning_closure_truth import LearningClosureTruthService
from src.domain.learning_closure import LearningClosureRun
from src.domain.learning_truth import LearningGoal, LearningTopic
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.learning_truth_repository import LearningTruthRepository
from src.repositories.runtime_repository import RuntimeRepository


class UnusedSourceEvidenceService:
    pass


class UnusedEvaluationRepository:
    pass


def _run(run_id: str = "closure-new") -> LearningClosureRun:
    return LearningClosureRun(
        id=run_id,
        thread_id="thread-1",
        source_thread_version=1,
        last_completed_turn_id="turn-1",
        source_hash=f"hash-{run_id}",
        closure_eligibility="learning_summary",
    )


def test_same_objective_reuses_goal_but_new_objective_gets_new_focus(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    RuntimeRepository(database).ensure_chat_thread("thread-1")
    truth = LearningTruthRepository(database)
    topic = truth.create_topic(
        LearningTopic(id="topic-old", title="Study Agent session recovery", scope="project")
    )
    old_goal, _context = truth.create_goal_for_thread(
        LearningGoal(
            id="goal-old",
            topic_id=topic.id,
            objective="理解 durable resume",
            status="active",
        ),
        thread_id="thread-1",
    )
    service = LearningClosureTruthService(
        truth,
        UnusedSourceEvidenceService(),  # type: ignore[arg-type]
        UnusedEvaluationRepository(),  # type: ignore[arg-type]
    )

    reused_topic, reused_goal = service._focus_or_create_goal(
        _run("closure-same"),
        objective="  理解   DURABLE resume  ",
        repo_url="https://github.com/2002yy/study-agent",
    )

    assert reused_topic.id == topic.id
    assert reused_goal.id == old_goal.id
    assert truth.get_focus_goal("thread-1").id == old_goal.id  # type: ignore[union-attr]

    new_topic, new_goal = service._focus_or_create_goal(
        _run("closure-new"),
        objective="理解 SourceEvidence freshness",
        repo_url="https://github.com/2002yy/study-agent",
    )

    assert new_topic.id == topic.id
    assert new_goal.id != old_goal.id
    assert new_goal.objective == "理解 SourceEvidence freshness"
    assert truth.get_focus_goal("thread-1").id == new_goal.id  # type: ignore[union-attr]
    stored_old = truth.get_goal(old_goal.id)
    assert stored_old is not None
    assert stored_old.status == "active"
    assert {goal.id for goal in truth.list_goals_for_thread("thread-1")} == {
        old_goal.id,
        new_goal.id,
    }
