from __future__ import annotations

import sqlite3

import pytest

from src.application.learning_outcome_commit import LearningOutcomeCommitService
from src.application.learning_semantic_closure import LearningSemanticClosureService
from src.application.learning_source_evidence import EvidenceConvergenceResult
from src.domain.learning_truth import (
    EvidenceBinding,
    LearningGoal,
    LearningTopic,
    SourceEvidence,
)
from src.infrastructure.sqlite.database import MIGRATIONS, RuntimeDatabase, SCHEMA_VERSION
from src.pedagogy.evaluation import PedagogyEvalRun, SemanticEvaluation
from src.repositories.learning_truth_repository import LearningTruthRepository
from src.repositories.runtime_repository import RuntimeRepository


COMMIT_SHA = "a" * 40
TREE_SHA = "b" * 40


def _build_v17_database(path) -> None:
    with sqlite3.connect(path) as connection:
        for version, sql in MIGRATIONS:
            if version > 17:
                break
            connection.executescript(sql)
            connection.execute(
                "INSERT OR REPLACE INTO runtime_meta(key, value) VALUES('schema_version', ?)",
                (str(version),),
            )
        connection.commit()


def _source() -> SourceEvidence:
    return SourceEvidence(
        repository="2002yy/study-agent",
        commit_sha=COMMIT_SHA,
        tree_sha=TREE_SHA,
        path="src/application/learning_semantic_closure.py",
        file_sha="file-sha",
        symbol="LearningSemanticClosureService.close",
        symbol_kind="method",
        start_line=40,
        end_line=40,
        evidence_kind="search_result",
    )


def _convergence() -> EvidenceConvergenceResult:
    return EvidenceConvergenceResult(
        primary=EvidenceBinding(source=_source(), role="primary", position=0),
        candidate_count=1,
    )


def _evaluation(
    *,
    decision: str,
    learner_input: str = "因为证据身份固定到 commit，所以 CI 暂不可用不会改写源码事实。",
    misconceptions: tuple[str, ...] = (),
) -> PedagogyEvalRun:
    semantic = (
        SemanticEvaluation(
            claims=("source identity",),
            correct_points=("commit pinned",) if decision == "accept" else (),
            misconceptions=misconceptions,
            reasoning_complete=decision == "accept",
            transfer_ready=decision == "accept",
            confidence=0.92,
            evidence_refs=("source-primary",),
        )
        if decision != "needs_semantic_review"
        else None
    )
    return PedagogyEvalRun(
        id=f"eval-{decision}",
        learner_input=learner_input,
        objective="Understand source evidence identity",
        protocol="guided",
        expected_concepts=("commit pinning",),
        evidence=("source-primary",),
        deterministic_result={
            "passed": decision == "accept",
            "is_claim": True,
            "reason": "reasoned_claim",
            "misconceptions": list(misconceptions),
        },
        semantic_result=semantic,
        confidence=0.92 if decision == "accept" else 0.0,
        final_decision=decision,
        reasons=(decision,),
    )


def _setup(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    runtime = RuntimeRepository(database)
    thread = runtime.ensure_chat_thread("thread-learning")
    truth = LearningTruthRepository(database)
    topic = truth.create_topic(LearningTopic(title="Durable learning"))
    goal, context = truth.create_goal_for_thread(
        LearningGoal(topic_id=topic.id, objective="Understand source evidence identity"),
        thread_id=thread.id,
        focus_pinned=True,
    )
    outcome = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="CI observation is separate from SourceEvidence identity.",
        claim_kind="invariant",
        convergence=_convergence(),
    )
    assert outcome.revision is not None
    return database, truth, topic, goal, context, outcome.revision.revision


