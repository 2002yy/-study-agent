import { useMemo, useSyncExternalStore } from "react";

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
  const semanticSessions = sessions as SemanticSessionRow[];
  const grouped = useMemo(
    () =>
      groupSessions(
        semanticSessions.filter((session) =>
          matchesSessionSearch(session, interaction.query),
        ),
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
