"""Deterministic freshness evaluation for durable source-backed Claims.

Freshness is an on-demand derived state (STATE_MODEL.md): it is never
persisted and never evaluated in a background sweep. Evaluation only
happens when a Goal/Claim is restored, referenced, or explicitly
checked.

Status rules (state_invariants.md L6/L7):
- Primary unchanged -> ``current``;
- Primary materially changed -> ``stale_candidate``;
- Primary removed / unmappable -> ``source_changed``;
- corroborating supporting drift is recorded but never stale;
- prerequisite material drift can trigger ``stale_candidate``;
- provider failure -> ``unavailable``, never "Claim is false".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from src.domain.learning_truth import ClaimRevisionBundle, utc_now
from src.web.github_structure import RepositoryStructureIndex


class HeadResolver(Protocol):
    """Resolve a heads ref to a pinned commit and path -> blob-sha tree."""

    def resolve_head(self, repo_url: str, ref: str = "") -> dict[str, Any]: ...


class BlobReader(Protocol):
    """Read a git blob's decoded text content by its exact blob sha."""

    def read_blob(self, repo_url: str, sha: str) -> str: ...


@dataclass(frozen=True)
class FreshnessEvaluation:
    status: str
    head_commit: str = ""
    evaluated_at: str = field(default_factory=utc_now)
    unavailable_reason: str = ""
    primary: dict[str, Any] = field(default_factory=dict)
    supporting_drift: tuple[dict[str, Any], ...] = ()


def _normalize_body(body: str) -> str:
    """Compare symbol bodies ignoring trailing whitespace and empty lines."""
    return "\n".join(line.rstrip() for line in body.splitlines() if line.strip())


def _lines(text: str, start_line: int, end_line: int) -> str:
    lines = text.splitlines()
    return "\n".join(lines[max(0, start_line - 1) : max(start_line - 1, end_line)])


