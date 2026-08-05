import type { ChatMessage, SessionRow } from "../types";
import type { SemanticSessionRow } from "../features/sessions/sessionNavigation";
import type { SessionSummary } from "../features/sessions/sessionSummary";

export const SUMMARIZED_NEW_SESSION_CONFIRMATION =
  "当前会话已整理但尚未归档。直接开始新会话时，旧会话会保留在历史中。继续吗？";
export const UNSUMMARIZED_NEW_SESSION_CONFIRMATION =
  "当前学习尚未整理，直接开始新会话？旧会话会保留在历史中。";

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

export function selectNewSessionConfirmation(
  messages: ChatMessage[],
  sessionSummary: SessionSummary | null,
): string | null {
  const hasUserMessages = messages.some((message) => message.role === "user");
  if (!hasUserMessages) return null;
  return sessionSummary?.status === "summarized"
    ? SUMMARIZED_NEW_SESSION_CONFIRMATION
    : UNSUMMARIZED_NEW_SESSION_CONFIRMATION;
}
