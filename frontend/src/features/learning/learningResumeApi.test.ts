import { afterEach, describe, expect, it, vi } from "vitest";

import { getLearningResume } from "./learningResumeApi";

const durableResume = {
  source: "durable",
  status: "active",
  topic: { topic_id: "topic-1", title: "会话恢复" },
  goal: { goal_id: "goal-1", topic_id: "topic-1", objective: "理解 durable resume", status: "active" },
  claims: [],
  claim_count: 0,
  unresolved: [],
  next_step: {},
  optional_next_steps: [],
};

describe("learning resume API", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reads the encoded read-only learning resume endpoint", async () => {
    const fetchMock = vi.fn(async () =>
      new Response(JSON.stringify(durableResume), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const result = await getLearningResume("chat / 1");

    expect(result.source).toBe("durable");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const calls = fetchMock.mock.calls as Array<[RequestInfo | URL, RequestInit | undefined]>;
    const [url, options] = calls[0];
    expect(String(url)).toBe("/sessions/chat%20%2F%201/learning-resume");
    expect(options?.method).toBeUndefined();
    expect(options?.body).toBeUndefined();
  });
});
