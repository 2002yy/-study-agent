from __future__ import annotations

from src.domain.evidence import (
    EVIDENCE_SNAPSHOT_SCHEMA_VERSION,
    ClaimEvidenceLinkV1,
    build_evidence_snapshot,
)


def test_local_evidence_uses_chunk_identity_and_disclosure_status():
    snapshot = build_evidence_snapshot(
        rag={
            "status": "found",
            "results": [
                {
                    "chunk": {
                        "chunk_id": "chunk-1",
                        "title": "TaskContract",
                        "source_path": "docs/task_contract.md",
                        "start_line": 10,
                        "end_line": 20,
                        "text": "contract text",
                    },
                    "score": 0.82,
                },
                {
                    "chunk": {
                        "chunk_id": "chunk-2",
                        "title": "TaskContract",
                        "source_path": "docs/task_contract.md",
                        "start_line": 30,
                        "end_line": 40,
                        "text": "more contract text",
                    },
                    "score": 0.71,
                },
            ],
        },
        disclosed_units=(
            {
                "source_id": "chunk-1",
                "type": "document_chunk",
                "content": "contract text",
                "citation": "docs/task_contract.md:L10-L20",
                "disclosure_role": "supporting_material",
                "reliability": 0.9,
            },
        ),
        disclosure_policy="single_evidence_unit",
    )

    assert snapshot.schema_version == EVIDENCE_SNAPSHOT_SCHEMA_VERSION
    assert [ref.id for ref in snapshot.refs] == ["chunk-1", "chunk-2"]
    assert snapshot.refs[0].lifecycle_status == "selected"
    assert snapshot.refs[0].selection_reason == (
        "disclosure_policy:single_evidence_unit"
    )
    assert snapshot.refs[1].lifecycle_status == "candidate"


def test_web_search_and_read_share_one_stable_ref_and_read_wins():
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
                    },
                    {
                        "name": "web_read",
                        "arguments": {"url": "https://fastapi.tiangolo.com"},
                        "result": {"ok": True, "title": "FastAPI docs"},
                    },
                ]
            }
        }
    )

    assert len(snapshot.refs) == 1
    ref = snapshot.refs[0]
    assert ref.type == "web_read"
    assert ref.lifecycle_status == "read"
    assert ref.provider_status == "read"
    assert ref.domain == "fastapi.tiangolo.com"


def test_answer_used_read_is_selected_but_candidate_only_search_is_not_failed():
    selected = build_evidence_snapshot(
        rag={
            "web_tools": {
                "used_sources": [{"url": "https://example.com/read"}],
                "calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "example"},
                        "result": {
                            "results": [
                                {
                                    "title": "Example",
                                    "url": "https://example.com/read",
                                }
                            ]
                        },
                    },
                    {
                        "name": "web_read",
                        "arguments": {"url": "https://example.com/read"},
                        "result": {"ok": True, "title": "Example"},
                    },
                ],
            }
        }
    )
    candidate = build_evidence_snapshot(
        rag={
            "web_tools": {
                "evidence_status": "candidate_only",
                "error": "尚未读取正文",
                "calls": [
                    {
                        "name": "web_search",
                        "arguments": {"query": "example"},
                        "result": {
                            "results": [
                                {
                                    "title": "Candidate",
                                    "url": "https://example.com/candidate",
                                }
                            ]
                        },
                    }
                ],
            }
        }
    )

    assert selected.refs[0].lifecycle_status == "selected"
    assert selected.refs[0].selection_reason == "web_read_sent_to_answer"
    assert candidate.refs[0].lifecycle_status == "candidate"
    assert candidate.refs[0].provider_status == "candidate_only"


