from __future__ import annotations

from src.web.evidence_pinning import pin_evidence_refs


SNAPSHOT = {
    "commit_sha": "abc123",
    "requested_ref": "refs/heads/main",
}


def test_pin_evidence_refs_adds_identity_to_nested_evidence_payloads():
    value = {
        "sources": [
            {
                "path": "src/core.ts",
                "tree_sha": "tree1",
                "start_line": 10,
                "end_line": 20,
            }
        ]
    }

    pinned = pin_evidence_refs(value, SNAPSHOT)

    item = pinned["sources"][0]
    assert item["commit_sha"] == "abc123"
    assert item["requested_ref"] == "refs/heads/main"
    assert set(item) == {"path", "tree_sha", "start_line", "end_line", "commit_sha", "requested_ref"}


def test_pin_evidence_refs_does_not_touch_legacy_fields():
    value = {"path": "src/core.ts", "tree_sha": "tree1", "start_line": 1, "end_line": 2, "extra": "x"}

    pinned = pin_evidence_refs(value, SNAPSHOT)

    assert pinned["extra"] == "x"
    assert pinned["commit_sha"] == "abc123"


def test_pin_evidence_refs_keeps_existing_identity_fields():
    value = {"path": "p", "tree_sha": "t", "start_line": 0, "end_line": 0, "commit_sha": "keep"}

    pinned = pin_evidence_refs(value, SNAPSHOT)

    assert pinned["commit_sha"] == "keep"
    assert pinned["requested_ref"] == "refs/heads/main"


def test_pin_evidence_refs_skips_non_evidence_objects():
    value = {"metadata": {"note": "hello"}, "count": 3, "flag": True}

    pinned = pin_evidence_refs(value, SNAPSHOT)

    assert pinned == {"metadata": {"note": "hello"}, "count": 3, "flag": True}


def test_pin_evidence_refs_recurses_through_lists_and_tuples():
    value = {
        "mixed": [
            {"path": "a.py", "tree_sha": "t", "start_line": 1, "end_line": 2},
            "plain",
            None,
        ],
        "t": ("x",),
    }

    pinned = pin_evidence_refs(value, SNAPSHOT)

    assert pinned["mixed"][0]["commit_sha"] == "abc123"
    assert pinned["mixed"][1] == "plain"
    assert pinned["mixed"][2] is None
    assert pinned["t"] == ["x"]


def test_pin_evidence_refs_with_empty_snapshot_writes_empty_identity():
    pinned = pin_evidence_refs(
        {"path": "a.py", "tree_sha": "t", "start_line": 1, "end_line": 2},
        {},
    )

    assert pinned["commit_sha"] == ""
    assert pinned["requested_ref"] == ""


def test_pin_evidence_refs_requires_all_shape_keys():
    missing_end = {"path": "a.py", "tree_sha": "t", "start_line": 1}
    assert pin_evidence_refs(missing_end, SNAPSHOT) == missing_end

    missing_path = {"tree_sha": "t", "start_line": 1, "end_line": 2}
    assert pin_evidence_refs(missing_path, SNAPSHOT) == missing_path
