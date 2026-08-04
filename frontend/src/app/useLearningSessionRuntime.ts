import { useCallback, useMemo, useState } from "react";

import { useMemoryController } from "../features/learning-memory/memoryController";
import {
  CHAT_SETTINGS_DEFAULTS,
  modeOptions,
} from "../features/settings/SettingsPanel";
import type { ApiSnapshot, ChatSettings } from "../types";
import type { WorkspaceRecovery } from "./WorkspacePersistence";
import { useWorkspace } from "./WorkspaceProvider";

type RuntimeSettings = NonNullable<ApiSnapshot["runtimeSettings"]>["settings"];

export type LearningRecoveryInput = Pick<
  WorkspaceRecovery,
  | "memoryRunId"
  | "learningClosureRunId"
  | "chatSettings"
  | "keepCurrentRole"
  | "conversationInstruction"
>;

export type LearningRecoveryState = {
  memoryRunId?: string;
  learningClosureRunId?: string;
  chatSettings: ChatSettings;
  keepCurrentRole: boolean;
  conversationInstruction: string;
};

export type LearningRecoveryPort = {
  state: LearningRecoveryState;
  restore: (recovery: LearningRecoveryInput) => boolean;
  hydrateRuntimeSettings: (settings: RuntimeSettings) => void;
};

export function useLearningSessionRuntime(options: {
  refresh: () => Promise<void>;
}) {
  const { state, dispatch } = useWorkspace();
  const [chatSettings, setChatSettings] = useState<ChatSettings>(
    CHAT_SETTINGS_DEFAULTS,
  );
  const [keepCurrentRole, setKeepCurrentRole] = useState(false);
  const [conversationInstruction, setConversationInstruction] = useState("");

  const memoryRunId = state.activeMemoryRunId;
  const learningClosureRunId = state.activeLearningClosureRunId;
  const setMemoryRunId = useCallback(
    (runId?: string) => dispatch({ type: "SET_ACTIVE_MEMORY_RUN", runId }),
    [dispatch],
  );
  const setLearningClosureRunId = useCallback(
    (runId?: string) =>
      dispatch({ type: "SET_ACTIVE_LEARNING_CLOSURE_RUN", runId }),
    [dispatch],
  );

  const memoryController = useMemoryController({
    activeRunId: memoryRunId,
    setActiveRunId: setMemoryRunId,
    activeClosureRunId: learningClosureRunId,
    setActiveClosureRunId: setLearningClosureRunId,
    onMemoryChanged: options.refresh,
    onSummaryChanged: (summary) =>
      dispatch({ type: "SET_SESSION_SUMMARY", summary }),
  });

  const restore = useCallback(
    (recovery: LearningRecoveryInput) => {
      if (recovery.memoryRunId) setMemoryRunId(recovery.memoryRunId);
      if (recovery.learningClosureRunId) {
        setLearningClosureRunId(recovery.learningClosureRunId);
      }

      let restoredChatSettings = false;
      if (recovery.chatSettings) {
        setChatSettings({
          ...CHAT_SETTINGS_DEFAULTS,
          ...recovery.chatSettings,
        });
        restoredChatSettings = true;
      }
      if (typeof recovery.keepCurrentRole === "boolean") {
        setKeepCurrentRole(recovery.keepCurrentRole);
      }
      if (typeof recovery.conversationInstruction === "string") {
        setConversationInstruction(recovery.conversationInstruction);
      }
      return restoredChatSettings;
    },
    [setLearningClosureRunId, setMemoryRunId],
  );

  const hydrateRuntimeSettings = useCallback((settings: RuntimeSettings) => {
    const visibleMode = modeOptions.some(([value]) => value === settings.selected_mode)
      ? settings.selected_mode
      : "auto";
    setChatSettings({
      selectedRole: settings.selected_role,
      selectedMode: visibleMode,
      selectedModel: settings.selected_model,
      relationshipMode: settings.relationship_mode,
      contextMode:
        settings.context_mode === "fast" ||
        settings.context_mode === "light" ||
        settings.context_mode === "deep"
          ? settings.context_mode
          : "",
    });
  }, []);

  const recovery = useMemo<LearningRecoveryPort>(
    () => ({
      state: {
        memoryRunId,
        learningClosureRunId,
        chatSettings,
        keepCurrentRole,
        conversationInstruction,
      },
      restore,
      hydrateRuntimeSettings,
    }),
    [
      memoryRunId,
      learningClosureRunId,
      chatSettings,
      keepCurrentRole,
      conversationInstruction,
      restore,
      hydrateRuntimeSettings,
    ],
  );

  return {
    chatSettings,
    setChatSettings,
    keepCurrentRole,
    setKeepCurrentRole,
    conversationInstruction,
    setConversationInstruction,
    memoryRunId,
    learningClosureRunId,
    setMemoryRunId,
    setLearningClosureRunId,
    memoryController,
    recovery,
  };
}

export type LearningSessionRuntime = ReturnType<
  typeof useLearningSessionRuntime
>;
