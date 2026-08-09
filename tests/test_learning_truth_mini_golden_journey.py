from __future__ import annotations

from pathlib import Path

from src.application.github_snapshot_service import GitHubSnapshotService
from src.application.learning_outcome_commit import LearningOutcomeCommitService
from src.application.learning_source_evidence import LearningSourceEvidenceService
from src.domain.learning_truth import LearningGoal, LearningTopic
from src.infrastructure.sqlite.database import RuntimeDatabase
from src.repositories.github_snapshot_repository import GitHubSnapshotRepository
from src.repositories.learning_truth_repository import LearningTruthRepository
from src.repositories.rag_repository import RagRepository


REPOSITORY = "2002yy/study-agent"
REPO_URL = "https://github.com/2002yy/study-agent"
COMMIT_SHA = "a" * 40
TREE_SHA = "b" * 40
SOURCE_PATH = "src/application/github_source_evidence.py"


class RealStudyAgentSourceSnapshotter:
    """Use checked-out Study Agent source with deterministic pinned metadata."""

    def snapshot(self, repo_url: str, *, query: str = "", ref: str = "") -> dict:
        source_file = Path(__file__).resolve().parents[1] / SOURCE_PATH
        content = source_file.read_text(encoding="utf-8")
        return {
            "ok": True,
            "repository": REPOSITORY,
            "ref": ref or "main",
            "requested_ref": ref or "main",
            "commit_sha": COMMIT_SHA,
            "tree_sha": TREE_SHA,
            "files": [
                {
                    "path": SOURCE_PATH,
                    "sha": "source-file-sha",
                    "url": f"{REPO_URL}/blob/{COMMIT_SHA}/{SOURCE_PATH}",
                    "content": content,
                }
            ],
            "file_count": 1,
            "used_chars": len(content),
        }


class ProviderUnavailableSnapshotter:
    def snapshot(self, repo_url: str, *, query: str = "", ref: str = "") -> dict:
        return {
            "ok": False,
            "repository": REPOSITORY,
            "ref": ref or "main",
            "requested_ref": ref or "main",
            "error": "provider_unavailable",
        }


def _snapshot_service(database: RuntimeDatabase, snapshotter: object) -> GitHubSnapshotService:
    return GitHubSnapshotService(
        GitHubSnapshotRepository(RagRepository(database)),
        snapshotter,  # type: ignore[arg-type]
    )


def test_real_study_agent_source_to_durable_claim_survives_repository_restart(tmp_path):
    database = RuntimeDatabase(tmp_path / "runtime.db")
    truth = LearningTruthRepository(database)
    topic = truth.create_topic(LearningTopic(title="Source evidence"))
    goal = truth.create_goal(
        LearningGoal(
            topic_id=topic.id,
            objective="Understand how commit CI is kept separate from source evidence",
        )
    )

    source_learning = LearningSourceEvidenceService(
        _snapshot_service(database, RealStudyAgentSourceSnapshotter())
    )
    convergence = source_learning.search_and_converge(
        REPO_URL,
        "summarize commit ci",
        ref="main",
    )

    assert convergence.claim_ready is True
    assert convergence.primary is not None
    assert convergence.primary.source.repository == REPOSITORY
    assert convergence.primary.source.commit_sha == COMMIT_SHA
    assert convergence.primary.source.tree_sha == TREE_SHA
    assert convergence.primary.source.path == SOURCE_PATH
    assert convergence.primary.source.symbol == "summarize_commit_ci"
    assert convergence.one_hop_explored is False

    committed = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="CI validation is supporting observation, not SourceEvidence identity.",
        claim_kind="invariant",
        convergence=convergence,
    )

    assert committed.outcome == "claim"
    assert committed.claim is not None
    assert committed.revision is not None
    assert committed.hypothesis is None
    assert committed.revision.revision.source_commit == COMMIT_SHA

    restarted = LearningTruthRepository(RuntimeDatabase(database.path))
    stored_claim = restarted.get_claim(committed.claim.id)
    stored_revision = restarted.get_revision(committed.revision.revision.id)

    assert restarted.get_topic(topic.id) == topic
    assert restarted.get_goal(goal.id) == goal
    assert stored_claim == committed.claim
    assert stored_revision == committed.revision
    assert stored_revision is not None
    assert stored_revision.evidence[0].role == "primary"
    assert stored_revision.evidence[0].source.symbol == "summarize_commit_ci"
    assert stored_revision.evidence[0].source.commit_sha == COMMIT_SHA

    with database.connect() as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM understanding_evidence"
        ).fetchone()[0] == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM learning_hypotheses"
        ).fetchone()[0] == 0


def test_provider_unavailable_stays_uncertainty_and_never_creates_claim_truth(tmp_path):
    database = RuntimeDatabase(tmp_path / "unavailable.db")
    truth = LearningTruthRepository(database)
    topic = truth.create_topic(LearningTopic(title="Unavailable source"))
    goal = truth.create_goal(
        LearningGoal(topic_id=topic.id, objective="Verify an unavailable implementation")
    )

    source_learning = LearningSourceEvidenceService(
        _snapshot_service(database, ProviderUnavailableSnapshotter())
    )
    convergence = source_learning.search_and_converge(
        REPO_URL,
        "unavailable implementation",
        ref="main",
    )

    assert convergence.claim_ready is False
    assert convergence.primary is None
    assert convergence.unresolved_reason == "provider_unavailable"

    committed = LearningOutcomeCommitService(truth).commit(
        topic_id=topic.id,
        goal_id=goal.id,
        claim_text="The unavailable implementation may preserve source identity.",
        claim_kind="mechanism",
        convergence=convergence,
    )

    assert committed.outcome == "hypothesis"
    assert committed.hypothesis is not None
    assert committed.hypothesis.unresolved_reason == "provider_unavailable"
    assert committed.claim is None
    assert committed.revision is None

    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM learning_claims").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM claim_revisions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM source_evidence").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM learning_hypotheses").fetchone()[0] == 1
