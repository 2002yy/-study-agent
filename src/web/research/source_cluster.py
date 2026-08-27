"""Conservative candidate-source clustering before any page is read.

These clusters are proposals for scheduling diversity, not proof of source
independence.  Evidence-level independence remains owned by successfully read
and extracted evidence later in the Claim Engine pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re
from typing import Any, Mapping
from urllib.parse import urlparse

from src.news.url_normalizer import canonicalize_url
from src.web.research.candidate_pool import CandidatePoolItem

_SOURCE_ROLES = {
    "primary",
    "authoritative_secondary",
    "independent_secondary",
    "community",
    "aggregator",
}


@dataclass(frozen=True)
class CandidateSourceProfile:
    candidate_id: str
    source_role: str = ""
    origin_url: str = ""
    publisher_key: str = ""
    quoted_source_key: str = ""


@dataclass(frozen=True)
class CandidateClusterAssignment:
    candidate_id: str
    cluster_id: str
    independence_key: str
    basis: str
    source_role: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "cluster_id": self.cluster_id,
            "independence_key": self.independence_key,
            "basis": self.basis,
            "source_role": self.source_role,
        }


@dataclass(frozen=True)
class CandidateSourceCluster:
    id: str
    candidate_ids: tuple[str, ...]
    independence_key: str
    basis: str
    source_roles: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "candidate_ids": list(self.candidate_ids),
            "independence_key": self.independence_key,
            "basis": self.basis,
            "source_roles": list(self.source_roles),
        }


@dataclass(frozen=True)
class CandidateClusteringResult:
    assignments: tuple[CandidateClusterAssignment, ...]
    clusters: tuple[CandidateSourceCluster, ...]


def cluster_candidate_sources(
    candidates: tuple[CandidatePoolItem, ...],
    *,
    profiles: Mapping[str, CandidateSourceProfile] | None = None,
) -> CandidateClusteringResult:
    """Group candidates by the strongest available conservative source key."""

    profile_map = dict(profiles or {})
    candidate_ids = {item.id for item in candidates}
    unknown = set(profile_map) - candidate_ids
    if unknown:
        raise ValueError(f"source profiles reference unknown candidates: {sorted(unknown)}")
    assignments: list[CandidateClusterAssignment] = []
    members: dict[str, list[CandidateClusterAssignment]] = {}
    order: list[str] = []
    for candidate in candidates:
        profile = profile_map.get(
            candidate.id,
            CandidateSourceProfile(candidate_id=candidate.id),
        )
        if profile.candidate_id != candidate.id:
            raise ValueError("source profile candidate_id does not match mapping key")
        role = profile.source_role.strip().casefold()
        if role and role not in _SOURCE_ROLES:
            raise ValueError(f"invalid candidate source role: {role}")
        key, basis = _independence_key(candidate, profile)
        cluster_id = f"candidate_cluster_{sha256(key.encode('utf-8')).hexdigest()[:16]}"
        assignment = CandidateClusterAssignment(
            candidate_id=candidate.id,
            cluster_id=cluster_id,
            independence_key=key,
            basis=basis,
            source_role=role,
        )
        assignments.append(assignment)
        if cluster_id not in members:
            members[cluster_id] = []
            order.append(cluster_id)
        members[cluster_id].append(assignment)
    clusters = tuple(
        CandidateSourceCluster(
            id=cluster_id,
            candidate_ids=tuple(item.candidate_id for item in members[cluster_id]),
            independence_key=members[cluster_id][0].independence_key,
            basis=members[cluster_id][0].basis,
            source_roles=tuple(
                dict.fromkeys(
                    item.source_role for item in members[cluster_id] if item.source_role
                )
            ),
        )
        for cluster_id in order
    )
    return CandidateClusteringResult(assignments=tuple(assignments), clusters=clusters)


def _independence_key(
    candidate: CandidatePoolItem,
    profile: CandidateSourceProfile,
) -> tuple[str, str]:
    if profile.origin_url:
        origin = canonicalize_url(profile.origin_url)
        if not origin:
            raise ValueError("candidate origin_url must be a public HTTP(S) URL")
        return f"origin:{origin}", "origin_url"
    quoted = _slug(profile.quoted_source_key)
    if quoted:
        return f"quoted:{quoted}", "quoted_source"
    publisher = _slug(profile.publisher_key)
    if not publisher:
        publisher = (urlparse(candidate.canonical_url).hostname or "").casefold()
    if publisher:
        return f"publisher:{publisher}", "publisher"
    return f"candidate:{candidate.id}", "candidate"


def _slug(value: str) -> str:
    return re.sub(
        r"[^\w.-]+",
        "-",
        str(value or "").strip().casefold(),
        flags=re.UNICODE,
    ).strip("-")[:200]


__all__ = [
    "CandidateClusterAssignment",
    "CandidateClusteringResult",
    "CandidateSourceCluster",
    "CandidateSourceProfile",
    "cluster_candidate_sources",
]
