import { afterEach, describe, expect, it, vi } from "vitest";

import { getLearningResume, revalidateClaim } from "./learningResumeApi";

const durableResume = {
  source: "durable",
  status: "active",
  topic: { topic_id: "topic-1", title: "会话恢复" },
  goal: {
    goal_id: "goal-1",
    topic_id: "topic-1",
    objective: "理解 durable resume",
    status: "active",
  },
  claims: [],
  claim_count: 0,
  unresolved: [],
  next_step: {},
  optional_next_steps: [],
};

describe("learning resume API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reads the encoded read-only learning resume endpoint", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(JSON.stringify(durableResume), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getLearningResume("chat / 1");

    expect(result.source).toBe("durable");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("/sessions/chat%20%2F%201/learning-resume");
    expect(options?.method).toBeUndefined();
    expect(options?.body).toBeUndefined();
  });

  it("posts the explicit revalidate endpoint for one claim", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response(
          JSON.stringify({
            claim_id: "claim-1",
            outcome: "revalidated",
            revision_id: "rev-3",
            head_commit: "c".repeat(40),
            freshness_status: "current",
          }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await revalidateClaim("chat / 1", "claim-1");

    expect(result.outcome).toBe("revalidated");
    expect(result.freshness_status).toBe("current");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, options] = fetchMock.mock.calls[0];
    expect(String(url)).toBe(
      "/sessions/chat%20%2F%201/claims/claim-1/revalidate",
    );
    expect(options?.method).toBe("POST");
    expect(options?.body).toBeUndefined();
  });

  it("surfaces revalidation failures as errors", async () => {
    const fetchMock = vi.fn(
      async (_input: RequestInfo | URL, _init?: RequestInit) =>
        new Response("no_convergence", {
          status: 409,
          statusText: "Conflict",
        }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      revalidateClaim("chat / 1", "claim-1"),
    ).rejects.toThrow("409 Conflict: no_convergence");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});