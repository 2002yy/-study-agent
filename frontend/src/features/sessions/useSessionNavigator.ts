import { useMemo, useState } from "react";

import type { SessionRow } from "../../types";
import { updateSessionTitle } from "./sessionApi";
import {
  groupSessions,
  matchesSessionSearch,
  sessionIdFromRow,
  sessionTitle,
  type SemanticSessionRow,
  type SessionGroupMode,
} from "./sessionNavigation";

export type SessionNavigatorActions = {
  onRestore?: (sessionId: string) => void;
  onArchive?: (sessionId: string) => void;
  onSessionChanged?: () => Promise<void> | void;
};

export function useSessionNavigator(
  sessions: SessionRow[],
  activeSessionId: string | undefined,
  isSending: boolean,
  actions: SessionNavigatorActions,
) {
  const [query, setQuery] = useState("");
  const [groupMode, setGroupMode] = useState<SessionGroupMode>("time");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [confirmArchiveId, setConfirmArchiveId] = useState<string | null>(null);
  const [renameError, setRenameError] = useState("");
  const [isRenaming, setIsRenaming] = useState(false);
  const semanticSessions = sessions as SemanticSessionRow[];
  const grouped = useMemo(
    () =>
      groupSessions(
        semanticSessions.filter((session) => matchesSessionSearch(session, query)),
        groupMode,
      ),
    [semanticSessions, query, groupMode],
  );

  const beginRename = (session: SemanticSessionRow) => {
    const sessionId = sessionIdFromRow(session);
    setEditingId(sessionId);
    setEditingTitle(session.manual_title || sessionTitle(session));
    setRenameError("");
  };

  const saveRename = async (session: SemanticSessionRow) => {
    if (isRenaming) return;
    setIsRenaming(true);
    setRenameError("");
    try {
      await updateSessionTitle(sessionIdFromRow(session), editingTitle);
      setEditingId(null);
      await actions.onSessionChanged?.();
    } catch (error) {
      setRenameError(error instanceof Error ? error.message : "会话标题保存失败");
    } finally {
      setIsRenaming(false);
    }
  };

  const restore = (sessionId: string) => {
    if (
      isSending &&
      !window.confirm("当前回答正在生成，切换会话将停止生成。继续吗？")
    ) {
      return;
    }
    actions.onRestore?.(sessionId);
  };

  const requestArchive = (sessionId: string) => {
    setConfirmArchiveId(sessionId);
  };

  const confirmArchive = () => {
    if (!confirmArchiveId) return;
    actions.onArchive?.(confirmArchiveId);
    setConfirmArchiveId(null);
  };

  return {
    semanticSessions,
    grouped,
    query,
    setQuery,
    groupMode,
    setGroupMode,
    editingId,
    editingTitle,
    setEditingTitle,
    cancelRename: () => setEditingId(null),
    beginRename,
    saveRename,
    isRenaming,
    renameError,
    confirmArchiveId,
    requestArchive,
    confirmArchive,
    cancelArchive: () => setConfirmArchiveId(null),
    restore,
    activeSessionId,
  };
}
