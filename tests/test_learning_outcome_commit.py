from __future__ import annotations

import sqlite3

import pytest

from src.application.learning_outcome_commit import LearningOutcomeCommitService
from src.application.learning_source_evidence import EvidenceConvergenceResult
from src.domain.learning_truth import (
    EvidenceBinding,
    LearningClaim,
    LearningGoal,
    LearningTopic,
    SourceEvidence,
)
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.learning_truth_repository import LearningTruthRepository


COMMIT_SHA = "a" * 40
TREE_SHA = "b" * 40


def _source(
    *,
    source_id: str,
    path: str,
    symbol: str,
    line: int,
    commit_sha: str = COMMIT_SHA,
) -> SourceEvidence:
    return SourceEvidence(
        id=source_id,
        repository="2002yy/study-agent",
        commit_sha=commit_sha,
        tree_sha=TREE_SHA,
        path=path,
        file_sha=f"sha:{path}",
        symbol=symbol,
        symbol_kind="method",
        start_line=line,
        end_line=line,
        evidence_kind="search_result",
    )


def _ready_convergence(*, collision: bool = False) -> EvidenceConvergenceResult:
    primary = _source(
        source_id="same-id" if collision else "primary",
        path="src/service.py",
        symbol="Service.run",
        line=10,
    )
    support = _source(
        source_id="same-id" if collision else "support",
        path="tests/test_service.py",
        symbol="test_run",
        line=20,
    )
    return EvidenceConvergenceResult(
        primary=EvidenceBinding(source=primary, role="primary", position=0),
        supporting=(
            EvidenceBinding(
                source=support,
                role="supporting_corroborating",
                position=1,
            ),
        ),
        candidate_count=2,
    )


def _setup(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    repository = LearningTruthRepository(database)
    topic = repository.create_topic(LearningTopic(title="Source evidence"))
    goal = repository.create_goal(
        LearningGoal(topic_id=topic.id, objective="Understand source identity")
    )
    return database, repository, topic, goal, LearningOutcomeCommitService(repository)


def test_no_primary_creates_hypothesis_and_zero_claim_rows(tmp_path):
    database, repository, topic, goal, service = _setup(tmp_path)

    result = service.commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="The alternate path probably preserves source identity.",
        claim_kind="mechanism",
        convergence=EvidenceConvergenceResult(unresolved_reason="missing_source"),
    )

    assert result.outcome == "hypothesis"
    assert result.claim is None
    assert result.revision is None
    assert result.hypothesis is not None
    assert result.hypothesis.unresolved_reason == "missing_source"
    assert repository.get_hypothesis(result.hypothesis.id) == result.hypothesis
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM learning_claims").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM claim_revisions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM source_evidence").fetchone()[0] == 0


def test_new_supported_claim_commits_claim_revision_and_evidence_atomically(tmp_path):
    _database, repository, topic, goal, service = _setup(tmp_path)

    result = service.commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="Source evidence is pinned to an exact repository state.",
        claim_kind="invariant",
        convergence=_ready_convergence(),
    )

    assert result.outcome == "claim"
    assert result.claim is not None
    assert result.revision is not None
    assert result.hypothesis is None
    assert result.revision.revision.claim_id == result.claim.id
    assert result.revision.revision.reason == "initial"
    assert result.revision.revision.source_commit == COMMIT_SHA
    assert [item.role for item in result.revision.evidence] == [
        "primary",
        "supporting_corroborating",
    ]
    assert repository.get_claim(result.claim.id) == result.claim
    assert repository.get_revision(result.revision.revision.id) == result.revision


def test_new_claim_failure_leaves_no_claim_shell_or_source_rows(tmp_path):
    database, _repository, topic, goal, service = _setup(tmp_path)

    with pytest.raises(sqlite3.IntegrityError):
        service.commit(
            topic_id=topic.id,
            goal_id=goal.id,
            claim_text="This commit must fail as one transaction.",
            claim_kind="invariant",
            convergence=_ready_convergence(collision=True),
        )

    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM learning_claims").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM claim_revisions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM source_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM claim_revision_evidence").fetchone()[0] == 0


