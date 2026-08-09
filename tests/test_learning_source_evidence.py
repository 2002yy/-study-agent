from __future__ import annotations

from dataclasses import asdict

from src.application.learning_source_evidence import (
    LearningSourceEvidenceService,
    SourceEvidenceCandidate,
)
from src.domain.learning_truth import SourceEvidence


COMMIT_SHA = "a" * 40
TREE_SHA = "b" * 40


def _ref(
    *,
    path: str = "src/service.py",
    symbol: str = "Service.run",
    symbol_kind: str = "method",
    start_line: int = 10,
    commit_sha: str = COMMIT_SHA,
    tree_sha: str = TREE_SHA,
    kind: str = "search_result",
) -> dict:
    return {
        "repository": "2002yy/study-agent",
        "commit_sha": commit_sha,
        "tree_sha": tree_sha,
        "path": path,
        "file_sha": f"sha:{path}",
        "symbol": symbol,
        "symbol_kind": symbol_kind,
        "start_line": start_line,
        "end_line": start_line,
        "kind": kind,
    }


def _source(
    *,
    path: str,
    symbol: str,
    start_line: int,
    commit_sha: str = COMMIT_SHA,
    tree_sha: str = TREE_SHA,
) -> SourceEvidence:
    return SourceEvidence(
        repository="2002yy/study-agent",
        commit_sha=commit_sha,
        tree_sha=tree_sha,
        path=path,
        file_sha=f"sha:{path}",
        symbol=symbol,
        symbol_kind="method",
        start_line=start_line,
        end_line=start_line,
        evidence_kind="search_result",
    )


class FakeSnapshotService:
    def __init__(self, results: list[dict]) -> None:
        self.results = results
        self.calls: list[dict] = []

    def search_repository(self, repo_url: str, query: str, **kwargs) -> dict:
        self.calls.append({"repo_url": repo_url, "query": query, **kwargs})
        return {"ok": True, "results": list(self.results)}


class FakeGraphService:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls: list[dict] = []

    def impact(self, repo_url: str, symbol: str, **kwargs) -> dict:
        self.calls.append({"repo_url": repo_url, "symbol": symbol, **kwargs})
        return dict(self.payload)


def test_normalization_whitelists_only_durable_source_identity():
    service = LearningSourceEvidenceService(FakeSnapshotService([]))  # type: ignore[arg-type]
    raw = {
        "evidence_ref": _ref(),
        "query": "service run",
        "score": 0.99,
        "rank": 1,
        "confidence": 0.88,
        "provider_status": "complete",
        "selection_reason": "top result",
        "ci_association": {"overall_status": "failure"},
    }

    candidate = service.normalize_candidates((raw,))[0]
    payload = asdict(candidate.source)

    assert payload["repository"] == "2002yy/study-agent"
    assert payload["commit_sha"] == COMMIT_SHA
    assert payload["symbol"] == "Service.run"
    assert {
        "query",
        "score",
        "rank",
        "confidence",
        "provider_status",
        "selection_reason",
        "ci_association",
    }.isdisjoint(payload)


def test_convergence_prefers_implementation_and_keeps_diverse_support():
    service = LearningSourceEvidenceService(FakeSnapshotService([]))  # type: ignore[arg-type]
    candidates = (
        SourceEvidenceCandidate(
            source=_source(path="docs/design.md", symbol="", start_line=1),
            proof_dimension="docs",
            ordinal=0,
        ),
        SourceEvidenceCandidate(
            source=_source(path="tests/test_service.py", symbol="test_run", start_line=5),
            proof_dimension="test",
            ordinal=1,
        ),
        SourceEvidenceCandidate(
            source=_source(path="src/service.py", symbol="Service.run", start_line=10),
            proof_dimension="implementation",
            ordinal=2,
        ),
        SourceEvidenceCandidate(
            source=_source(path="src/domain/contract.py", symbol="Contract", start_line=2),
            proof_dimension="contract",
            supporting_role="prerequisite",
            ordinal=3,
        ),
        SourceEvidenceCandidate(
            source=_source(path="tests/test_other.py", symbol="test_other", start_line=9),
            proof_dimension="test",
            ordinal=4,
        ),
        SourceEvidenceCandidate(
            source=_source(path="config/settings.yaml", symbol="", start_line=1),
            proof_dimension="config",
            ordinal=5,
        ),
    )

    result = service.converge(candidates)

    assert result.claim_ready is True
    assert result.primary is not None
    assert result.primary.source.path == "src/service.py"
    assert result.primary.role == "primary"
    assert len(result.supporting) == 4
    assert [item.source.path for item in result.supporting] == [
        "src/domain/contract.py",
        "tests/test_service.py",
        "config/settings.yaml",
        "docs/design.md",
    ]
    assert result.supporting[0].role == "supporting_prerequisite"
    assert sum(item.source.path.startswith("tests/") for item in result.supporting) == 1


