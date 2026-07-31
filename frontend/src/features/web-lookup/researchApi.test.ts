// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { cancelResearchRun } from "./researchApi";

function payload(overrides: Record<string, unknown> = {}) {
  return {
    id: "web_lookup_cancel",
    query: "Python dependency injection",
    stage: "reading",
    status: "running",
    research_context: {},
    query_attempts: [{ query: "Python dependency injection", status: "completed" }],
    selected_sources: [{ item: { title: "Python docs" }, assessment: {} }],
    rejected_sources: [],
    provider_status: "",
    stop_reason: "user_cancelled",
    answer_confidence: "low",
    items: [],
    source_block: "",
    warnings: [],
    error: "",
    max_items: 8,
    active_operation_id: "web_research_1",
    active_operation_started_at: "2026-07-31T08:00:00Z",
    stage_started_at: "2026-07-31T08:00:00Z",
    cancel_requested_at: "2026-07-31T08:00:01Z",
    version: 2,
    created_at: "2026-07-31T08:00:00Z",
    updated_at: "2026-07-31T08:00:01Z",
    completed_at: null,
    ...overrides,
  };
}

function okJson(value: Record<string, unknown>) {
  return {
    ok: true,
    status: 200,
    statusText: "OK",
    json: async () => value,
    text: async () => "",
  } as Response;
}

describe("cancelResearchRun", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("polls the same durable run until cancellation is finalized", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(okJson(payload()))
      .mockResolvedValueOnce(okJson(payload({ version: 3 })))
      .mockResolvedValueOnce(
        okJson(
          payload({
            stage: "cancelled",
            status: "cancelled",
            active_operation_id: null,
            active_operation_started_at: null,
            stage_started_at: null,
            completed_at: "2026-07-31T08:00:02Z",
            version: 4,
          }),
        ),
      );
    vi.stubGlobal("fetch", fetchMock);

    const result = await cancelResearchRun("web_lookup_cancel", {
      pollIntervalMs: 0,
      timeoutMs: 1000,
    });

    expect(result.status).toBe("cancelled");
    expect(result.run_id).toBe("web_lookup_cancel");
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      "/research-runs/web_lookup_cancel/cancel",
      "/research-runs/web_lookup_cancel",
      "/research-runs/web_lookup_cancel",
    ]);
  });

  it("keeps the durable run recoverable when finalization exceeds the wait budget", async () => {
    const fetchMock = vi.fn().mockResolvedValue(okJson(payload()));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      cancelResearchRun("web_lookup_cancel", {
        pollIntervalMs: 0,
        timeoutMs: 0,
      }),
    ).rejects.toThrow("刷新后可继续查看或重试");

    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
