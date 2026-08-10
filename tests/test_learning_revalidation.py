from __future__ import annotations

import pytest

from src.application.learning_outcome_commit import LearningOutcomeCommitService
from src.application.learning_revalidation import LearningRevalidationService
from src.application.learning_source_evidence import (
    EvidenceConvergenceResult,
)
from src.domain.learning_truth import (
    EvidenceBinding,
    LearningGoal,
    LearningTopic,
    SourceEvidence,
)
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.learning_truth_repository import LearningTruthRepository
from src.repositories.runtime_repository import RuntimeRepository


def _source(commit: str = "a" * 40) -> SourceEvidence:
    return SourceEvidence(
        repository="2002yy/study-agent",
        commit_sha=commit,
        tree_sha="c" * 40,
        path="src/application/learning_resume.py",
        file_sha=f"file-{commit}",
        symbol="LearningResumeService.build",
        symbol_kind="method",
        start_line=10,
        end_line=10,
        evidence_kind="search_result",
    )


def _convergence(commit: str = "a" * 40) -> EvidenceConvergenceResult:
    return EvidenceConvergenceResult(
        primary=EvidenceBinding(
            source=_source(commit=commit),
            role="primary",
            position=0,
        ),
        candidate_count=1,
    )


def _setup(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    runtime = RuntimeRepository(database)
    thread = runtime.ensure_chat_thread("thread-revalidate")
    truth = LearningTruthRepository(database)
    topic = truth.create_topic(LearningTopic(title="Revalidation"))
    goal, _context = truth.create_goal_for_thread(
        LearningGoal(topic_id=topic.id, objective="Revalidate claims"),
        thread_id=thread.id,
        focus_pinned=True,
    )
    return database, runtime, truth, thread, topic, goal


class FakeSourceEvidence:
    def __init__(self, result: EvidenceConvergenceResult | None = None):
        self.result = result or EvidenceConvergenceResult(
            unresolved_reason="missing_source"
        )
        self.calls: list[tuple[str, str]] = []

    def search_and_converge(self, repo_url: str, query: str):
        self.calls.append((repo_url, query))
        return self.result


class FakeFreshness:
    def __init__(self, status: str = "current"):
        self.status = status

    def evaluate(self, bundle, *, ref: str = ""):
        from src.application.learning_freshness import FreshnessEvaluation

        return FreshnessEvaluation(status=self.status, head_commit="z" * 40)


def test_revalidate_missing_claim_raises(tmp_path):
    _database, _runtime, truth, _thread, _topic, _goal = _setup(tmp_path)
    service = LearningRevalidationService(
        truth,
        source_evidence_service=FakeSourceEvidence(),
        commit_service=LearningOutcomeCommitService(truth),
    )
    with pytest.raises(ValueError, match="claim_not_found"):
        service.revalidate("thread-revalidate", "claim-missing")


def test_revalidate_without_active_goal_raises(tmp_path):
    _database, _runtime, truth, _thread, topic, _goal = _setup(tmp_path)
    outcome = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=_goal.id,
        claim_text="Revalidation targets an existing claim.",
        claim_kind="invariant",
        convergence=_convergence(),
    )
    assert outcome.claim is not None
    service = LearningRevalidationService(
        truth,
        source_evidence_service=FakeSourceEvidence(),
        commit_service=LearningOutcomeCommitService(truth),
    )
    with pytest.raises(ValueError, match="no_active_goal"):
        service.revalidate("thread-without-focus", outcome.claim.id)


def test_revalidate_no_convergence_returns_unresolved(tmp_path):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    outcome = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="This claim will not re-converge.",
        claim_kind="invariant",
        convergence=_convergence(),
    )
    assert outcome.claim is not None
    source_evidence = FakeSourceEvidence(
        EvidenceConvergenceResult(unresolved_reason="ambiguous_owner")
    )
    service = LearningRevalidationService(
        truth,
        source_evidence_service=source_evidence,
        commit_service=LearningOutcomeCommitService(truth),
    )

    result = service.revalidate("thread-revalidate", outcome.claim.id)

    assert result.outcome == "no_convergence"
    assert result.unresolved_reason == "ambiguous_owner"
    assert result.revision_id == ""
    assert source_evidence.calls == [
        ("2002yy/study-agent", "This claim will not re-converge.")
    ]


def test_revalidate_commits_new_revision_on_same_lineage(tmp_path):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    outcome = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="Revalidation reuses the claim lineage.",
        claim_kind="invariant",
        convergence=_convergence(commit="a" * 40),
    )
    assert outcome.claim is not None and outcome.revision is not None
    original_claim_id = outcome.claim.id
    original_revision_id = outcome.revision.revision.id
    service = LearningRevalidationService(
        truth,
        source_evidence_service=FakeSourceEvidence(
            _convergence(commit="b" * 40)
        ),
        commit_service=LearningOutcomeCommitService(truth),
        freshness_service=FakeFreshness(status="current"),
    )

    result = service.revalidate("thread-revalidate", original_claim_id)

    assert result.outcome == "revalidated"
    assert result.claim_id == original_claim_id
    assert result.revision_id != original_revision_id
    assert result.freshness_status == "current"
    bundles = truth.list_revisions(original_claim_id)
    assert len(bundles) == 2
    assert bundles[-1].revision.reason == "revalidated"
    assert bundles[-1].revision.claim_text == "Revalidation reuses the claim lineage."
    assert bundles[-1].evidence[0].source.commit_sha == "b" * 40


def test_revalidate_without_freshness_service_has_empty_status(tmp_path):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    outcome = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="Revalidation without a freshness probe.",
        claim_kind="invariant",
        convergence=_convergence(),
    )
    assert outcome.claim is not None
    service = LearningRevalidationService(
        truth,
        source_evidence_service=FakeSourceEvidence(
            _convergence(commit="b" * 40)
        ),
        commit_service=LearningOutcomeCommitService(truth),
    )

    result = service.revalidate("thread-revalidate", outcome.claim.id)

    assert result.outcome == "revalidated"
    assert result.freshness_status == ""


def test_revalidate_without_primary_evidence_raises(tmp_path, monkeypatch):
    _database, _runtime, truth, _thread, topic, goal = _setup(tmp_path)
    from src.domain.learning_truth import (
        ClaimRevision,
        ClaimRevisionBundle,
        EvidenceBinding,
        LearningClaim,
        SourceEvidence,
    )

    claim = truth.create_claim(
        LearningClaim(topic_id=topic.id, scope="project", claim_kind="mechanism")
    )
    unrepoed = ClaimRevisionBundle(
        revision=ClaimRevision(
            claim_id=claim.id, claim_text="No primary repository."
        ),
        evidence=(
            EvidenceBinding(
                source=SourceEvidence(
                    repository="",
                    commit_sha="a" * 40,
                    tree_sha="c" * 40,
                    path="x.py",
                    file_sha="f",
                    start_line=1,
                    end_line=1,
                ),
                role="primary",
                position=0,
            ),
        ),
    )
    single = lambda claim_id: [unrepoed]  # noqa: E731
    monkeypatch.setattr(truth, "list_revisions", single)
    service = LearningRevalidationService(
        truth,
        source_evidence_service=FakeSourceEvidence(),
        commit_service=LearningOutcomeCommitService(truth),
    )
    with pytest.raises(ValueError, match="claim_has_no_primary_source"):
        service.revalidate("thread-revalidate", claim.id)