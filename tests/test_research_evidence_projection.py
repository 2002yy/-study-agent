from __future__ import annotations

from types import SimpleNamespace

from src.application.research_evidence import research_sources_snapshot


def test_research_source_projection_keeps_identity_and_assessment_only():
    run = SimpleNamespace(
        id="web_lookup_1",
        provider_status="partial",
        stop_reason="budget_exhausted",
        selected_sources=[
            {
                "item": {
                    "title": "Official guide",
                    "url": "https://example.com/guide",
                    "published_at": "2026-07-01",
                    "snippet": "must not persist",
                    "content": "full article must not persist",
                    "token": "secret-token",
                },
                "assessment": {
                    "source_id": "web_source_1",
                    "title": "Official guide",
                    "url": "https://example.com/guide",
                    "domain": "example.com",
                    "source_type": "web",
                    "relevance": 0.95,
                    "directness": "direct_title",
                    "freshness": "reported",
                    "selected": True,
                    "worth_reading": True,
                    "private_debug": "must not persist",
                },
            }
        ],
        rejected_sources=[
            {
                "item": {
                    "title": "Duplicate",
                    "url": "https://example.com/duplicate",
                    "description": "must not persist",
                },
                "assessment": {
                    "source_id": "web_source_2",
                    "title": "Duplicate",
                    "url": "https://example.com/duplicate",
                    "domain": "example.com",
                    "relevance": 0.4,
                    "selected": False,
                    "rejection_reason": "duplicate",
                    "duplicate_of": "web_source_1",
                },
            }
        ],
        query_attempts=[{"query": "private query trace"}],
        source_block="full source block must not persist",
    )

    snapshot = research_sources_snapshot(run)

    assert snapshot == {
        "run_id": "web_lookup_1",
        "provider_status": "partial",
        "stop_reason": "budget_exhausted",
        "selected_sources": [
            {
                "item": {
                    "title": "Official guide",
                    "url": "https://example.com/guide",
                    "published_at": "2026-07-01",
                },
                "assessment": {
                    "source_id": "web_source_1",
                    "title": "Official guide",
                    "url": "https://example.com/guide",
                    "domain": "example.com",
                    "source_type": "web",
                    "relevance": 0.95,
                    "directness": "direct_title",
                    "freshness": "reported",
                    "selected": True,
                    "worth_reading": True,
                },
            }
        ],
        "rejected_sources": [
            {
                "item": {
                    "title": "Duplicate",
                    "url": "https://example.com/duplicate",
                },
                "assessment": {
                    "source_id": "web_source_2",
                    "title": "Duplicate",
                    "url": "https://example.com/duplicate",
                    "domain": "example.com",
                    "relevance": 0.4,
                    "selected": False,
                    "rejection_reason": "duplicate",
                    "duplicate_of": "web_source_1",
                },
            }
        ],
    }

    serialized = repr(snapshot)
    assert "snippet" not in serialized
    assert "content" not in serialized
    assert "token" not in serialized
    assert "private query trace" not in serialized
    assert "full source block" not in serialized


def test_research_source_projection_drops_malformed_records():
    run = SimpleNamespace(
        id="web_lookup_2",
        provider_status="found",
        stop_reason="enough_evidence",
        selected_sources=[None, "bad", {}, {"item": {"nested": {"x": 1}}}],
        rejected_sources=[],
    )

    assert research_sources_snapshot(run)["selected_sources"] == []