def test_v17_to_v18_adds_navigation_relations_without_synthesizing_truth(tmp_path):
    db_path = tmp_path / "runtime.db"
    _build_v17_database(db_path)
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT INTO chat_threads(
                id, status, settings_snapshot, created_at, updated_at, version,
                learning_state
            ) VALUES ('thread-old', 'active', '{}', 'now', 'now', 1, '{}')
            """
        )
        connection.execute(
            """
            INSERT INTO learning_topics(id, title, scope, created_at, updated_at)
            VALUES ('topic-old', 'Old', 'project', 'now', 'now')
            """
        )
        connection.execute(
            """
            INSERT INTO learning_goals(id, topic_id, objective, status, created_at, updated_at)
            VALUES ('goal-old', 'topic-old', 'Old goal', 'active', 'now', 'now')
            """
        )
        connection.commit()

    RuntimeDatabase(db_path).initialize()

    with sqlite3.connect(db_path) as connection:
        version = connection.execute(
            "SELECT value FROM runtime_meta WHERE key = 'schema_version'"
        ).fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        context_count = connection.execute(
            "SELECT COUNT(*) FROM learning_goal_contexts"
        ).fetchone()[0]
        relation_count = connection.execute(
            "SELECT COUNT(*) FROM learning_goal_claim_revisions"
        ).fetchone()[0]

    assert version == str(SCHEMA_VERSION) == "19"
    assert "learning_goal_contexts" in tables
    assert "learning_goal_claim_revisions" in tables
    assert context_count == 0
    assert relation_count == 0


def test_goal_focus_prefers_pinned_then_recent_and_terminal_goal_unpins(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    runtime = RuntimeRepository(database)
    thread = runtime.ensure_chat_thread("thread-focus")
    truth = LearningTruthRepository(database)
    topic = truth.create_topic(LearningTopic(title="Focus"))
    first, _ = truth.create_goal_for_thread(
        LearningGoal(topic_id=topic.id, objective="First"),
        thread_id=thread.id,
        focus_pinned=True,
    )
    second, _ = truth.create_goal_for_thread(
        LearningGoal(topic_id=topic.id, objective="Second"),
        thread_id=thread.id,
        focus_pinned=False,
    )

    assert truth.get_focus_goal(thread.id) == first

    second_context = truth.focus_goal(second.id, pinned=True)
    assert second_context.focus_pinned is True
    assert truth.get_goal_context(first.id) is not None
    assert truth.get_goal_context(first.id).focus_pinned is False  # type: ignore[union-attr]
    assert truth.get_focus_goal(thread.id) == second

    truth.update_goal_status(second.id, "completed")
    assert truth.get_goal_context(second.id) is not None
    assert truth.get_goal_context(second.id).focus_pinned is False  # type: ignore[union-attr]
    assert truth.get_focus_goal(thread.id) == first


def test_outcome_commit_atomically_links_revision_to_goal(tmp_path):
    _database, truth, _topic, goal, _context, revision = _setup(tmp_path)

    revisions = truth.list_goal_revisions(goal.id)

    assert [item.revision.id for item in revisions] == [revision.id]
    assert revisions[0].evidence[0].role == "primary"


def test_accept_validation_persists_raw_understanding_and_completes_goal(tmp_path):
    database, truth, _topic, goal, _context, revision = _setup(tmp_path)
    service = LearningSemanticClosureService(truth)
    evaluation = _evaluation(decision="accept")

    result = service.close(
        goal_id=goal.id,
        target_revision_ids=(revision.id,),
        method="apply",
        prompt="If CI is unavailable, does SourceEvidence become invalid? Why?",
        evaluation_run=evaluation,
        goal_status="completed",
    )

    assert result.validation_status == "pass"
    assert result.goal.status == "completed"
    assert result.understanding is not None
    assert result.understanding.user_response == evaluation.learner_input
    assert result.claim_results[0].result == "pass"
    stored = truth.get_understanding_evidence(result.understanding.id)
    assert stored is not None
    assert stored[0] == result.understanding
    assert stored[1] == result.claim_results
    assert truth.get_goal_context(goal.id) is not None
    assert truth.get_goal_context(goal.id).focus_pinned is False  # type: ignore[union-attr]

    with database.connect() as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(understanding_evidence)")
        }
    assert "confidence" not in columns
    assert "reasoning" not in columns


def test_semantic_evaluator_unavailable_is_partial_not_failure(tmp_path):
    _database, truth, _topic, goal, _context, revision = _setup(tmp_path)
    service = LearningSemanticClosureService(truth)

    with pytest.raises(ValueError, match="cannot complete"):
        service.close(
            goal_id=goal.id,
            target_revision_ids=(revision.id,),
            prompt="Explain why the source remains valid.",
            evaluation_run=_evaluation(decision="needs_semantic_review"),
            goal_status="completed",
        )

    result = service.close(
        goal_id=goal.id,
        target_revision_ids=(revision.id,),
        prompt="Explain why the source remains valid.",
        evaluation_run=_evaluation(decision="needs_semantic_review"),
        goal_status="active",
        next_step_text="Retry the understanding check when semantic review is available",
    )

    assert result.validation_status == "partial"
    assert result.claim_results[0].result == "partial"
    assert result.goal.status == "active"
    assert result.next_step is not None
    assert result.next_step.is_primary is True


def test_explicit_misconception_maps_to_fail_without_false_completion(tmp_path):
    _database, truth, _topic, goal, _context, revision = _setup(tmp_path)
    service = LearningSemanticClosureService(truth)

    result = service.close(
        goal_id=goal.id,
        target_revision_ids=(revision.id,),
        method="explain",
        prompt="Explain the source/CI relationship.",
        evaluation_run=_evaluation(
            decision="reject",
            misconceptions=("ci_failure_invalidates_source",),
        ),
        goal_status="blocked",
        next_step_text="Revisit SourceEvidence identity before revalidation",
    )

    assert result.validation_status == "fail"
    assert result.claim_results[0].result == "fail"
    assert result.goal.status == "blocked"
    assert result.next_step is not None


def test_user_can_explicitly_skip_validation_without_fabricating_understanding(tmp_path):
    database, truth, _topic, goal, _context, revision = _setup(tmp_path)
    service = LearningSemanticClosureService(truth)

    result = service.close(
        goal_id=goal.id,
        target_revision_ids=(revision.id,),
        goal_status="completed",
        skip_validation=True,
    )

    assert result.validation_status == "skipped"
    assert result.goal.status == "completed"
    assert result.understanding is None
    assert result.claim_results == ()
    assert truth.list_understanding_for_revision(revision.id) == []
    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM understanding_evidence"
        ).fetchone()[0] == 0


def test_semantic_closure_rejects_cross_goal_revision_and_rolls_back_all_state(tmp_path):
    database, truth, topic, goal, _context, _revision = _setup(tmp_path)
    other = truth.create_goal(LearningGoal(topic_id=topic.id, objective="Other goal"))
    other_outcome = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=other.id,
        claim_text="Another source-backed fact.",
        claim_kind="mechanism",
        convergence=_convergence(),
    )
    assert other_outcome.revision is not None
    foreign_revision_id = other_outcome.revision.revision.id
    service = LearningSemanticClosureService(truth)

    with pytest.raises(ValueError, match="linked to its Goal"):
        service.close(
            goal_id=goal.id,
            target_revision_ids=(foreign_revision_id,),
            prompt="Explain the other fact.",
            evaluation_run=_evaluation(decision="accept"),
            goal_status="completed",
        )

    assert truth.get_goal(goal.id) is not None
    assert truth.get_goal(goal.id).status == "active"  # type: ignore[union-attr]
    assert truth.list_understanding_for_revision(foreign_revision_id) == []
    assert truth.list_next_steps_for_goal(goal.id) == []
    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM understanding_evidence"
        ).fetchone()[0] == 0
