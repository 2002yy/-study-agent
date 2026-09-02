import { describe, expect, it } from "vitest";
import {
  KNOWN_RESEARCH_STOP_REASONS,
  RESEARCH_STOP_REASON_LABELS,
  researchStopReasonDisplay,
} from "./researchStopReason";

const EXPECTED_CANONICAL_REASONS = [
  "evidence_gate_pass",
  "evidence_budget_exhausted",
  "evidence_gap_open",
  "evidence_saturated",
  "wave_limit_exhausted",
  "claim_planning_blocked_by_policy",
  "claim_plan_unavailable",
  "active_runtime_unavailable",
  "user_cancelled",
  "providers_failed",
  "providers_returned_no_results",
  "direct_results_found",
  "read_backed_tool_evidence_found",
  "search_candidates_only",
  "empty",
  "candidates_only",
  "chat_tool_loop_failed",
  "research_stage_failed",
  "legacy_run_interrupted",
] as const;

describe("research stop reason display contract", () => {
  it("maps every frozen canonical reason to non-technical product copy", () => {
    expect(KNOWN_RESEARCH_STOP_REASONS).toEqual(EXPECTED_CANONICAL_REASONS);
    for (const reason of EXPECTED_CANONICAL_REASONS) {
      expect(RESEARCH_STOP_REASON_LABELS[reason]).toBeTruthy();
      expect(RESEARCH_STOP_REASON_LABELS[reason]).not.toBe(reason);
    }
  });

  it("never echoes an unknown future or legacy reason to the learner", () => {
    const unknown = "future_provider_specific_stop_reason";
    expect(researchStopReasonDisplay(unknown, "安全回退")).toBe("安全回退");
    expect(researchStopReasonDisplay(unknown)).not.toContain(unknown);
  });

  it("uses the caller fallback for an empty non-terminal reason", () => {
    expect(researchStopReasonDisplay("", "尚未结束")).toBe("尚未结束");
  });
});
