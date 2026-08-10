"""Freshness evaluation contract tests (P2-D-4A).

Covers TESTING.md section 5 (P2-D-4 freshness rules) against a
deterministic fake head resolver + fake blob reader, using the real
Study Agent source file for symbol remapping (same pattern as the mini
Golden Journey tests).
"""

from __future__ import annotations

from pathlib import Path

from src.application.learning_freshness import LearningFreshnessService
from src.domain.learning_truth import (
    ClaimRevision,
    ClaimRevisionBundle,
    EvidenceBinding,
    SourceEvidence,
)

REPOSITORY = "2002yy/study-agent"
REPO_URL = "https://github.com/2002yy/study-agent"
SOURCE_PATH = "src/application/github_source_evidence.py"
OLD_COMMIT = "old" * 40
OLD_FILE_SHA = "old-blob-sha"
HEAD_FILE_SHA = "head-blob-sha"
HEAD_COMMIT = "head" * 40
SYMBOL = "summarize_commit_ci"


def _real_source_text() -> str:
    return (
        Path(__file__).resolve().parents[1] / SOURCE_PATH
    ).read_text(encoding="utf-8")


def _changed_line() -> str:
    return 'requested_sha = str(commit_sha or "").strip().lower()'


def _text_changed_body() -> str:
    return _real_source_text().replace(
        _changed_line(), 'requested_sha = str(commit_sha or "").strip().upper()'
    )


def _text_whitespace_only() -> str:
    return _real_source_text().replace(_changed_line(), _changed_line() + "   ")


def _text_symbol_removed() -> str:
    text = _real_source_text()
    start = text.index("def summarize_commit_ci")
    return text[:start] + ("# function removed\n" * 3) + text[start + 2000 :].split(
        "\n", 1
    )[1]


def _supporting_text() -> str:
    return "# supporting module\n\ndef helper():\n    return 1\n"


def _binding(
    *,
    path: str,
    file_sha: str,
    symbol: str,
    role: str,
    position: int,
    start_line: int,
    end_line: int,
    commit_sha: str = OLD_COMMIT,
) -> EvidenceBinding:
    return EvidenceBinding(
        source=SourceEvidence(
            repository=REPOSITORY,
            commit_sha=commit_sha,
            tree_sha=commit_sha,
            path=path,
            file_sha=file_sha,
            symbol=symbol,
            symbol_kind="function",
            start_line=start_line,
            end_line=end_line,
        ),
        role=role,
        position=position,
    )


def _primary_binding_for(text: str) -> EvidenceBinding:
    content = text.splitlines()
    start = next(
        index + 1
        for index, line in enumerate(content)
        if line.startswith("def summarize_commit_ci")
    )
    end = start + 1
    while end <= len(content):
        if content[end - 1].startswith(("def ", "class ", "@", "async ")):
            break
        end += 1
    return _binding(
        path=SOURCE_PATH,
        file_sha=OLD_FILE_SHA,
        symbol=SYMBOL,
        role="primary",
        position=0,
        start_line=start,
        end_line=end,
    )


class FakeHeadResolver:
    def __init__(
        self,
        tree: dict[str, str],
        *,
        ok: bool = True,
        error: str = "",
        commit_sha: str = HEAD_COMMIT,
    ) -> None:
        self.tree = tree
        self.ok = ok
        self.error = error
        self.commit_sha = commit_sha
        self.calls: list[tuple[str, str]] = []

    def resolve_head(self, repo_url: str, ref: str = "") -> dict:
        self.calls.append((repo_url, ref))
        if not self.ok:
            return {
                "ok": False,
                "error": self.error,
                "commit_sha": "",
                "tree": {},
            }
        return {
            "ok": True,
            "commit_sha": self.commit_sha,
            "tree": dict(self.tree),
        }


class FakeBlobReader:
    def __init__(self, blobs: dict[str, str]) -> None:
        self.blobs = blobs
        self.reads: list[str] = []

    def read_blob(self, repo_url: str, sha: str) -> str:
        self.reads.append(sha)
        if sha not in self.blobs:
            raise LookupError(f"missing blob {sha}")
        return self.blobs[sha]


def _service(head: FakeHeadResolver, blobs: FakeBlobReader) -> LearningFreshnessService:
    return LearningFreshnessService(head_resolver=head, blob_reader=blobs)


def _bundle_with(primary: EvidenceBinding, supporting: tuple = ()) -> ClaimRevisionBundle:
    return ClaimRevisionBundle(
        revision=ClaimRevision(
            claim_id="claim-1",
            claim_text="CI validation is supporting observation, not SourceEvidence identity.",
            source_commit=OLD_COMMIT,
            reason="initial",
        ),
        evidence=(primary, *supporting),
    )


def test_head_file_sha_unchanged_is_current_without_reading_blobs():
    primary = _primary_binding_for(_real_source_text())
    head = FakeHeadResolver({SOURCE_PATH: OLD_FILE_SHA})
    blobs = FakeBlobReader({})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "current"
    assert result.head_commit == HEAD_COMMIT
    assert result.primary["reason"] == "identical_blob_sha"
    assert result.primary["body_unchanged"] is True
    assert result.primary["head_file_sha"] == OLD_FILE_SHA
    assert blobs.reads == []
    assert head.calls == [(REPOSITORY, "")]


