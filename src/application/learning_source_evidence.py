"""Deterministic convergence from source-search candidates to durable-ready evidence.

The service owns learning-specific retrieval boundaries. It may use GitHub search
and a one-hop graph expansion, but it never persists Claim truth and never copies
retrieval scores, provider status, CI state, or selection diagnostics into
``SourceEvidence``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Any, Iterable

from src.application.github_graph_service import GitHubGraphService
from src.application.github_snapshot_service import GitHubSnapshotService
from src.domain.learning_truth import EvidenceBinding, SourceEvidence


_CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".kts",
    ".mjs",
    ".py",
    ".rs",
    ".ts",
    ".tsx",
}
_DOC_SUFFIXES = {".md", ".mdx", ".rst", ".txt"}
_CONFIG_SUFFIXES = {".json", ".toml", ".yaml", ".yml"}
_DIMENSION_ORDER = {
    "implementation": 0,
    "contract": 1,
    "entry_or_caller": 2,
    "test": 3,
    "config": 4,
    "docs": 5,
    "other": 6,
}
_PROVIDER_UNAVAILABLE_MARKERS = (
    "provider_unavailable",
    "provider_failed",
    "github_http_401",
    "github_http_403",
    "github_http_429",
    "rate_limit",
    "timeout",
    "connection",
    "temporarily_unavailable",
)


@dataclass(frozen=True)
class SourceEvidenceCandidate:
    source: SourceEvidence
    proof_dimension: str
    origin: str = "search"
    supporting_role: str = "corroborating"
    ordinal: int = 0


@dataclass(frozen=True)
class EvidenceConvergenceResult:
    primary: EvidenceBinding | None = None
    supporting: tuple[EvidenceBinding, ...] = ()
    unresolved_reason: str = ""
    candidate_count: int = 0
    dropped_count: int = 0
    one_hop_explored: bool = False

    @property
    def claim_ready(self) -> bool:
        return self.primary is not None

    @property
    def bindings(self) -> tuple[EvidenceBinding, ...]:
        if self.primary is None:
            return ()
        return (self.primary, *self.supporting)


class LearningSourceEvidenceService:
    """Converge commit-pinned source candidates under P2-D evidence rules."""

    def __init__(
        self,
        snapshot_service: GitHubSnapshotService,
        graph_service: GitHubGraphService | None = None,
    ) -> None:
        self.snapshot_service = snapshot_service
        self.graph_service = graph_service

    def search_and_converge(
        self,
        repo_url: str,
        query: str,
        *,
        ref: str = "",
        top_k: int = 12,
        force_refresh: bool = False,
    ) -> EvidenceConvergenceResult:
        searched = self.snapshot_service.search_repository(
            repo_url,
            query,
            ref=ref,
            top_k=top_k,
            include_ci=False,
            force_refresh=force_refresh,
        )
        if searched.get("ok") is not True:
            return EvidenceConvergenceResult(
                unresolved_reason=_search_failure_reason(searched)
            )

        raw_results = searched.get("results", ())
        direct_candidates = self.normalize_candidates(raw_results, origin="search")
        preliminary = self.converge(direct_candidates)
        if preliminary.primary is None:
            return preliminary

        primary_source = preliminary.primary.source
        one_hop_candidates: tuple[SourceEvidenceCandidate, ...] = ()
        explored = False
        if self.graph_service is not None and primary_source.symbol.strip():
            explored = True
            graph = self.graph_service.impact(
                repo_url,
                primary_source.symbol,
                ref=primary_source.commit_sha,
                depth=1,
                max_files=12,
                max_edges=40,
            )
            one_hop_candidates = self.normalize_candidates(
                _nested_evidence_refs(graph),
                origin="one_hop",
            )

        result = self.converge((*direct_candidates, *one_hop_candidates))
        return EvidenceConvergenceResult(
            primary=result.primary,
            supporting=result.supporting,
            unresolved_reason=result.unresolved_reason,
            candidate_count=result.candidate_count,
            dropped_count=result.dropped_count,
            one_hop_explored=explored,
        )

    def normalize_candidates(
        self,
        raw_candidates: Iterable[object],
        *,
        origin: str = "search",
    ) -> tuple[SourceEvidenceCandidate, ...]:
        normalized: list[SourceEvidenceCandidate] = []
        for ordinal, raw in enumerate(raw_candidates):
            if not isinstance(raw, dict):
                continue
            evidence_ref = _evidence_ref(raw)
            source = _source_from_ref(evidence_ref)
            if source is None:
                continue
            proof_dimension = _proof_dimension(raw, source, origin=origin)
            supporting_role = _supporting_role(raw)
            normalized.append(
                SourceEvidenceCandidate(
                    source=source,
                    proof_dimension=proof_dimension,
                    origin=origin,
                    supporting_role=supporting_role,
                    ordinal=ordinal,
                )
            )
        return tuple(normalized)

    def converge(
        self,
        candidates: Iterable[SourceEvidenceCandidate],
    ) -> EvidenceConvergenceResult:
        raw = tuple(candidates)
        if not raw:
            return EvidenceConvergenceResult(unresolved_reason="missing_source")

        unique: dict[tuple[object, ...], SourceEvidenceCandidate] = {}
        for candidate in raw:
            identity = _source_identity(candidate.source)
            existing = unique.get(identity)
            if existing is None or _candidate_rank(candidate) < _candidate_rank(existing):
                unique[identity] = candidate

        ranked = sorted(unique.values(), key=_candidate_rank)
        if not ranked:
            return EvidenceConvergenceResult(
                unresolved_reason="insufficient_evidence",
                candidate_count=len(raw),
                dropped_count=len(raw),
            )

        primary_candidate = ranked[0]
        primary = EvidenceBinding(
            source=primary_candidate.source,
            role="primary",
            position=0,
        )
        immutable_scope = (
            primary.source.repository,
            primary.source.commit_sha,
            primary.source.tree_sha,
        )

        supporting: list[EvidenceBinding] = []
        selected_dimensions: set[tuple[str, str]] = set()
        for candidate in ranked[1:]:
            source = candidate.source
            if (source.repository, source.commit_sha, source.tree_sha) != immutable_scope:
                continue
            role = (
                "supporting_prerequisite"
                if candidate.supporting_role == "prerequisite"
                else "supporting_corroborating"
            )
            dimension_key = (candidate.proof_dimension, role)
            if dimension_key in selected_dimensions:
                continue
            selected_dimensions.add(dimension_key)
            supporting.append(
                EvidenceBinding(
                    source=source,
                    role=role,
                    position=len(supporting) + 1,
                )
            )
            if len(supporting) >= 4:
                break

        selected_count = 1 + len(supporting)
        return EvidenceConvergenceResult(
            primary=primary,
            supporting=tuple(supporting),
            candidate_count=len(raw),
            dropped_count=max(0, len(raw) - selected_count),
        )


def _search_failure_reason(searched: dict[str, Any]) -> str:
    error = str(searched.get("error") or "").strip().casefold()
    provider_status = str(searched.get("provider_status") or "").strip().casefold()
    status = str(searched.get("status") or "").strip().casefold()
    combined = " ".join((error, provider_status, status))
    if any(marker in combined for marker in _PROVIDER_UNAVAILABLE_MARKERS):
        return "provider_unavailable"
    return "missing_source"


def _evidence_ref(raw: dict[str, Any]) -> dict[str, Any]:
    nested = raw.get("evidence_ref")
    if isinstance(nested, dict):
        return nested
    return raw


def _source_from_ref(ref: dict[str, Any]) -> SourceEvidence | None:
    repository = str(ref.get("repository") or "").strip()
    commit_sha = str(ref.get("commit_sha") or "").strip()
    tree_sha = str(ref.get("tree_sha") or "").strip()
    path = str(ref.get("path") or "").strip()
    file_sha = str(ref.get("file_sha") or "").strip()
    try:
        start_line = int(ref.get("start_line") or 0)
        end_line = int(ref.get("end_line") or 0)
    except (TypeError, ValueError):
        return None
    if (
        not repository
        or not commit_sha
        or not tree_sha
        or not path
        or not file_sha
        or start_line <= 0
        or end_line < start_line
    ):
        return None
    return SourceEvidence(
        repository=repository,
        commit_sha=commit_sha,
        tree_sha=tree_sha,
        path=path,
        file_sha=file_sha,
        symbol=str(ref.get("symbol") or ""),
        symbol_kind=str(ref.get("symbol_kind") or ""),
        start_line=start_line,
        end_line=end_line,
        evidence_kind=str(ref.get("kind") or ref.get("evidence_kind") or "source"),
    )


def _proof_dimension(
    raw: dict[str, Any],
    source: SourceEvidence,
    *,
    origin: str,
) -> str:
    explicit = str(raw.get("proof_dimension") or "").strip()
    if explicit in _DIMENSION_ORDER:
        return explicit

    path = source.path.casefold()
    suffix = PurePosixPath(path).suffix
    symbol_kind = source.symbol_kind.casefold()
    if (
        path.startswith("tests/")
        or "/tests/" in f"/{path}"
        or PurePosixPath(path).name.startswith("test_")
        or ".test." in path
        or ".spec." in path
    ):
        return "test"
    if suffix in _DOC_SUFFIXES or path.startswith("docs/"):
        return "docs"
    if suffix in _CONFIG_SUFFIXES or "config" in PurePosixPath(path).name.casefold():
        return "config"
    if (
        "/domain/" in f"/{path}"
        or "/schemas/" in f"/{path}"
        or "/types/" in f"/{path}"
        or symbol_kind in {"interface", "type", "protocol"}
    ):
        return "contract"
    if origin == "one_hop":
        return "entry_or_caller"
    if suffix in _CODE_SUFFIXES and source.symbol.strip():
        return "implementation"
    return "other"


def _supporting_role(raw: dict[str, Any]) -> str:
    hint = str(raw.get("supporting_role") or "").strip().casefold()
    return "prerequisite" if hint == "prerequisite" else "corroborating"


def _candidate_rank(candidate: SourceEvidenceCandidate) -> tuple[object, ...]:
    return (
        _DIMENSION_ORDER.get(candidate.proof_dimension, 99),
        0 if candidate.origin == "search" else 1,
        candidate.ordinal,
        _source_identity(candidate.source),
    )


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


def _nested_evidence_refs(value: object) -> tuple[dict[str, Any], ...]:
    found: list[dict[str, Any]] = []

    def visit(item: object) -> None:
        if isinstance(item, dict):
            if _looks_like_pinned_evidence(item):
                found.append(item)
            for nested in item.values():
                visit(nested)
        elif isinstance(item, (list, tuple)):
            for nested in item:
                visit(nested)

    visit(value)
    return tuple(found)


def _looks_like_pinned_evidence(value: dict[str, Any]) -> bool:
    return bool(
        value.get("repository")
        and value.get("commit_sha")
        and value.get("tree_sha")
        and value.get("path")
        and value.get("file_sha")
        and "start_line" in value
        and "end_line" in value
    )
