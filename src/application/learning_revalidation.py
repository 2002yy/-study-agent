"""Explicit claim revalidation: re-converge a Claim against its source of truth.

The entry re-runs the deterministic source-search convergence for an existing
durable Claim, then commits a new Revision on the same Claim lineage
(reason ``revalidated``). It never creates a second Claim and never decides
user mastery.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.application.learning_freshness import LearningFreshnessService
from src.application.learning_outcome_commit import LearningOutcomeCommitService
from src.application.learning_source_evidence import (
    LearningSourceEvidenceService,
)
from src.repositories.learning_truth_repository import LearningTruthRepository


@dataclass(frozen=True)
class RevalidationResult:
    outcome: str
    claim_id: str
    revision_id: str = ""
    unresolved_reason: str = ""
    head_commit: str = ""
    freshness_status: str = ""
    unavailable_reason: str = ""


class LearningRevalidationService:
    """Revalidate an existing durable Claim without forking its lineage."""

    def __init__(
        self,
        repository: LearningTruthRepository,
        source_evidence_service: LearningSourceEvidenceService,
        commit_service: LearningOutcomeCommitService,
        freshness_service: LearningFreshnessService | None = None,
    ) -> None:
        self.repository = repository
        self.source_evidence_service = source_evidence_service
        self.commit_service = commit_service
        self.freshness_service = freshness_service

    def revalidate(self, thread_id: str, claim_id: str) -> RevalidationResult:
        claim = self.repository.get_claim(claim_id)
        if claim is None:
            raise ValueError("claim_not_found")
        goal = self.repository.get_focus_goal(thread_id)
        if goal is None:
            raise ValueError("no_active_goal")
        bundles = self.repository.list_revisions(claim_id)
        if not bundles:
            raise ValueError("claim_has_no_revision")
        bundle = bundles[-1]
        primary = next(
            (item for item in bundle.evidence if item.role == "primary"),
            None,
        )
        repository_url = primary.source.repository if primary is not None else ""
        if not repository_url:
            raise ValueError("claim_has_no_primary_source")

        claim_text = bundle.revision.claim_text
        convergence = self.source_evidence_service.search_and_converge(
            repository_url,
            claim_text,
        )
        if not convergence.claim_ready:
            return RevalidationResult(
                outcome="no_convergence",
                claim_id=claim_id,
                unresolved_reason=convergence.unresolved_reason,
            )

        committed = self.commit_service.commit(
            topic_id=claim.topic_id,
            goal_id=goal.id,
            claim_text=claim_text,
            claim_kind=claim.claim_kind,
            scope=claim.scope or "project",
            convergence=convergence,
            existing_claim_id=claim_id,
            revision_reason="revalidated",
        )
        if committed.revision is None:
            return RevalidationResult(
                outcome=committed.outcome,
                claim_id=claim_id,
                unresolved_reason=(
                    f"commit_failed: {committed.outcome}"
                ),
            )
        return RevalidationResult(
            outcome="revalidated",
            claim_id=claim_id,
            revision_id=committed.revision.revision.id,
            head_commit=str(convergence.primary.source.commit_sha or "")
            if convergence.primary is not None
            else "",
            freshness_status=self._post_revalidation_freshness(committed.revision),
        )

    def _post_revalidation_freshness(
        self, bundle: Any
    ) -> str:
        if self.freshness_service is None:
            return ""
        try:
            evaluation = self.freshness_service.evaluate(bundle)
        except Exception as exc:  # noqa: BLE001 - provider boundary explicit
            return f"unavailable: {type(exc).__name__}: {exc}"
        if evaluation.status == "unavailable":
            return f"unavailable: {evaluation.unavailable_reason}"
        return str(evaluation.status)