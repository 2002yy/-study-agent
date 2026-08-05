import { describe, expect, it } from "vitest";

import type { ChatMessage, SessionRow } from "../types";
import type { SemanticSessionRow } from "../features/sessions/sessionNavigation";
import type { SessionSummary } from "../features/sessions/sessionSummary";
import {
  selectActiveLearningSession,
  selectLearningSessionSummary,
  selectNewSessionConfirmation,
  SUMMARIZED_NEW_SESSION_CONFIRMATION,
  UNSUMMARIZED_NEW_SESSION_CONFIRMATION,
} from "./learningSessionViewModel";

const summary = (
  threadId: string,
  status: SessionSummary["status"],
): SessionSummary => ({
  thread_id: threadId,
  status,
  can_summarize: status !== "summarized",
});

describe("learning session view selectors", () => {
  it("selects the active semantic session by the current thread", () => {
    const sessions = [
      { session_id: "thread-a", name: "A" },
      { session_id: "thread-b", name: "B", objective: "Learn B" },
    ] as SessionRow[];

    expect(selectActiveLearningSession(sessions, "thread-b")).toMatchObject({
      session_id: "thread-b",
      objective: "Learn B",
    });
    expect(selectActiveLearningSession(sessions, "missing")).toBeNull();
    expect(selectActiveLearningSession(sessions, undefined)).toBeNull();
  });

  it("does not expose a session summary before a thread exists", () => {
    expect(
      selectLearningSessionSummary(
        null,
        summary("thread-a", "summarized"),
        undefined,
      ),
    ).toBeNull();
  });

  it("prefers a newer local summary over a stale not-summarized server row", () => {
    const activeSession = {
      session_id: "thread-a",
      name: "A",
      summary: summary("thread-a", "not_summarized"),
    } as SemanticSessionRow;
    const local = summary("thread-a", "summarized");

    expect(
      selectLearningSessionSummary(activeSession, local, "thread-a"),
    ).toBe(local);
  });

  it("keeps a meaningful server summary and ignores local state from another thread", () => {
    const server = summary("thread-a", "needs_update");
    const activeSession = {
      session_id: "thread-a",
      name: "A",
      summary: server,
    } as SemanticSessionRow;

    expect(
      selectLearningSessionSummary(
        activeSession,
        summary("thread-b", "summarized"),
        "thread-a",
      ),
    ).toBe(server);
  });

  it("preserves the existing new-session confirmation semantics", () => {
    const assistantOnly = [{ role: "assistant" } as ChatMessage];
    const withUser = [{ role: "user" } as ChatMessage];

    expect(selectNewSessionConfirmation(assistantOnly, null)).toBeNull();
    expect(
      selectNewSessionConfirmation(
        withUser,
        summary("thread-a", "summarized"),
      ),
    ).toBe(SUMMARIZED_NEW_SESSION_CONFIRMATION);
    expect(
      selectNewSessionConfirmation(
        withUser,
        summary("thread-a", "needs_update"),
      ),
    ).toBe(UNSUMMARIZED_NEW_SESSION_CONFIRMATION);
  });
});