def test_research_run_preserves_selected_and_rejected_assessments():
    snapshot = build_evidence_snapshot(
        rag={
            "research_sources": {
                "run_id": "web_lookup_1",
                "provider_status": "found",
                "source_truth_version": 2,
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
                            "relevance": 0.95,
                        },
                        "read_status": "read",
                    }
                ],
                "rejected_sources": [
                    {
                        "item": {
                            "title": "Duplicate guide",
                            "url": "https://example.com/duplicate",
                        },
                        "assessment": {
                            "source_id": "web_source_2",
                            "title": "Duplicate guide",
                            "url": "https://example.com/duplicate",
                            "domain": "example.com",
                            "relevance": 0.4,
                            "rejection_reason": "duplicate",
                        },
                    }
                ],
            }
        }
    )

    assert [ref.lifecycle_status for ref in snapshot.refs] == [
        "selected",
        "rejected",
    ]
    assert snapshot.refs[0].selection_reason == "research_run:web_lookup_1"
    assert snapshot.refs[0].published_at == "2026-07-01"
    assert snapshot.refs[1].rejection_reason == "duplicate"


def test_legacy_selected_source_without_read_truth_is_derived_as_unknown_candidate():
    snapshot = build_evidence_snapshot(
        rag={
            "research_sources": {
                "run_id": "legacy-run",
                "provider_status": "found",
                "selected_sources": [
                    {
                        "item": {
                            "title": "Legacy search result",
                            "url": "https://example.com/legacy",
                        },
                        "assessment": {
                            "title": "Legacy search result",
                            "url": "https://example.com/legacy",
                        },
                    }
                ],
                "rejected_sources": [],
            }
        }
    )

    assert len(snapshot.refs) == 1
    assert snapshot.refs[0].lifecycle_status == "candidate"
    assert snapshot.refs[0].provider_status == "legacy_unknown"
    assert snapshot.refs[0].selection_reason == ""


def test_pedagogy_evidence_ids_remain_distinct_from_claim_links():
    rag = {
        "status": "found",
        "results": [
            {
                "chunk": {
                    "chunk_id": "chunk-1",
                    "title": "Evidence",
                    "source_path": "evidence.md",
                    "text": "supported",
                },
                "score": 0.9,
            }
        ],
    }

    snapshot = build_evidence_snapshot(
        rag=rag,
        pedagogy_evidence_ids=("chunk-1", "unknown-evidence"),
    )

    assert snapshot.pedagogy_evidence_ids == ("chunk-1",)
    assert snapshot.claim_links == ()


def test_claim_links_require_real_claim_ids_and_known_evidence():
    snapshot = build_evidence_snapshot(
        rag={
            "status": "found",
            "results": [
                {
                    "chunk": {
                        "chunk_id": "chunk-1",
                        "title": "Evidence",
                        "source_path": "evidence.md",
                        "text": "supported",
                    },
                    "score": 0.9,
                }
            ],
        },
        claim_links=(
            ClaimEvidenceLinkV1(
                claim_id="claim-1",
                evidence_id="chunk-1",
                support_type="direct_support",
                confidence=0.95,
            ),
            ClaimEvidenceLinkV1(
                claim_id="claim-2",
                evidence_id="unknown-evidence",
                support_type="direct_support",
                confidence=0.8,
            ),
            ClaimEvidenceLinkV1(
                claim_id="",
                evidence_id="chunk-1",
                support_type="direct_support",
                confidence=0.8,
            ),
        ),
    )

    assert [link.to_dict() for link in snapshot.claim_links] == [
        {
            "claim_id": "claim-1",
            "evidence_id": "chunk-1",
            "support_type": "direct_support",
            "confidence": 0.95,
        }
    ]


def test_snapshot_does_not_invent_claim_links_or_rejections():
    snapshot = build_evidence_snapshot(
        rag={
            "status": "found",
            "results": [
                {
                    "chunk": {
                        "chunk_id": "chunk-1",
                        "title": "Evidence",
                        "source_path": "evidence.md",
                        "text": "supported",
                    },
                    "score": 0.9,
                }
            ],
        }
    )

    assert snapshot.claim_links == ()
    assert snapshot.refs[0].lifecycle_status == "candidate"
    assert snapshot.refs[0].rejection_reason == ""