def test_existing_claim_reuse_is_explicit_and_creates_same_lineage_revision(tmp_path):
    _database, repository, topic, goal, service = _setup(tmp_path)
    first = service.commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="Source evidence identity is commit pinned.",
        claim_kind="invariant",
        convergence=_ready_convergence(),
    )
    assert first.claim is not None

    second = service.commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="Source evidence identity remains commit pinned after revalidation.",
        claim_kind="invariant",
        convergence=EvidenceConvergenceResult(
            primary=EvidenceBinding(
                source=_source(
                    source_id="primary-v2",
                    path="src/service.py",
                    symbol="Service.run",
                    line=11,
                    commit_sha="c" * 40,
                ),
                role="primary",
                position=0,
            ),
            candidate_count=1,
        ),
        existing_claim_id=first.claim.id,
        revision_reason="revalidated",
    )

    assert second.claim == first.claim
    assert second.revision is not None
    assert second.revision.revision.claim_id == first.claim.id
    assert second.revision.revision.reason == "revalidated"
    assert second.revision.revision.source_commit == "c" * 40
    assert len(repository.list_claims(topic.id)) == 1
    revisions = repository.list_revisions(first.claim.id)
    assert len(revisions) == 2
    assert [item.revision.reason for item in revisions] == ["initial", "revalidated"]


def test_without_existing_claim_id_same_text_does_not_auto_merge(tmp_path):
    _database, repository, topic, goal, service = _setup(tmp_path)

    first = service.commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="A stable assertion.",
        claim_kind="boundary",
        convergence=_ready_convergence(),
    )
    second = service.commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="A stable assertion.",
        claim_kind="boundary",
        convergence=_ready_convergence(),
    )

    assert first.claim is not None and second.claim is not None
    assert first.claim.id != second.claim.id
    assert len(repository.list_claims(topic.id)) == 2


def test_existing_claim_requires_matching_topic_scope_kind_and_explicit_reason(tmp_path):
    _database, repository, topic, goal, service = _setup(tmp_path)
    existing = repository.create_claim(
        LearningClaim(topic_id=topic.id, scope="project", claim_kind="mechanism")
    )

    with pytest.raises(ValueError, match="explicit"):
        service.commit(
            topic_id=topic.id,
            goal_id=goal.id,
            claim_text="A revised mechanism.",
            claim_kind="mechanism",
            convergence=_ready_convergence(),
            existing_claim_id=existing.id,
        )

    with pytest.raises(ValueError, match="scope"):
        service.commit(
            topic_id=topic.id,
            goal_id=goal.id,
            claim_text="A revised mechanism.",
            claim_kind="mechanism",
            convergence=_ready_convergence(),
            scope="general",
            existing_claim_id=existing.id,
            revision_reason="meaning_changed",
        )

    with pytest.raises(ValueError, match="kind"):
        service.commit(
            topic_id=topic.id,
            goal_id=goal.id,
            claim_text="A revised boundary.",
            claim_kind="boundary",
            convergence=_ready_convergence(),
            existing_claim_id=existing.id,
            revision_reason="meaning_changed",
        )


def test_transient_or_unrecognized_claim_kind_is_rejected(tmp_path):
    _database, _repository, topic, goal, service = _setup(tmp_path)

    with pytest.raises(ValueError, match="claim kind"):
        service.commit(
            topic_id=topic.id,
            goal_id=goal.id,
            claim_text="Search returned twelve results.",
            claim_kind="retrieval_detail",
            convergence=_ready_convergence(),
        )


def test_hypothesis_reason_is_bounded_and_existing_claim_never_falls_back(tmp_path):
    _database, repository, topic, goal, service = _setup(tmp_path)
    existing = repository.create_claim(
        LearningClaim(topic_id=topic.id, scope="project", claim_kind="mechanism")
    )

    unknown = service.commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="Unresolved assertion.",
        claim_kind="mechanism",
        convergence=EvidenceConvergenceResult(unresolved_reason="unexpected_internal_state"),
    )
    assert unknown.hypothesis is not None
    assert unknown.hypothesis.unresolved_reason == "insufficient_evidence"

    with pytest.raises(ValueError, match="without Primary"):
        service.commit(
            topic_id=topic.id,
            goal_id=goal.id,
            claim_text="Existing Claim cannot be revised without source evidence.",
            claim_kind="mechanism",
            convergence=EvidenceConvergenceResult(unresolved_reason="provider_unavailable"),
            existing_claim_id=existing.id,
            revision_reason="revalidated",
        )
