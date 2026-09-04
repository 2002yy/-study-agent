"""Tests for the server-owned bounded binding-row projection.

The projection is the only allowed gateway from durable ResearchRun briefs
toward the answer-claim binder model context: whitelisted fields, bounded
sequence sizes, no page bodies, no client-supplied inputs, and empty rows for
missing/malformed briefs so callers fail safe.
"""

from __future__ import annotations

from types import SimpleNamespace

from src.application.research_evidence import research_binding_rows


def _brief_run(
    *,
    rows: list[dict],
    brief: dict | None = None,
) -> SimpleNamespace:
    context = {}
    if brief is not None:
        context["claim_engine_evidence_brief"] = brief
    elif rows is not None:
        context["claim_engine_evidence_brief"] = {
            "schema_version": "research-evidence-brief-v1",
            "gate_status": "pass",
            "eligible_evidence": rows,
        }
    return SimpleNamespace(id="web_lookup_1", research_context=context)


def _eligible_row(
    evidence_id: str = "evidence_abc123",
    **extra: object,
) -> dict:
    row: dict = {
        "evidence_id": evidence_id,
        "claim_id": "claim_1",
        "relation": "supports",
        "strength": "strong",
        "source_role": "official_statement",
        "source_cluster_id": "cluster_1",
        "title": "Official release",
        "url": "https://official.example/release",
        "locator": "第四段",
        "published_at": "2026-09-01",
        "anchored_spans": ["official confirmation of the release"],
        "caveats": ["translated statement"],
        "private_internal": "must never project",
    }
    row.update(extra)
    return row


def test_projects_brief_rows_with_whitelisted_fields_only():
    run = _brief_run(rows=[_eligible_row()])
    rows = research_binding_rows(run)
    assert len(rows) == 1
    row = rows[0]
    assert row["evidence_id"] == "evidence_abc123"
    assert row["claim_id"] == "claim_1"
    assert row["relation"] == "supports"
    assert row["strength"] == "strong"
    assert row["source_role"] == "official_statement"
    assert row["source_cluster_id"] == "cluster_1"
    assert row["title"] == "Official release"
    assert row["url"] == "https://official.example/release"
    assert row["locator"] == "第四段"
    assert row["published_at"] == "2026-09-01"
    assert row["anchored_spans"] == ("official confirmation of the release",)
    assert row["caveats"] == ("translated statement",)
    assert "private_internal" not in row


def test_dedupes_by_evidence_id_and_keeps_first():
    run = _brief_run(
        rows=[
            _eligible_row("evidence_a1", title="first"),
            _eligible_row("evidence_a1", title="second"),
            _eligible_row("evidence_b2"),
        ]
    )
    rows = research_binding_rows(run)
    assert [row["evidence_id"] for row in rows] == ["evidence_a1", "evidence_b2"]
    assert rows[0]["title"] == "first"


def test_limits_row_count_and_sequence_items():
    rows = [
        _eligible_row(f"evidence_{index}", anchored_spans=[f"span {index}"] * 20)
        for index in range(60)
    ]
    projected = research_binding_rows(_brief_run(rows=rows))
    assert len(projected) == 24
    assert len(projected[0]["anchored_spans"]) == 6
    assert all(len(span) <= 300 for span in projected[0]["anchored_spans"])


def test_bounds_text_and_drops_non_scalar_fields():
    run = _brief_run(
        rows=[
            _eligible_row(
                title="x" * 5000,
                locator="a" * 5000,
                anchored_spans=["z" * 5000],
                caveats=[{"nested": "object"}],
            )
        ]
    )
    rows = research_binding_rows(run)
    assert len(rows[0]["title"]) <= 5000  # scalar text is collapsed, not raw
    assert len(rows[0]["anchored_spans"][0]) <= 300
    assert rows[0]["caveats"] == ()


def test_missing_brief_returns_empty_rows():
    run = SimpleNamespace(id="web_lookup_1", research_context={})
    assert research_binding_rows(run) == []
    no_context = SimpleNamespace(id="web_lookup_1", research_context=None)
    assert research_binding_rows(no_context) == []


def test_malformed_brief_returns_empty_rows():
    run = SimpleNamespace(
        id="web_lookup_1",
        research_context={"claim_engine_evidence_brief": "not a mapping"},
    )
    assert research_binding_rows(run) == []
    run = SimpleNamespace(
        id="web_lookup_1",
        research_context={
            "claim_engine_evidence_brief": {"eligible_evidence": "not a list"}
        },
    )
    assert research_binding_rows(run) == []


def test_non_mapping_eligible_entries_are_skipped():
    run = _brief_run(rows=[_eligible_row("evidence_a1"), {"junk": True}, {"more": 1}])
    rows = research_binding_rows(run)
    assert [row["evidence_id"] for row in rows] == ["evidence_a1"]


def test_whitespace_only_evidence_ids_are_skipped():
    run = _brief_run(rows=[_eligible_row("   "), _eligible_row("evidence_b2")])
    rows = research_binding_rows(run)
    assert [row["evidence_id"] for row in rows] == ["evidence_b2"]


def test_ignores_unwhitelisted_page_body_on_valid_support_row():
    # The row must otherwise satisfy the publication support contract; this
    # test is specifically about privacy projection, not eligibility.
    run = _brief_run(
        rows=[
            _eligible_row(
                "evidence_x1",
                title="T",
                url="https://example.com/x",
                content="full page body that must never leave",
            )
        ]
    )
    rows = research_binding_rows(run)
    assert len(rows) == 1
    assert "content" not in rows[0]
