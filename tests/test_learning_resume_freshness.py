from __future__ import annotations

from src.application.learning_freshness import FreshnessEvaluation
from src.application.learning_outcome_commit import LearningOutcomeCommitService
from src.application.learning_resume import LearningResumeService
from src.application.learning_source_evidence import EvidenceConvergenceResult
from src.domain.learning_truth import (
    EvidenceBinding,
    LearningGoal,
    LearningTopic,
    SourceEvidence,
)
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.learning_truth_repository import LearningTruthRepository
from src.repositories.runtime_repository import RuntimeRepository


def _source() -> SourceEvidence:
    return SourceEvidence(
        repository="2002yy/study-agent",
        commit_sha="a" * 40,
        tree_sha="c" * 40,
        path="src/application/learning_resume.py",
        file_sha="file-a",
        symbol="LearningResumeService.build",
        symbol_kind="method",
        start_line=10,
        end_line=10,
        evidence_kind="search_result",
    )


def _convergence() -> EvidenceConvergenceResult:
    return EvidenceConvergenceResult(
        primary=EvidenceBinding(
            source=_source(),
            role="primary",
            position=0,
        ),
        candidate_count=1,
    )


def _setup(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    runtime = RuntimeRepository(database)
    thread = runtime.ensure_chat_thread("thread-resume-fresh")
    truth = LearningTruthRepository(database)
    topic = truth.create_topic(LearningTopic(title="Durable resume freshness"))
    goal, _context = truth.create_goal_for_thread(
        LearningGoal(topic_id=topic.id, objective="Resume with freshness"),
        thread_id=thread.id,
        focus_pinned=True,
    )
    return database, runtime, truth, thread, topic, goal


def _commit_claim(truth, topic, goal, text: str):
    outcome = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text=text,
        claim_kind="invariant",
        convergence=_convergence(),
    )
    assert outcome.claim is not None and outcome.revision is not None
    return outcome.revision


class RecordingEvaluator:
    def __init__(self):
        self.calls: list = []
        self.results: dict[str, FreshnessEvaluation] = {}

    def evaluate(self, bundle, *, ref: str = ""):
        self.calls.append(bundle.revision.claim_id)
        return self.results.get(
            bundle.revision.claim_id,
            FreshnessEvaluation(status="current", head_commit="h" * 40),
        )


class ThrowingEvaluator:
    def evaluate(self, bundle, *, ref: str = ""):
        raise RuntimeError("provider exploded")


def test_resume_includes_freshness_when_evaluator_wired(tmp_path):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    bundle = _commit_claim(truth, topic, goal, "Freshness rides the resume projection.")
    evaluator = RecordingEvaluator()
    evaluator.results[bundle.revision.claim_id] = FreshnessEvaluation(
        status="stale_candidate",
        head_commit="h" * 40,
        primary={
            "path": "src/application/learning_resume.py",
            "symbol": "LearningResumeService.build",
            "reason": "normalized_body_changed",
            "head_file_sha": "head-blob-sha",
        },
        supporting_drift=(
            {
                "role": "supporting_corroborating",
                "path": "other.py",
                "reason": "normalized_body_changed",
                "materially_changed": True,
            },
        ),
    )

    resume = LearningResumeService(truth, freshness_evaluator=evaluator).build(
        "thread-resume-fresh"
    )

    assert evaluator.calls == [bundle.revision.claim_id]
    assert resume["claims"][0]["freshness"] == {
        "status": "stale_candidate",
        "head_commit": "h" * 40,
        "reason": "normalized_body_changed",
        "primary": {
            "path": "src/application/learning_resume.py",
            "symbol": "LearningResumeService.build",
            "reason": "normalized_body_changed",
            "head_file_sha": "head-blob-sha",
        },
        "supporting_drift": (
            {
                "role": "supporting_corroborating",
                "path": "other.py",
                "reason": "normalized_body_changed",
                "materially_changed": True,
            },
        ),
        "unavailable_reason": "",
    }


def test_resume_omits_freshness_when_evaluator_not_wired(tmp_path):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    _commit_claim(truth, topic, goal, "No freshness without an evaluator.")

    resume = LearningResumeService(truth).build("thread-resume-fresh")

    assert "freshness" not in resume["claims"][0]


def test_resume_freshness_failure_is_unavailable_not_fatal(tmp_path):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    _commit_claim(truth, topic, goal, "Freshness provider failure must not break resume.")

    resume = LearningResumeService(truth, freshness_evaluator=ThrowingEvaluator()).build(
        "thread-resume-fresh"
    )

    assert resume["status"] == "active"
    assert resume["claims"][0]["freshness"]["status"] == "unavailable"
    assert "RuntimeError" in resume["claims"][0]["freshness"]["unavailable_reason"]


def test_resume_freshness_supports_unavailable_evaluation(tmp_path):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    bundle = _commit_claim(truth, topic, goal, "Unavailable evaluation surfaces as is.")
    evaluator = RecordingEvaluator()
    evaluator.results[bundle.revision.claim_id] = FreshnessEvaluation(
        status="unavailable",
        unavailable_reason="head_resolution_failed",
        head_commit="h" * 40,
        primary={
            "path": "src/application/learning_resume.py",
            "reason": "blob_read_failed",
            "error": "blob_read_failed: ValueError: boom",
        },
    )

    resume = LearningResumeService(truth, freshness_evaluator=evaluator).build(
        "thread-resume-fresh"
    )

    freshness = resume["claims"][0]["freshness"]
    assert freshness["status"] == "unavailable"
    assert freshness["unavailable_reason"] == "head_resolution_failed"
    assert freshness["primary"]["reason"] == "blob_read_failed"
    assert (
        "error" in freshness["primary"]
        and "boom" in freshness["primary"]["error"]
    )


def test_resume_freshness_legacy_fallback_has_no_claims(tmp_path):
    _database, _runtime, truth, _thread, topic, _goal = _setup(tmp_path)
    evaluator = RecordingEvaluator()

    resume = LearningResumeService(truth, freshness_evaluator=evaluator).build(
        "thread-never-durable"
    )

    assert resume["source"] == "legacy_fallback"
    assert evaluator.calls == []