def test_whitespace_only_body_change_is_current():
    old_text = _real_source_text()
    head_text = _text_whitespace_only()
    primary = _primary_binding_for(old_text)
    head = FakeHeadResolver({SOURCE_PATH: HEAD_FILE_SHA})
    blobs = FakeBlobReader({HEAD_FILE_SHA: head_text, OLD_FILE_SHA: old_text})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "current"
    assert result.primary["reason"] == "normalized_body_equal"
    assert result.primary["body_unchanged"] is True
    assert set(blobs.reads) == {OLD_FILE_SHA, HEAD_FILE_SHA}


def test_material_primary_change_is_stale_candidate():
    old_text = _real_source_text()
    head_text = _text_changed_body()
    primary = _primary_binding_for(old_text)
    head = FakeHeadResolver({SOURCE_PATH: HEAD_FILE_SHA})
    blobs = FakeBlobReader({HEAD_FILE_SHA: head_text, OLD_FILE_SHA: old_text})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "stale_candidate"
    assert result.primary["reason"] == "normalized_body_changed"
    assert result.primary["body_unchanged"] is False


def test_primary_path_removed_is_source_changed():
    primary = _primary_binding_for(_real_source_text())
    head = FakeHeadResolver({})
    blobs = FakeBlobReader({})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "source_changed"
    assert result.primary["reason"] == "primary_path_missing"
    assert blobs.reads == []


def test_primary_symbol_unmappable_is_source_changed():
    old_text = _real_source_text()
    head_text = _text_symbol_removed()
    primary = _primary_binding_for(old_text)
    head = FakeHeadResolver({SOURCE_PATH: HEAD_FILE_SHA})
    blobs = FakeBlobReader({HEAD_FILE_SHA: head_text, OLD_FILE_SHA: old_text})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "source_changed"
    assert result.primary["reason"] == "primary_symbol_not_found"
    assert result.primary["matched"] is False


def test_corroborating_support_drift_does_not_stale():
    old_text = _real_source_text()
    supporting_old = _supporting_text()
    supporting_head = supporting_old + "\n# drifted comment\n"
    primary = _primary_binding_for(old_text)
    corroborating = _binding(
        path="src/application/support.py",
        file_sha="support-old-sha",
        symbol="helper",
        role="supporting_corroborating",
        position=1,
        start_line=1,
        end_line=3,
    )
    head = FakeHeadResolver(
        {SOURCE_PATH: OLD_FILE_SHA, "src/application/support.py": "support-head-sha"}
    )
    blobs = FakeBlobReader(
        {
            "support-head-sha": supporting_head,
            "support-old-sha": supporting_old,
        }
    )
    result = _service(head, blobs).evaluate(
        _bundle_with(primary, supporting=(corroborating,))
    )

    assert result.status == "current"
    assert result.primary["reason"] == "identical_blob_sha"
    drifts = [item for item in result.supporting_drift if item["path"] == "src/application/support.py"]
    assert drifts and drifts[0]["materially_changed"] is True
    assert drifts[0]["role"] == "supporting_corroborating"


def test_prerequisite_material_change_triggers_stale_candidate():
    old_text = _real_source_text()
    prereq_old = _supporting_text()
    prereq_head = prereq_old.replace("return 1", "return 2")
    primary = _primary_binding_for(old_text)
    prerequisite = _binding(
        path="src/application/support.py",
        file_sha="prereq-old-sha",
        symbol="helper",
        role="supporting_prerequisite",
        position=1,
        start_line=1,
        end_line=3,
    )
    head = FakeHeadResolver(
        {SOURCE_PATH: OLD_FILE_SHA, "src/application/support.py": "prereq-head-sha"}
    )
    blobs = FakeBlobReader(
        {
            "prereq-head-sha": prereq_head,
            "prereq-old-sha": prereq_old,
        }
    )
    result = _service(head, blobs).evaluate(
        _bundle_with(primary, supporting=(prerequisite,))
    )

    assert result.status == "stale_candidate"
    assert result.primary["reason"] == "identical_blob_sha"
    prereq_details = [
        item for item in result.supporting_drift if item["role"] == "supporting_prerequisite"
    ]
    assert prereq_details and prereq_details[0]["materially_changed"] is True


def test_provider_unavailable_head_resolution_is_unavailable_not_stale():
    primary = _primary_binding_for(_real_source_text())
    head = FakeHeadResolver({}, ok=False, error="github_http_403")
    blobs = FakeBlobReader({})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "unavailable"
    assert result.unavailable_reason == "github_http_403"
    assert blobs.reads == []


def test_blob_read_failure_is_unavailable_not_stale():
    old_text = _real_source_text()
    primary = _primary_binding_for(old_text)
    head = FakeHeadResolver({SOURCE_PATH: HEAD_FILE_SHA})
    blobs = FakeBlobReader({HEAD_FILE_SHA: _text_changed_body()})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "unavailable"
    assert "blob_read_failed" in result.unavailable_reason
    assert result.primary["reason"] == "blob_read_failed"


def test_current_claim_never_degrades_confirmed_and_keeps_lineage():
    primary = _primary_binding_for(_real_source_text())
    head = FakeHeadResolver({SOURCE_PATH: OLD_FILE_SHA})
    blobs = FakeBlobReader({})
    result = _service(head, blobs).evaluate(_bundle_with(primary))

    assert result.status == "current"
    assert result.evaluated_at
    assert result.primary["symbol"] == SYMBOL
    assert result.primary["path"] == SOURCE_PATH