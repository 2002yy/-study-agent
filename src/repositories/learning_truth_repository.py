"""Single SQLite transaction owner for durable P2-D learning truth."""

from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from src.domain.learning_truth import (
    ClaimRevision,
    ClaimRevisionBundle,
    EvidenceBinding,
    LearningClaim,
    LearningGoal,
    LearningHypothesis,
    LearningTopic,
    NextStep,
    SourceEvidence,
    UnderstandingClaimResult,
    UnderstandingEvidence,
)
from src.infrastructure.sqlite.database import RuntimeDatabase


_ALLOWED_EVIDENCE_ROLES = {
    "primary",
    "supporting_corroborating",
    "supporting_prerequisite",
}
_ALLOWED_UNDERSTANDING_RESULTS = {"pass", "partial", "fail"}


class LearningTruthRepository:
    """Own normalized durable learning truth and its transaction boundaries."""

    def __init__(self, database: RuntimeDatabase):
        self.database = database
        self.database.initialize()

    def create_topic(self, topic: LearningTopic) -> LearningTopic:
        if not topic.title.strip():
            raise ValueError("Learning topic title is required")
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO learning_topics(id, title, scope, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (topic.id, topic.title, topic.scope, topic.created_at, topic.updated_at),
            )
        return topic

    def get_topic(self, topic_id: str) -> LearningTopic | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_topics WHERE id = ?", (topic_id,)
            ).fetchone()
        return _topic_from_row(row) if row else None

    def list_topics(self) -> list[LearningTopic]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM learning_topics ORDER BY updated_at DESC, id"
            ).fetchall()
        return [_topic_from_row(row) for row in rows]

    def create_goal(self, goal: LearningGoal) -> LearningGoal:
        if not goal.objective.strip():
            raise ValueError("Learning goal objective is required")
        with self.database.connect() as connection:
            self._require_topic(connection, goal.topic_id)
            connection.execute(
                """
                INSERT INTO learning_goals(
                    id, topic_id, objective, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    goal.id,
                    goal.topic_id,
                    goal.objective,
                    goal.status,
                    goal.created_at,
                    goal.updated_at,
                ),
            )
        return goal

    def get_goal(self, goal_id: str) -> LearningGoal | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_goals WHERE id = ?", (goal_id,)
            ).fetchone()
        return _goal_from_row(row) if row else None

    def list_goals(self, topic_id: str) -> list[LearningGoal]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM learning_goals
                WHERE topic_id = ? ORDER BY updated_at DESC, id
                """,
                (topic_id,),
            ).fetchall()
        return [_goal_from_row(row) for row in rows]

    def add_prerequisite(self, goal_id: str, prerequisite_goal_id: str) -> None:
        if goal_id == prerequisite_goal_id:
            raise ValueError("Learning goal cannot require itself")
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._require_goal(connection, goal_id)
                self._require_goal(connection, prerequisite_goal_id)
                if self._would_create_prerequisite_cycle(
                    connection,
                    goal_id=goal_id,
                    prerequisite_goal_id=prerequisite_goal_id,
                ):
                    raise ValueError("Learning goal prerequisite cycle detected")
                connection.execute(
                    """
                    INSERT INTO learning_goal_prerequisites(goal_id, prerequisite_goal_id)
                    VALUES (?, ?)
                    """,
                    (goal_id, prerequisite_goal_id),
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def list_prerequisite_ids(self, goal_id: str) -> list[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT prerequisite_goal_id
                FROM learning_goal_prerequisites
                WHERE goal_id = ? ORDER BY prerequisite_goal_id
                """,
                (goal_id,),
            ).fetchall()
        return [str(row[0]) for row in rows]

    def create_claim(self, claim: LearningClaim) -> LearningClaim:
        with self.database.connect() as connection:
            self._require_topic(connection, claim.topic_id)
            connection.execute(
                """
                INSERT INTO learning_claims(id, topic_id, scope, claim_kind, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    claim.id,
                    claim.topic_id,
                    claim.scope,
                    claim.claim_kind,
                    claim.created_at,
                ),
            )
        return claim

    def get_claim(self, claim_id: str) -> LearningClaim | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_claims WHERE id = ?", (claim_id,)
            ).fetchone()
        return _claim_from_row(row) if row else None

    def list_claims(self, topic_id: str) -> list[LearningClaim]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM learning_claims
                WHERE topic_id = ? ORDER BY created_at, id
                """,
                (topic_id,),
            ).fetchall()
        return [_claim_from_row(row) for row in rows]

    def commit_revision(
        self,
        revision: ClaimRevision,
        bindings: Sequence[EvidenceBinding],
    ) -> ClaimRevisionBundle:
        normalized = tuple(bindings)
        self._validate_revision_bindings(normalized)
        if not revision.claim_text.strip():
            raise ValueError("Claim revision text is required")

        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                self._require_claim(connection, revision.claim_id)
                connection.execute(
                    """
                    INSERT INTO claim_revisions(
                        id, claim_id, claim_text, source_commit, reason, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        revision.id,
                        revision.claim_id,
                        revision.claim_text,
                        revision.source_commit,
                        revision.reason,
                        revision.created_at,
                    ),
                )
                stored_bindings: list[EvidenceBinding] = []
                for binding in sorted(normalized, key=lambda item: item.position):
                    stored_source = self._store_or_reuse_source_evidence(
                        connection, binding.source
                    )
                    connection.execute(
                        """
                        INSERT INTO claim_revision_evidence(
                            claim_revision_id, source_evidence_id, role, position
                        ) VALUES (?, ?, ?, ?)
                        """,
                        (
                            revision.id,
                            stored_source.id,
                            binding.role,
                            binding.position,
                        ),
                    )
                    stored_bindings.append(
                        EvidenceBinding(
                            source=stored_source,
                            role=binding.role,
                            position=binding.position,
                        )
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return ClaimRevisionBundle(revision=revision, evidence=tuple(stored_bindings))

    def get_revision(self, revision_id: str) -> ClaimRevisionBundle | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM claim_revisions WHERE id = ?", (revision_id,)
            ).fetchone()
            if row is None:
                return None
            evidence_rows = connection.execute(
                """
                SELECT e.*, link.role, link.position
                FROM claim_revision_evidence AS link
                JOIN source_evidence AS e ON e.id = link.source_evidence_id
                WHERE link.claim_revision_id = ?
                ORDER BY link.position, e.id
                """,
                (revision_id,),
            ).fetchall()
        return ClaimRevisionBundle(
            revision=_revision_from_row(row),
            evidence=tuple(
                EvidenceBinding(
                    source=_source_evidence_from_row(item),
                    role=str(item["role"]),
                    position=int(item["position"]),
                )
                for item in evidence_rows
            ),
        )

    def list_revisions(self, claim_id: str) -> list[ClaimRevisionBundle]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT id FROM claim_revisions
                WHERE claim_id = ? ORDER BY created_at, id
                """,
                (claim_id,),
            ).fetchall()
        result: list[ClaimRevisionBundle] = []
        for row in rows:
            bundle = self.get_revision(str(row["id"]))
            if bundle is not None:
                result.append(bundle)
        return result

    def create_understanding_evidence(
        self,
        evidence: UnderstandingEvidence,
        results: Sequence[UnderstandingClaimResult],
    ) -> UnderstandingEvidence:
        normalized = tuple(results)
        if not 1 <= len(normalized) <= 3:
            raise ValueError("Understanding evidence must evaluate 1 to 3 claim revisions")
        if len({item.claim_revision_id for item in normalized}) != len(normalized):
            raise ValueError("Understanding evidence contains duplicate claim revisions")
        if any(item.understanding_evidence_id != evidence.id for item in normalized):
            raise ValueError("Understanding result owner does not match evidence id")
        if any(item.result not in _ALLOWED_UNDERSTANDING_RESULTS for item in normalized):
            raise ValueError("Unsupported understanding result")

        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                for item in normalized:
                    self._require_revision(connection, item.claim_revision_id)
                connection.execute(
                    """
                    INSERT INTO understanding_evidence(
                        id, method, prompt, user_response, verified_at
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        evidence.id,
                        evidence.method,
                        evidence.prompt,
                        evidence.user_response,
                        evidence.verified_at,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO understanding_evidence_claims(
                        understanding_evidence_id, claim_revision_id, result
                    ) VALUES (?, ?, ?)
                    """,
                    [
                        (evidence.id, item.claim_revision_id, item.result)
                        for item in normalized
                    ],
                )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return evidence

    def get_understanding_evidence(
        self, evidence_id: str
    ) -> tuple[UnderstandingEvidence, tuple[UnderstandingClaimResult, ...]] | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM understanding_evidence WHERE id = ?", (evidence_id,)
            ).fetchone()
            if row is None:
                return None
            result_rows = connection.execute(
                """
                SELECT * FROM understanding_evidence_claims
                WHERE understanding_evidence_id = ? ORDER BY claim_revision_id
                """,
                (evidence_id,),
            ).fetchall()
        evidence = _understanding_from_row(row)
        return evidence, tuple(
            UnderstandingClaimResult(
                understanding_evidence_id=str(item["understanding_evidence_id"]),
                claim_revision_id=str(item["claim_revision_id"]),
                result=str(item["result"]),
            )
            for item in result_rows
        )

    def create_hypothesis(self, hypothesis: LearningHypothesis) -> LearningHypothesis:
        if not hypothesis.text.strip():
            raise ValueError("Learning hypothesis text is required")
        with self.database.connect() as connection:
            self._require_topic(connection, hypothesis.topic_id)
            goal = self._require_goal(connection, hypothesis.goal_id)
            if str(goal["topic_id"]) != hypothesis.topic_id:
                raise ValueError("Learning hypothesis goal belongs to another topic")
            connection.execute(
                """
                INSERT INTO learning_hypotheses(
                    id, topic_id, goal_id, text, unresolved_reason,
                    resolved_by_claim_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    hypothesis.id,
                    hypothesis.topic_id,
                    hypothesis.goal_id,
                    hypothesis.text,
                    hypothesis.unresolved_reason,
                    hypothesis.resolved_by_claim_id,
                    hypothesis.created_at,
                ),
            )
        return hypothesis

    def get_hypothesis(self, hypothesis_id: str) -> LearningHypothesis | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM learning_hypotheses WHERE id = ?", (hypothesis_id,)
            ).fetchone()
        return _hypothesis_from_row(row) if row else None

    def create_next_step(self, next_step: NextStep) -> NextStep:
        if not next_step.text.strip():
            raise ValueError("Next step text is required")
        with self.database.connect() as connection:
            self._require_goal(connection, next_step.goal_id)
            connection.execute(
                """
                INSERT INTO next_steps(
                    id, goal_id, text, status, is_primary, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_step.id,
                    next_step.goal_id,
                    next_step.text,
                    next_step.status,
                    int(next_step.is_primary),
                    next_step.created_at,
                    next_step.updated_at,
                ),
            )
        return next_step

    def get_next_step(self, next_step_id: str) -> NextStep | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM next_steps WHERE id = ?", (next_step_id,)
            ).fetchone()
        return _next_step_from_row(row) if row else None

    @staticmethod
    def _validate_revision_bindings(bindings: tuple[EvidenceBinding, ...]) -> None:
        if not bindings:
            raise ValueError("Claim revision requires exactly one primary evidence")
        primary_count = sum(binding.role == "primary" for binding in bindings)
        supporting_count = len(bindings) - primary_count
        if primary_count != 1:
            raise ValueError("Claim revision requires exactly one primary evidence")
        if supporting_count > 4:
            raise ValueError("Claim revision supports at most four supporting evidence items")
        if any(binding.role not in _ALLOWED_EVIDENCE_ROLES for binding in bindings):
            raise ValueError("Unsupported claim evidence role")
        positions = [binding.position for binding in bindings]
        if any(position < 0 for position in positions) or len(set(positions)) != len(positions):
            raise ValueError("Claim evidence positions must be unique non-negative values")
        identities = [_source_identity(binding.source) for binding in bindings]
        if len(set(identities)) != len(identities):
            raise ValueError("Claim revision contains duplicate source evidence")
        for binding in bindings:
            _validate_source_evidence(binding.source)

    @staticmethod
    def _store_or_reuse_source_evidence(
        connection: sqlite3.Connection,
        source: SourceEvidence,
    ) -> SourceEvidence:
        identity = _source_identity(source)
        row = connection.execute(
            """
            SELECT * FROM source_evidence
            WHERE repository = ? AND commit_sha = ? AND tree_sha = ? AND path = ?
              AND file_sha = ? AND symbol = ? AND symbol_kind = ?
              AND start_line = ? AND end_line = ? AND evidence_kind = ?
            """,
            identity,
        ).fetchone()
        if row is not None:
            return _source_evidence_from_row(row)
        connection.execute(
            """
            INSERT INTO source_evidence(
                id, repository, commit_sha, tree_sha, path, file_sha,
                symbol, symbol_kind, start_line, end_line, evidence_kind, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source.id,
                *identity,
                source.created_at,
            ),
        )
        return source

    @staticmethod
    def _would_create_prerequisite_cycle(
        connection: sqlite3.Connection,
        *,
        goal_id: str,
        prerequisite_goal_id: str,
    ) -> bool:
        row = connection.execute(
            """
            WITH RECURSIVE ancestors(id) AS (
                SELECT prerequisite_goal_id
                FROM learning_goal_prerequisites
                WHERE goal_id = ?
                UNION
                SELECT edge.prerequisite_goal_id
                FROM learning_goal_prerequisites AS edge
                JOIN ancestors ON edge.goal_id = ancestors.id
            )
            SELECT 1 FROM ancestors WHERE id = ? LIMIT 1
            """,
            (prerequisite_goal_id, goal_id),
        ).fetchone()
        return row is not None

    @staticmethod
    def _require_topic(connection: sqlite3.Connection, topic_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM learning_topics WHERE id = ?", (topic_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Learning topic not found: {topic_id}")
        return row

    @staticmethod
    def _require_goal(connection: sqlite3.Connection, goal_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM learning_goals WHERE id = ?", (goal_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Learning goal not found: {goal_id}")
        return row

    @staticmethod
    def _require_claim(connection: sqlite3.Connection, claim_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM learning_claims WHERE id = ?", (claim_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Learning claim not found: {claim_id}")
        return row

    @staticmethod
    def _require_revision(connection: sqlite3.Connection, revision_id: str) -> sqlite3.Row:
        row = connection.execute(
            "SELECT * FROM claim_revisions WHERE id = ?", (revision_id,)
        ).fetchone()
        if row is None:
            raise ValueError(f"Claim revision not found: {revision_id}")
        return row


