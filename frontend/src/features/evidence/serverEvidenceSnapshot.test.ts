import { describe, expect, it } from "vitest";

import { evidenceFromSessionTurns, normalizeEvidence } from "./evidenceHelpers";
import type { ChatResponse } from "../../types";

const baseRag: ChatResponse["rag"] = {
  status: "found",
  query: "evidence",
  retrieval_mode: "hybrid",
  reason: "",
  context: "",
  sources: "",
  result_count: 1,
  results: [
    {
      chunk: {
        chunk_id: "raw-chunk",
        title: "Raw fallback",
        source_path: "raw.md",
      },
      score: 0.9,
    },
  ],
  debug: {},
  attempts: [],
  rewritten_query: "",
};

function ragWithServerSnapshot(): ChatResponse["rag"] {
  return {
    ...baseRag,
    evidence_snapshot: {
      schema_version: "evidence-snapshot-v1",
      disclosure_policy: "single_evidence_unit",
      refs: [
        {
          id: "server-chunk",
          type: "local",
          title: "Server truth",
          source: "server.md",
          url: "",
          domain: "",
          published_at: "",
          score: 0.82,
          lifecycle_status: "selected",
          provider_status: "found",
          selection_reason: "disclosure_policy:single_evidence_unit",
          rejection_reason: "",
        },
        {
          id: "web-rejected",
          type: "research",
          title: "Rejected source",
          source: "web_source_2",
          url: "https://example.com/rejected",
          domain: "example.com",
          published_at: "2026-07-01",
          score: 0.4,
          lifecycle_status: "rejected",
          provider_status: "found",
          selection_reason: "",
          rejection_reason: "duplicate",
        },
      ],
      claim_links: [],
    },
  } as ChatResponse["rag"];
}

describe("server evidence snapshot dual-read", () => {
  it("prefers the versioned server snapshot over conflicting raw RAG fields", () => {
    const refs = normalizeEvidence({ rag: ragWithServerSnapshot() });

    expect(refs.map((ref) => ref.id)).toEqual(["server-chunk", "web-rejected"]);
    expect(refs[0]).toMatchObject({
      status: "selected",
      title: "Server truth",
      selectionReason: "disclosure_policy:single_evidence_unit",
      providerStatus: "found",
    });
    expect(refs[1]).toMatchObject({
      status: "rejected",
      rejectionReason: "duplicate",
      publishedAt: "2026-07-01",
    });
  });

  it("treats a valid empty server snapshot as authoritative", () => {
    const rag = {
      ...baseRag,
      evidence_snapshot: {
        schema_version: "evidence-snapshot-v1",
        disclosure_policy: "none",
        refs: [],
        claim_links: [],
      },
    } as ChatResponse["rag"];

    expect(normalizeEvidence({ rag })).toEqual([]);
  });

  it("restores the same server lifecycle truth from a persisted turn", () => {
    const rag = ragWithServerSnapshot();
    const restored = evidenceFromSessionTurns([
      {
        turn_id: "turn-1",
        rag_snapshot: rag as unknown as Record<string, unknown>,
        pedagogy_snapshot: {
          mode: "socratic",
          phase: "scaffold",
          move: "give_hint",
          disclosure_level: 1,
          evidence_ids: ["server-chunk"],
        },
      },
    ]).get("turn-1");

    expect(restored).toBeDefined();
    expect(normalizeEvidence(restored!)).toEqual(normalizeEvidence({ rag }));
  });
});
