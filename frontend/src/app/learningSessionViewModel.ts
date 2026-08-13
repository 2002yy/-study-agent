import type { SessionRow } from "../types";
import type { SemanticSessionRow } from "../features/sessions/sessionNavigation";
import type { SessionSummary } from "../features/sessions/sessionSummary";

export function selectActiveLearningSession(
  sessions: SessionRow[],
  threadId?: string,
): SemanticSessionRow | null {
  if (!threadId) return null;
  return (
    (sessions.find(
      (session) => session.session_id === threadId,
    ) as SemanticSessionRow | undefined) ?? null
  );
}

export function selectLearningSessionSummary(
  activeSession: SemanticSessionRow | null,
  localSummary: SessionSummary | null,
  threadId?: string,
): SessionSummary | null {
  if (!threadId) return null;
  const serverSummary = activeSession?.summary ?? null;
  const matchingLocalSummary =
    localSummary?.thread_id === threadId ? localSummary : null;

  if (
    serverSummary?.status === "not_summarized" &&
    matchingLocalSummary &&
    matchingLocalSummary.status !== "not_summarized"
  ) {
    return matchingLocalSummary;
  }

  return serverSummary ?? matchingLocalSummary;
}