def _source_identity(source: SourceEvidence) -> tuple[object, ...]:
    return (
        source.repository,
        source.commit_sha,
        source.tree_sha,
        source.path,
        source.file_sha,
        source.symbol,
        source.symbol_kind,
        source.start_line,
        source.end_line,
        source.evidence_kind,
    )


def _validate_source_evidence(source: SourceEvidence) -> None:
    required = (
        source.repository,
        source.commit_sha,
        source.tree_sha,
        source.path,
        source.file_sha,
        source.evidence_kind,
    )
    if any(not value.strip() for value in required):
        raise ValueError("Source evidence identity fields are required")
    if source.start_line <= 0 or source.end_line < source.start_line:
        raise ValueError("Source evidence line range is invalid")


def _topic_from_row(row: sqlite3.Row) -> LearningTopic:
    return LearningTopic(
        id=str(row["id"]),
        title=str(row["title"]),
        scope=str(row["scope"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _goal_from_row(row: sqlite3.Row) -> LearningGoal:
    return LearningGoal(
        id=str(row["id"]),
        topic_id=str(row["topic_id"]),
        objective=str(row["objective"]),
        status=str(row["status"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _claim_from_row(row: sqlite3.Row) -> LearningClaim:
    return LearningClaim(
        id=str(row["id"]),
        topic_id=str(row["topic_id"]),
        scope=str(row["scope"]),
        claim_kind=str(row["claim_kind"]),
        created_at=str(row["created_at"]),
    )


def _revision_from_row(row: sqlite3.Row) -> ClaimRevision:
    return ClaimRevision(
        id=str(row["id"]),
        claim_id=str(row["claim_id"]),
        claim_text=str(row["claim_text"]),
        source_commit=str(row["source_commit"]),
        reason=str(row["reason"]),
        created_at=str(row["created_at"]),
    )


def _source_evidence_from_row(row: sqlite3.Row) -> SourceEvidence:
    return SourceEvidence(
        id=str(row["id"]),
        repository=str(row["repository"]),
        commit_sha=str(row["commit_sha"]),
        tree_sha=str(row["tree_sha"]),
        path=str(row["path"]),
        file_sha=str(row["file_sha"]),
        symbol=str(row["symbol"]),
        symbol_kind=str(row["symbol_kind"]),
        start_line=int(row["start_line"]),
        end_line=int(row["end_line"]),
        evidence_kind=str(row["evidence_kind"]),
        created_at=str(row["created_at"]),
    )


def _understanding_from_row(row: sqlite3.Row) -> UnderstandingEvidence:
    return UnderstandingEvidence(
        id=str(row["id"]),
        method=str(row["method"]),
        prompt=str(row["prompt"]),
        user_response=str(row["user_response"]),
        verified_at=str(row["verified_at"]),
    )


def _hypothesis_from_row(row: sqlite3.Row) -> LearningHypothesis:
    return LearningHypothesis(
        id=str(row["id"]),
        topic_id=str(row["topic_id"]),
        goal_id=str(row["goal_id"]),
        text=str(row["text"]),
        unresolved_reason=str(row["unresolved_reason"]),
        resolved_by_claim_id=(
            str(row["resolved_by_claim_id"])
            if row["resolved_by_claim_id"] is not None
            else None
        ),
        created_at=str(row["created_at"]),
    )


def _next_step_from_row(row: sqlite3.Row) -> NextStep:
    return NextStep(
        id=str(row["id"]),
        goal_id=str(row["goal_id"]),
        text=str(row["text"]),
        status=str(row["status"]),
        is_primary=bool(row["is_primary"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )
