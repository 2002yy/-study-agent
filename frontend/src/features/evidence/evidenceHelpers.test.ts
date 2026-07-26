import { describe, expect, it } from "vitest";
import {
  buildCitations,
  evidenceFromResponse,
  evidenceSummary,
  evidenceFromSessionTurns,
  normalizeEvidence,
  summarizeWebCalls,
} from "./evidenceHelpers";
import type { ChatResponse } from "../../types";

const baseRag: ChatResponse["rag"] = {
  status: "ok",
  query: "q",
  retrieval_mode: "hybrid",
  reason: "",
  context: "",
  sources: "",
  result_count: 1,
  results: [],
  debug: {},
  attempts: [],
  rewritten_query: "",
};

const nestedLocalResult = {
  chunk: {
    chunk_id: "chunk-1",
    title: "Doc A",
    source_path: "docs/a.md",
    start_line: 10,
    end_line: 20,
  },
  score: 0.8,
};

describe("evidenceHelpers", () => {
  it("summarizes valid web_search and web_read calls", () => {
    const calls = summarizeWebCalls([
      {
        name: "web_search",
        arguments: { query: "FastAPI" },
        result: { results: [{ title: "t", url: "u" }, { title: "", url: "" }] },
      },
      {
        name: "web_read",
        arguments: { url: "https://x.com" },
        result: { ok: "true", content: "page".repeat(200) },
      },
    ]);
    expect(calls.searches).toEqual([{ query: "FastAPI", results: [{ title: "t", url: "u", snippet: undefined }] }]);
    expect(calls.reads[0].url).toBe("https://x.com");
    expect(calls.reads[0].ok).toBe(true);
    expect(calls.reads[0].preview.length).toBeLessThanOrEqual(300);
  });

  it("builds citations from the actual nested RagResult chunk shape", () => {
    const cites = buildCitations({
      ...baseRag,
      results: [nestedLocalResult],
    });
    expect(cites).toEqual([{ title: "Doc A", source: "docs/a.md", score: 0.8 }]);
  });

  it("filters empty, zero-score and duplicate citation placeholders", () => {
    const cites = buildCitations({
      ...baseRag,
      results: [
        { chunk: {}, score: 0 },
        { chunk: { title: "", source_path: "" }, score: 0.5 },
        { chunk: { source_path: "docs/a.md" }, score: 0.7 },
        { chunk: { source_path: "docs/a.md" }, score: 0.6 },
      ],
    });
    expect(cites).toEqual([{ title: "a.md", source: "docs/a.md", score: 0.7 }]);
  });

  it("builds evidence from a ChatResponse", () => {
    const resp: ChatResponse = {
      reply: "r",
      session_id: "s",
      turn_id: "t1",
      route: { mode: "socratic" },
      rag: baseRag,
      pedagogy: { mode: "socratic", phase: "scaffold", move: "give_hint", disclosure_level: 2 },
    };
    const ev = evidenceFromResponse(resp);
    expect(ev.pedagogy?.move).toBe("give_hint");
    expect(ev.rag).toBe(baseRag);
    expect(ev.route).toEqual({ mode: "socratic" });
  });

  it("maps session turns to evidence by turnId (pedagogy + route + rag)", () => {
    const map = evidenceFromSessionTurns([
      {
        turn_id: "t1",
        pedagogy_snapshot: { mode: "socratic", move: "give_hint", phase: "scaffold", disclosure_level: 1 },
        route_snapshot: { mode: "socratic", role: "nahida" },
        rag_snapshot: { status: "ok", results: [nestedLocalResult], web_tools: { used: true } },
      },
      {
        turn_id: "t2",
        pedagogy_snapshot: { mode: "feynman_diagnosis", move: "diagnose", phase: "diagnose", disclosure_level: 2 },
      },
    ]);
    expect(map.get("t1")?.pedagogy?.move).toBe("give_hint");
    expect(map.get("t1")?.route).toEqual({ mode: "socratic", role: "nahida" });
    expect(map.get("t1")?.rag?.results).toEqual([nestedLocalResult]);
    expect(map.get("t2")?.rag).toBeUndefined();
    expect(map.get("t2")?.pedagogy?.move).toBe("diagnose");
  });

  it("normalizes production nested local results and uses chunk_id as evidence identity", () => {
    const refs = normalizeEvidence({
      rag: {
        ...baseRag,
        results: [nestedLocalResult],
      },
    });

    expect(refs).toEqual([
      {
        id: "chunk-1",
        type: "local",
        title: "Doc A",
        source: "docs/a.md",
        domain: "",
        url: "",
        score: 0.8,
        status: "candidate",
      },
    ]);
  });

  it("unifies local + web refs with dedupe and filter", () => {
    const refs = normalizeEvidence({
      rag: {
        ...baseRag,
        results: [
          nestedLocalResult,
          { chunk: { chunk_id: "empty", title: "", source_path: "" }, score: 0 },
        ],
        web_tools: {
          enabled: true,
          used: true,
          calls: [
            {
              name: "web_search",
              arguments: { query: "q" },
              result: {
                results: [
                  { title: "Web A", url: "https://a.com" },
                  { title: "Web A", url: "https://a.com" },
                  { title: "", url: "" },
                ],
              },
            },
            {
              name: "web_read",
              arguments: { url: "https://b.com" },
              result: { ok: "true", content: "page" },
            },
          ],
          error: "",
        },
      },
    });
    const types = refs.map((r) => r.type);
    expect(types).toContain("local");
    expect(types).toContain("web_search");
    expect(types).toContain("web_read");
    expect(refs.filter((r) => r.url === "https://a.com")).toHaveLength(1);
    expect(refs).toHaveLength(3);
  });

  it("preserves evidence ids and normalized refs across live response and restored session", () => {
    const response: ChatResponse = {
      reply: "grounded answer",
      session_id: "session-1",
      turn_id: "turn-1",
      route: { mode: "socratic" },
      rag: {
        ...baseRag,
        results: [nestedLocalResult],
      },
      pedagogy: {
        mode: "socratic",
        phase: "scaffold",
        move: "give_hint",
        disclosure_level: 1,
        evidence_ids: ["chunk-1"],
      },
    };

    const liveEvidence = evidenceFromResponse(response);
    const restored = evidenceFromSessionTurns([
      {
        turn_id: "turn-1",
        route_snapshot: { mode: "socratic" },
        pedagogy_snapshot: {
          mode: "socratic",
          phase: "scaffold",
          move: "give_hint",
          disclosure_level: 1,
          evidence_ids: ["chunk-1"],
        },
        rag_snapshot: {
          ...baseRag,
          results: [nestedLocalResult],
        },
      },
    ]).get("turn-1");

    expect(restored).toBeDefined();
    expect(restored?.pedagogy?.evidence_ids).toEqual(["chunk-1"]);
    expect(normalizeEvidence(restored!)).toEqual(normalizeEvidence(liveEvidence));
  });

  it("evidenceSummary counts by type and status", () => {
    const refs = normalizeEvidence({
      rag: {
        ...baseRag,
        results: [{ chunk: { chunk_id: "chunk-doc", title: "Doc", source_path: "d.md" }, score: 0.5 }],
        web_tools: {
          enabled: true,
          used: true,
          calls: [
            { name: "web_search", arguments: { query: "q" }, result: { results: [{ title: "W", url: "https://w.com" }] } },
            { name: "web_read", arguments: { url: "https://r.com" }, result: { ok: "true" } },
          ],
          error: "",
        },
      },
    });
    const summary = evidenceSummary(refs);
    expect(summary.local).toBe(1);
    expect(summary.web).toBe(2);
    expect(summary.total).toBe(3);
    expect(summary.selected).toBe(0);
  });
});
