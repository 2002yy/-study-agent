"""Unified EvidenceRef model and normalizers (G13).

Normalizes evidence from RAG citations, model-directed web tools, and research
runs into a single EvidenceRef list with type/score/status, deduped and filtered
so placeholders/empty/zero-score local refs do not pollute the trail.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal
from urllib.parse import urlparse

EvidenceType = Literal["local", "web_search", "web_read", "research"]
EvidenceStatus = Literal["candidate", "read", "selected", "rejected"]

_STATUS_PRIORITY = {"selected": 0, "read": 1, "rejected": 2, "candidate": 3}


@dataclass(frozen=True)
class EvidenceRef:
    id: str
    type: EvidenceType
    title: str = ""
    source: str = ""
    domain: str = ""
    url: str = ""
    published_at: str = ""
    score: float = 0.0
    status: EvidenceStatus = "candidate"
    raw: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)


def _domain_of(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except Exception:
        return ""


def _ref_id(url: str, source: str, title: str) -> str:
    return url or source or title or ""


def normalize_rag_results(results: list[dict[str, Any]] | None) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for item in results or []:
        title = str(item.get("title") or item.get("source_path") or "")
        source = str(item.get("source_path") or item.get("source") or "")
        score = float(item.get("score") or 0.0)
        refs.append(
            EvidenceRef(
                id=_ref_id("", source, title),
                type="local",
                title=title,
                source=source,
                score=score,
                status="candidate",
                raw=item,
            )
        )
    return refs


def normalize_web_calls(calls: list[dict[str, Any]] | None) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for call in calls or []:
        name = str(call.get("name") or "")
        arguments = call.get("arguments") or {}
        result = call.get("result") or {}
        if name == "web_search":
            raw_results = result.get("results")
            results = raw_results if isinstance(raw_results, list) else []
            for r in results:
                title = str(r.get("title") or "")
                url = str(r.get("url") or "")
                if not title and not url:
                    continue
                refs.append(
                    EvidenceRef(
                        id=_ref_id(url, "", title),
                        type="web_search",
                        title=title,
                        url=url,
                        domain=_domain_of(url),
                        status="candidate",
                        raw=r,
                    )
                )
        elif name == "web_read":
            url = str(arguments.get("url") or result.get("url") or "")
            if not url:
                continue
            refs.append(
                EvidenceRef(
                    id=url,
                    type="web_read",
                    title=url,
                    url=url,
                    domain=_domain_of(url),
                    status="read",
                    raw=result,
                )
            )
    return refs


def normalize_research_sources(
    selected: list[dict[str, Any]] | None,
    rejected: list[dict[str, Any]] | None,
) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    for item in selected or []:
        url = str(item.get("citation") or item.get("url") or "")
        title = str(item.get("title") or item.get("citation") or "")
        refs.append(
            EvidenceRef(
                id=_ref_id(url, item.get("source_id", ""), title),
                type="research",
                title=title,
                source=str(item.get("source_id") or ""),
                url=url,
                domain=_domain_of(url),
                status="selected",
                raw=item,
            )
        )
    for item in rejected or []:
        url = str(item.get("citation") or item.get("url") or "")
        title = str(item.get("title") or item.get("citation") or "")
        refs.append(
            EvidenceRef(
                id=_ref_id(url, item.get("source_id", ""), title),
                type="research",
                title=title,
                source=str(item.get("source_id") or ""),
                url=url,
                domain=_domain_of(url),
                status="rejected",
                raw=item,
            )
        )
    return refs


def _dedupe_key(ref: EvidenceRef) -> str:
    if ref.url:
        return f"url:{ref.url}"
    if ref.source:
        return f"src:{ref.type}:{ref.source}"
    return f"title:{ref.type}:{ref.title}"


def dedupe_evidence(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    best: dict[str, EvidenceRef] = {}
    for ref in refs:
        key = _dedupe_key(ref)
        existing = best.get(key)
        if existing is None:
            best[key] = ref
            continue
        if _STATUS_PRIORITY[ref.status] < _STATUS_PRIORITY[existing.status]:
            best[key] = ref
        elif (
            _STATUS_PRIORITY[ref.status] == _STATUS_PRIORITY[existing.status]
            and ref.score > existing.score
        ):
            best[key] = ref
    return list(best.values())


def filter_placeholders(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    kept: list[EvidenceRef] = []
    for ref in refs:
        if not ref.title and not ref.url and not ref.source:
            continue
        if ref.type == "local" and ref.score <= 0.0:
            continue
        kept.append(ref)
    return kept


def normalize_evidence(
    *,
    rag_results: list[dict[str, Any]] | None = None,
    web_calls: list[dict[str, Any]] | None = None,
    research_selected: list[dict[str, Any]] | None = None,
    research_rejected: list[dict[str, Any]] | None = None,
) -> list[EvidenceRef]:
    refs: list[EvidenceRef] = []
    refs.extend(normalize_rag_results(rag_results))
    refs.extend(normalize_web_calls(web_calls))
    refs.extend(normalize_research_sources(research_selected, research_rejected))
    refs = filter_placeholders(refs)
    return dedupe_evidence(refs)
