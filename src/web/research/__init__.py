"""Shared Research Quality Engine contracts.

The package is deliberately disconnected from runtime execution until a later
RQCE batch adds an explicit, tested adapter.
"""

from src.web.research.contracts import (
    RESEARCH_STATE_SCHEMA_VERSION,
    ClaimEvidenceRelation,
    ConflictGap,
    EvidenceCluster,
    EvidenceGap,
    EvidenceRequirement,
    ResearchBrief,
    ResearchBudget,
    ResearchClaim,
    ResearchClaimEvidenceLink,
    ResearchClaimKind,
    ResearchClaimPriority,
    ResearchClaimState,
    ResearchEvidence,
    ResearchEvidenceExtractionStatus,
    ResearchQuestion,
    ResearchState,
    ResearchTraceEvent,
    ResearchTraceEventType,
    build_research_state,
)
from src.web.research.state import (
    CLAIM_ENGINE_CONTEXT_KEY,
    ClaimEngineLoadResult,
    attach_claim_engine_state,
    load_claim_engine_state,
    new_empty_shadow_state,
)
from src.web.research.policy import (
    EvidencePolicy,
    EvidencePolicyProfile,
    SourceRole,
    evidence_policy_for_claim,
)
from src.web.research.evidence_gate import (
    EvidenceGateResult,
    EvidenceGateStatus,
    evaluate_evidence_gate,
)
from src.web.research.trace import (
    TraceAppendResult,
    append_research_trace,
    try_append_research_trace,
)
from src.web.research.stop_gate import (
    ShadowStopDecision,
    evaluate_shadow_stop,
    safe_evaluate_shadow_stop,
)

__all__ = [
    "RESEARCH_STATE_SCHEMA_VERSION",
    "ClaimEvidenceRelation",
    "ConflictGap",
    "EvidenceCluster",
    "EvidenceGap",
    "EvidenceRequirement",
    "ResearchBrief",
    "ResearchBudget",
    "ResearchClaim",
    "ResearchClaimEvidenceLink",
    "ResearchClaimKind",
    "ResearchClaimPriority",
    "ResearchClaimState",
    "ResearchEvidence",
    "ResearchEvidenceExtractionStatus",
    "ResearchQuestion",
    "ResearchState",
    "ResearchTraceEvent",
    "ResearchTraceEventType",
    "build_research_state",
    "CLAIM_ENGINE_CONTEXT_KEY",
    "ClaimEngineLoadResult",
    "attach_claim_engine_state",
    "load_claim_engine_state",
    "new_empty_shadow_state",
    "EvidencePolicy",
    "EvidencePolicyProfile",
    "SourceRole",
    "evidence_policy_for_claim",
    "EvidenceGateResult",
    "EvidenceGateStatus",
    "evaluate_evidence_gate",
    "TraceAppendResult",
    "append_research_trace",
    "try_append_research_trace",
    "ShadowStopDecision",
    "evaluate_shadow_stop",
    "safe_evaluate_shadow_stop",
]