class LearningFreshnessService:
    """Evaluate whether the latest Claim revision still matches its sources."""

    def __init__(
        self,
        head_resolver: HeadResolver,
        blob_reader: BlobReader,
    ) -> None:
        self.head_resolver = head_resolver
        self.blob_reader = blob_reader

    def evaluate(
        self,
        bundle: ClaimRevisionBundle,
        *,
        ref: str = "",
    ) -> FreshnessEvaluation:
        primary = next(
            (item for item in bundle.evidence if item.role == "primary"),
            None,
        )
        if primary is None:
            return FreshnessEvaluation(
                status="unavailable",
                unavailable_reason="no_primary_evidence",
            )

        head = self.head_resolver.resolve_head(primary.source.repository, ref)
        if head.get("ok") is not True:
            return FreshnessEvaluation(
                status="unavailable",
                head_commit=str(head.get("commit_sha") or ""),
                unavailable_reason=str(
                    head.get("error") or "head_resolution_failed"
                ),
            )

        head_commit = str(head.get("commit_sha") or "")
        tree = head.get("tree") or {}

        primary_detail, primary_status = self._evaluate_primary(
            primary, tree=tree
        )
        if primary_status is not None:
            return FreshnessEvaluation(
                status=primary_status,
                head_commit=head_commit,
                primary=primary_detail,
                unavailable_reason=(
                    str(primary_detail.get("error") or "")
                    if primary_status == "unavailable"
                    else ""
                ),
            )

        drifts: list[dict[str, Any]] = []
        prerequisite_material = False
        for binding in bundle.evidence:
            if binding.role == "primary":
                continue
            detail = self._evaluate_supporting(binding, tree=tree)
            drifts.append(detail)
            if (
                binding.role == "supporting_prerequisite"
                and detail.get("materially_changed") is True
            ):
                prerequisite_material = True

        if prerequisite_material:
            return FreshnessEvaluation(
                status="stale_candidate",
                head_commit=head_commit,
                primary=primary_detail,
                supporting_drift=tuple(drifts),
            )
        return FreshnessEvaluation(
            status="current",
            head_commit=head_commit,
            primary=primary_detail,
            supporting_drift=tuple(drifts),
        )

    def _evaluate_primary(
        self,
        binding: Any,
        *,
        tree: dict[str, Any],
    ) -> tuple[dict[str, Any], str | None]:
        source = binding.source
        path = source.path
        base = {
            "path": path,
            "symbol": source.symbol,
            "head_file_sha": tree.get(path) or "",
        }
        if path not in tree:
            return {**base, "reason": "primary_path_missing", "matched": False}, (
                "source_changed"
            )
        head_sha = str(tree[path])
        if head_sha == source.file_sha:
            return {
                **base,
                "reason": "identical_blob_sha",
                "matched": True,
                "body_unchanged": True,
            }, None

        try:
            old_content = self.blob_reader.read_blob(source.repository, source.file_sha)
            head_content = self.blob_reader.read_blob(source.repository, head_sha)
        except Exception as exc:  # noqa: BLE001 - provider boundary stays explicit
            message = f"blob_read_failed: {type(exc).__name__}: {exc}"
            return {
                **base,
                "reason": "blob_read_failed",
                "error": message,
                "matched": None,
                "body_unchanged": None,
            }, "unavailable"

        old_body = _lines(old_content, source.start_line, source.end_line)
        head_def = self._remap_symbol(head_content, path=path, symbol=source.symbol)
        if head_def is None:
            return {
                **base,
                "reason": "primary_symbol_not_found",
                "matched": False,
                "body_unchanged": None,
            }, "source_changed"

        new_body = _lines(head_content, head_def["start_line"], head_def["end_line"])
        unchanged = _normalize_body(old_body) == _normalize_body(new_body)
        return (
            {
                **base,
                "reason": (
                    "normalized_body_equal"
                    if unchanged
                    else "normalized_body_changed"
                ),
                "matched": True,
                "body_unchanged": unchanged,
            },
            None if unchanged else "stale_candidate",
        )

    def _evaluate_supporting(
        self,
        binding: Any,
        *,
        tree: dict[str, Any],
    ) -> dict[str, Any]:
        source = binding.source
        path = source.path
        base = {
            "role": binding.role,
            "path": path,
            "symbol": source.symbol,
            "head_file_sha": tree.get(path) or "",
        }
        if path not in tree:
            return {**base, "reason": "path_missing", "materially_changed": True}
        head_sha = str(tree[path])
        if head_sha == source.file_sha:
            return {
                **base,
                "reason": "identical_blob_sha",
                "materially_changed": False,
            }
        try:
            old_content = self.blob_reader.read_blob(source.repository, source.file_sha)
            head_content = self.blob_reader.read_blob(source.repository, head_sha)
        except Exception as exc:  # noqa: BLE001 - provider boundary stays explicit
            return {
                **base,
                "reason": "blob_read_failed",
                "error": f"{type(exc).__name__}: {exc}",
                "materially_changed": None,
            }

        old_body = _lines(old_content, source.start_line, source.end_line)
        head_def = self._remap_symbol(head_content, path=path, symbol=source.symbol)
        if head_def is None:
            return {
                **base,
                "reason": "symbol_not_found",
                "materially_changed": True,
            }
        new_body = _lines(head_content, head_def["start_line"], head_def["end_line"])
        unchanged = _normalize_body(old_body) == _normalize_body(new_body)
        return {
            **base,
            "reason": (
                "normalized_body_equal" if unchanged else "normalized_body_changed"
            ),
            "materially_changed": not unchanged,
        }

    @staticmethod
    def _remap_symbol(
        head_content: str,
        *,
        path: str,
        symbol: str,
    ) -> dict[str, Any] | None:
        if not symbol:
            return None
        index = RepositoryStructureIndex(
            {"files": [{"path": path, "content": head_content}]}
        )
        for definition in index.definitions(symbol, top_k=20):
            evidence = definition.get("evidence") or {}
            if evidence.get("path") != path:
                continue
            start_line = int(evidence.get("start_line") or 1)
            end_line = int(evidence.get("end_line") or start_line)
            return {
                "start_line": start_line,
                "end_line": max(end_line, start_line),
            }
        return None