from __future__ import annotations

from src.domain.evidence import build_evidence_snapshot


def test_legacy_ordinal_web_unit_does_not_invent_selected_url_identity():
    snapshot = build_evidence_snapshot(
        rag={
            "web_tools": {
                "calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "FastAPI"},
                        "result": {
                            "results": [
                                {
                                    "title": "FastAPI docs",
                                    "url": "https://fastapi.tiangolo.com/",
                                }
                            ]
                        },
                    }
                ]
            }
        },
        disclosed_units=(
            {
                "source_id": "web-1",
                "type": "search_excerpt",
                "content": "legacy context block",
                "citation": "web:1",
                "disclosure_role": "external_fact",
                "reliability": 0.72,
            },
        ),
        disclosure_policy="single_evidence_unit",
    )

    assert len(snapshot.refs) == 1
    assert snapshot.refs[0].url == "https://fastapi.tiangolo.com/"
    assert snapshot.refs[0].lifecycle_status == "candidate"
    assert all(ref.id != "web-1" for ref in snapshot.refs)


def test_research_source_assessment_can_authoritatively_select_same_url():
    snapshot = build_evidence_snapshot(
        rag={
            "web_tools": {
                "calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "FastAPI"},
                        "result": {
                            "results": [
                                {
                                    "title": "FastAPI docs",
                                    "url": "https://fastapi.tiangolo.com/",
                                }
                            ]
                        },
                    }
                ]
            },
            "research_sources": {
                "run_id": "research-1",
                "provider_status": "found",
                "source_truth_version": 2,
                "selected_sources": [
                    {
                        "item": {
                            "title": "FastAPI docs",
                            "url": "https://fastapi.tiangolo.com",
                        },
                        "assessment": {
                            "source_id": "web_source_1",
                            "title": "FastAPI docs",
                            "url": "https://fastapi.tiangolo.com",
                            "domain": "fastapi.tiangolo.com",
                            "relevance": 1.0,
                        },
                        "read_status": "read",
                    }
                ],
                "rejected_sources": [],
            },
        }
    )

    assert len(snapshot.refs) == 1
    assert snapshot.refs[0].lifecycle_status == "selected"
    assert snapshot.refs[0].selection_reason == "research_run:research-1"
