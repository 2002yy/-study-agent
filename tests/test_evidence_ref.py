from __future__ import annotations

from src.evidence.evidence_ref import (
    EvidenceRef,
    dedupe_evidence,
    filter_placeholders,
    normalize_evidence,
    normalize_rag_results,
    normalize_web_calls,
)


def test_normalize_rag_results_into_local_refs():
    refs = normalize_rag_results(
        [
            {"title": "Doc A", "source_path": "a.md", "score": 0.8},
            {"title": "Doc B", "source_path": "b.md", "score": 0.0},
        ]
    )
    assert [r.type for r in refs] == ["local", "local"]
    assert refs[0].source == "a.md"
    assert refs[0].score == 0.8
    assert refs[0].status == "candidate"


def test_normalize_web_calls_split_search_and_read():
    refs = normalize_web_calls(
        [
            {
                "name": "web_search",
                "arguments": {"query": "FastAPI"},
                "result": {
                    "results": [
                        {"title": "FastAPI", "url": "https://fastapi.tiangolo.com"},
                        {"title": "", "url": ""},
                    ]
                },
            },
            {
                "name": "web_read",
                "arguments": {"url": "https://example.com/x"},
                "result": {"ok": "true", "content": "page"},
            },
        ]
    )
    types = [r.type for r in refs]
    assert "web_search" in types
    assert "web_read" in types
    read_ref = next(r for r in refs if r.type == "web_read")
    assert read_ref.url == "https://example.com/x"
    assert read_ref.status == "read"
    # empty title+url search result is filtered out
    assert not any(r.url == "" for r in refs)


def test_dedupe_keeps_selected_and_highest_score():
    refs = [
        EvidenceRef(id="u1", type="web_search", title="A", url="https://a.com", score=0.3, status="candidate"),
        EvidenceRef(id="u2", type="web_search", title="A", url="https://a.com", score=0.5, status="selected"),
        EvidenceRef(id="u3", type="web_search", title="B", url="https://b.com", score=0.9, status="candidate"),
    ]
    deduped = dedupe_evidence(refs)
    assert len(deduped) == 2
    a = next(r for r in deduped if r.url == "https://a.com")
    assert a.status == "selected"
    assert a.score == 0.5


def test_filter_placeholders_drops_empty_and_zero_score_local():
    refs = [
        EvidenceRef(id="x", type="local", title="", source="", url="", score=0.0, status="candidate"),
        EvidenceRef(id="y", type="local", title="Doc", source="y.md", url="", score=0.0, status="candidate"),
        EvidenceRef(id="z", type="web_search", title="Z", url="https://z.com", score=0.0, status="candidate"),
    ]
    kept = filter_placeholders(refs)
    kept_ids = {r.id for r in kept}
    assert "x" not in kept_ids  # empty title+url
    assert "y" not in kept_ids  # zero-score local
    assert "z" in kept_ids  # web with url kept even at score 0


def test_normalize_evidence_combines_and_dedupes_across_sources():
    refs = normalize_evidence(
        rag_results=[{"title": "Doc A", "source_path": "a.md", "score": 0.8}],
        web_calls=[
            {
                "name": "web_search",
                "arguments": {"query": "q"},
                "result": {
                    "results": [
                        {"title": "A", "url": "https://a.com"},
                        {"title": "A", "url": "https://a.com"},  # duplicate
                    ]
                },
            }
        ],
        research_selected=[{"source_id": "s1", "type": "web", "citation": "https://a.com", "title": "A"}],
        research_rejected=[{"source_id": "s2", "type": "web", "citation": "https://rejected.com", "title": "R"}],
    )
    by_url = {r.url: r for r in refs if r.url}
    # https://a.com appears in web_search (candidate) and research (selected) -> deduped to selected
    assert by_url["https://a.com"].status == "selected"
    assert by_url["https://a.com"].type in {"web_search", "research"}
    assert by_url["https://rejected.com"].status == "rejected"
    # local citation present
    assert any(r.type == "local" and r.source == "a.md" for r in refs)
