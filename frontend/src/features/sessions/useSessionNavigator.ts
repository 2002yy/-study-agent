import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";

import type { SessionRow } from "../../types";
import { searchSessions } from "../../api";
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

type SessionNavigatorInteractionState = {
  query: string;
  groupMode: SessionGroupMode;
  editingId: string | null;
  editingTitle: string;
  renameError: string;
  isRenaming: boolean;
};

const INITIAL_INTERACTION_STATE: SessionNavigatorInteractionState = {
  query: "",
  groupMode: "time",
  editingId: null,
  editingTitle: "",
  renameError: "",
  isRenaming: false,
};

let sharedInteractionState = INITIAL_INTERACTION_STATE;
const interactionListeners = new Set<() => void>();

function interactionSnapshot(): SessionNavigatorInteractionState {
  return sharedInteractionState;
}

function updateInteractionState(
  patch:
    | Partial<SessionNavigatorInteractionState>
    | ((current: SessionNavigatorInteractionState) => Partial<SessionNavigatorInteractionState>),
) {
  const nextPatch = typeof patch === "function" ? patch(sharedInteractionState) : patch;
  sharedInteractionState = { ...sharedInteractionState, ...nextPatch };
  interactionListeners.forEach((listener) => listener());
}

function subscribeToInteractionState(listener: () => void) {
  interactionListeners.add(listener);
  return () => {
    interactionListeners.delete(listener);
    if (!interactionListeners.size) {
      sharedInteractionState = INITIAL_INTERACTION_STATE;
    }
  };
}

// Local filter still applies to snapshot rows when no server result set is
// active (query empty or server search failed); server rows are already
// backend-filtered.
function queryFiltered(
  rows: SemanticSessionRow[],
  query: string,
): SemanticSessionRow[] {
  const trimmed = query.trim();
  if (!trimmed) return rows;
  return rows.filter((session) => matchesSessionSearch(session, trimmed));
}

const PAGE_SIZE = 50;

/**
 * One workspace-level interaction owner shared by the desktop sidebar and mobile drawer.
 * Both render surfaces subscribe to this store, so search, rename and archive confirmation
 * cannot diverge while they are mounted at the same time.
 */
export function useSessionNavigator(
  sessions: SessionRow[],
  activeSessionId: string | undefined,
  actions: SessionNavigatorActions,
) {
  const interaction = useSyncExternalStore(
    subscribeToInteractionState,
    interactionSnapshot,
    interactionSnapshot,
  );
  // G4: server-side search/paging. When a query is active the displayed
  // set comes from the backend (covering ALL sessions), not just the
  // newest-window snapshot rows.
  const [serverRows, setServerRows] = useState<SemanticSessionRow[] | null>(null);
  const [serverTotal, setServerTotal] = useState(0);
  const [isServerSearching, setIsServerSearching] = useState(false);
  const [serverError, setServerError] = useState("");
  const requestIdRef = useRef(0);

  useEffect(() => {
    const query = interaction.query.trim();
    if (!query) {
      setServerRows(null);
      setServerTotal(0);
      setServerError("");
      return;
    }
    const requestId = ++requestIdRef.current;
    const timer = setTimeout(() => {
      setIsServerSearching(true);
      searchSessions({ query, limit: PAGE_SIZE, offset: 0 })
        .then((response) => {
          if (requestIdRef.current !== requestId) return;
          setServerRows(response.sessions as SemanticSessionRow[]);
          setServerTotal(response.total);
          setServerError("");
        })
        .catch(() => {
          if (requestIdRef.current !== requestId) return;
          setServerError("服务端会话搜索失败，当前仅搜索最近会话。");
        })
        .finally(() => {
          if (requestIdRef.current === requestId) setIsServerSearching(false);
        });
    }, 300);
    return () => clearTimeout(timer);
  }, [interaction.query]);

  const loadMore = async () => {
    const query = interaction.query.trim();
    const base = serverRows ?? [];
    const requestId = ++requestIdRef.current;
    setIsServerSearching(true);
    try {
      const response = await searchSessions({
        query,
        limit: PAGE_SIZE,
        offset: base.length,
      });
      if (requestIdRef.current !== requestId) return;
      const merged = [...base];
      const seen = new Set(merged.map(sessionIdFromRow));
      for (const row of response.sessions as SemanticSessionRow[]) {
        if (!seen.has(sessionIdFromRow(row))) merged.push(row);
      }
      setServerRows(merged);
      setServerTotal(response.total);
      setServerError("");
    } catch {
      setServerError("加载更多会话失败，请重试。");
    } finally {
      setIsServerSearching(false);
    }
  };

  const semanticSessions = (
    serverRows ?? (sessions as SemanticSessionRow[])
  );
  const grouped = useMemo(
    () =>
      groupSessions(
        queryFiltered(semanticSessions, interaction.query),
        interaction.groupMode,
      ),
    [semanticSessions, interaction.query, interaction.groupMode],
  );

  const beginRename = (session: SemanticSessionRow) => {
    updateInteractionState({
      editingId: sessionIdFromRow(session),
      editingTitle: session.manual_title || sessionTitle(session),
      renameError: "",
    });
  };

  const saveRename = async (session: SemanticSessionRow) => {
    if (interaction.isRenaming) return;
    updateInteractionState({ isRenaming: true, renameError: "" });
    try {
      await updateSessionTitle(sessionIdFromRow(session), interaction.editingTitle);
      updateInteractionState({ editingId: null });
      await actions.onSessionChanged?.();
    } catch (error) {
      updateInteractionState({
        renameError: error instanceof Error ? error.message : "会话标题保存失败",
      });
    } finally {
      updateInteractionState({ isRenaming: false });
    }
  };

  const restore = (sessionId: string) => {
    actions.onRestore?.(sessionId);
  };

  return {
    semanticSessions,
    grouped,
    query: interaction.query,
    setQuery: (query: string) => updateInteractionState({ query }),
    groupMode: interaction.groupMode,
    setGroupMode: (groupMode: SessionGroupMode) => updateInteractionState({ groupMode }),
    // G4 paging/search surface
    isServerSearching,
    serverError,
    serverTotal,
    hasMore: serverRows !== null && grouped.length < serverTotal,
    loadMore,
    editingId: interaction.editingId,
    editingTitle: interaction.editingTitle,
    setEditingTitle: (editingTitle: string) => updateInteractionState({ editingTitle }),
    cancelRename: () => updateInteractionState({ editingId: null, renameError: "" }),
    beginRename,
    saveRename,
    isRenaming: interaction.isRenaming,
    renameError: interaction.renameError,
    requestArchive: (sessionId: string) => actions.onArchive?.(sessionId),
    restore,
    activeSessionId,
  };
}
