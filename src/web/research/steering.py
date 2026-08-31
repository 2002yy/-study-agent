"""Durable helpers for Claim Engine active steering.

Steering remains metadata inside the owning ``WebLookupRun``.  This module
only owns its bounded append/merge envelope; mapping a pending entry into the
research claim graph stays in the active runtime executor.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ACTIVE_RESEARCH_STEERING_KEY = "claim_engine_steering"
ACTIVE_RESEARCH_STEERING_STATUSES = frozenset({"pending", "applied", "late"})


def is_active_claim_engine_context(context: Mapping[str, Any]) -> bool:
    claim_engine = context.get("claim_engine")
    return isinstance(claim_engine, Mapping) and claim_engine.get("mode") == "active"


def active_steering_entries(context: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return copied, server-shaped entries without accepting anonymous data."""

    raw = context.get(ACTIVE_RESEARCH_STEERING_KEY)
    if not isinstance(raw, list):
        return []
    return [
        dict(item)
        for item in raw
        if isinstance(item, Mapping)
        and isinstance(item.get("id"), str)
        and bool(item["id"])
        and item.get("status") in ACTIVE_RESEARCH_STEERING_STATUSES
    ]


def append_active_steering(
    context: Mapping[str, Any],
    *,
    entry_id: str,
    content: str,
    received_at: str,
) -> dict[str, Any]:
    """Append one pending entry with a server-owned identity."""

    updated = dict(context)
    entries = active_steering_entries(context)
    if any(item["id"] == entry_id for item in entries):
        return updated
    entries.append(
        {
            "id": entry_id,
            "content": content,
            "received_at": received_at,
            "status": "pending",
            "applied_wave": None,
            "applied_at": None,
            "claim_id": "",
            "gap_id": "",
            "late_reason": "",
        }
    )
    updated[ACTIVE_RESEARCH_STEERING_KEY] = entries
    return updated


def merge_active_steering_context(
    incoming: Mapping[str, Any],
    durable: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge concurrent append-only entries by server-owned ID.

    The executor's incoming copy wins for an existing ID because it may have
    advanced that entry from pending to applied/late.  Durable-only IDs were
    received concurrently and must survive the checkpoint.
    """

    updated = dict(incoming)
    incoming_entries = active_steering_entries(incoming)
    durable_entries = active_steering_entries(durable)
    if not incoming_entries and not durable_entries:
        return updated

    merged: dict[str, dict[str, Any]] = {
        str(item["id"]): item for item in durable_entries
    }
    for item in incoming_entries:
        merged[str(item["id"])] = item
    updated[ACTIVE_RESEARCH_STEERING_KEY] = sorted(
        merged.values(),
        key=lambda item: (str(item.get("received_at") or ""), str(item["id"])),
    )
    return updated