def test_convergence_deduplicates_exact_identity_and_rejects_mixed_commit_support():
    service = LearningSourceEvidenceService(FakeSnapshotService([]))  # type: ignore[arg-type]
    primary = SourceEvidenceCandidate(
        source=_source(path="src/service.py", symbol="Service.run", start_line=10),
        proof_dimension="implementation",
        ordinal=0,
    )
    duplicate = SourceEvidenceCandidate(
        source=primary.source,
        proof_dimension="implementation",
        origin="one_hop",
        ordinal=1,
    )
    wrong_commit = SourceEvidenceCandidate(
        source=_source(
            path="src/domain/contract.py",
            symbol="Contract",
            start_line=2,
            commit_sha="c" * 40,
        ),
        proof_dimension="contract",
        ordinal=2,
    )
    valid_test = SourceEvidenceCandidate(
        source=_source(path="tests/test_service.py", symbol="test_run", start_line=4),
        proof_dimension="test",
        ordinal=3,
    )

    result = service.converge((primary, duplicate, wrong_commit, valid_test))

    assert result.primary is not None
    assert result.primary.source == primary.source
    assert [item.source.path for item in result.supporting] == ["tests/test_service.py"]
    assert all(item.source.commit_sha == COMMIT_SHA for item in result.bindings)


def test_no_valid_source_never_becomes_claim_ready():
    service = LearningSourceEvidenceService(FakeSnapshotService([]))  # type: ignore[arg-type]

    normalized = service.normalize_candidates(
        (
            {"evidence_ref": {"path": "src/service.py", "start_line": 1, "end_line": 1}},
            {"score": 1.0},
        )
    )
    result = service.converge(normalized)

    assert normalized == ()
    assert result.claim_ready is False
    assert result.primary is None
    assert result.bindings == ()
    assert result.unresolved_reason == "missing_source"


def test_search_and_converge_uses_exact_commit_and_one_hop_only():
    direct_primary = {"evidence_ref": _ref()}
    direct_docs = {
        "evidence_ref": _ref(path="docs/source.md", symbol="", start_line=3)
    }
    snapshot = FakeSnapshotService([direct_docs, direct_primary])
    graph = FakeGraphService(
        {
            "resolution": {"selected": {"evidence": _ref()}},
            "edges": [
                {
                    "kind": "reference",
                    "evidence": _ref(
                        path="tests/test_service.py",
                        symbol="test_run",
                        start_line=7,
                        kind="reference",
                    ),
                },
                {
                    "kind": "import",
                    "evidence": _ref(
                        path="src/domain/contract.py",
                        symbol="Contract",
                        start_line=2,
                        kind="definition",
                    ),
                },
            ],
        }
    )
    service = LearningSourceEvidenceService(  # type: ignore[arg-type]
        snapshot,
        graph,  # type: ignore[arg-type]
    )

    result = service.search_and_converge(
        "https://github.com/2002yy/study-agent",
        "service run",
        ref="main",
    )

    assert snapshot.calls == [
        {
            "repo_url": "https://github.com/2002yy/study-agent",
            "query": "service run",
            "ref": "main",
            "top_k": 12,
            "include_ci": False,
        }
    ]
    assert graph.calls == [
        {
            "repo_url": "https://github.com/2002yy/study-agent",
            "symbol": "Service.run",
            "ref": COMMIT_SHA,
            "depth": 1,
            "max_files": 12,
            "max_edges": 40,
        }
    ]
    assert result.one_hop_explored is True
    assert result.primary is not None
    assert result.primary.source.path == "src/service.py"
    assert {item.source.path for item in result.supporting} == {
        "src/domain/contract.py",
        "tests/test_service.py",
        "docs/source.md",
    }


def test_search_without_symbol_does_not_expand_graph():
    snapshot = FakeSnapshotService(
        [{"evidence_ref": _ref(path="docs/decision.md", symbol="", symbol_kind="", start_line=1)}]
    )
    graph = FakeGraphService({"unexpected": True})
    service = LearningSourceEvidenceService(  # type: ignore[arg-type]
        snapshot,
        graph,  # type: ignore[arg-type]
    )

    result = service.search_and_converge(
        "https://github.com/2002yy/study-agent",
        "decision",
    )

    assert result.claim_ready is True
    assert result.one_hop_explored is False
    assert graph.calls == []
