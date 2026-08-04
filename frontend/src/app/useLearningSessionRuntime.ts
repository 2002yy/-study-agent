import {
  useCallback,
  useMemo,
  useRef,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import {
  createEmptyRag,
  useChatController,
} from "../features/chat/chatController";
import { useMemoryController } from "../features/learning-memory/memoryController";
import {
  CHAT_SETTINGS_DEFAULTS,
  modeOptions,
  RAG_SETTINGS_DEFAULTS,
} from "../features/settings/SettingsPanel";
import { seedMessages } from "../features/single-chat/chatHistory";
import type { ApiSnapshot, ChatSettings } from "../types";
import type { EvidenceLearningPort } from "./useEvidenceRuntime";
import type { WorkspaceRecovery } from "./WorkspacePersistence";
import { useWorkspace } from "./WorkspaceProvider";

type RuntimeSettings = NonNullable<ApiSnapshot["runtimeSettings"]>["settings"];

export type LearningArtifactPort = {
  clearChatArtifacts: () => void;
};

export type LearningRecoveryInput = Pick<
  WorkspaceRecovery,
  | "singleChatSessionId"
  | "sessionId"
  | "memoryRunId"
  | "learningClosureRunId"
  | "chatSettings"
  | "keepCurrentRole"
  | "conversationInstruction"
  | "lastRoute"
  | "lastRag"
  | "lastSessionId"
  | "cachedMessages"
  | "isSending"
>;

export type LearningRecoveryState = Pick<
  WorkspaceRecovery,
  | "singleChatSessionId"
  | "memoryRunId"
  | "learningClosureRunId"
  | "lastRoute"
  | "lastRag"
  | "lastSessionId"
  | "cachedMessages"
  | "isSending"
> & {
  chatSettings: ChatSettings;
  keepCurrentRole: boolean;
  conversationInstruction: string;
};

export type LearningRecoveryPort = {
  state: LearningRecoveryState;
  restore: (recovery: LearningRecoveryInput | null) => boolean;
  hydrateRuntimeSettings: (settings: RuntimeSettings) => void;
};

export function useLearningSessionRuntime(options: {
  refresh: () => Promise<void>;
  setInput: Dispatch<SetStateAction<string>>;
  setOperationError: Dispatch<SetStateAction<string>>;
  evidence: EvidenceLearningPort;
  webPolicy: string;
}) {
  const { state, dispatch } = useWorkspace();
  const [chatSettings, setChatSettings] = useState<ChatSettings>(
    CHAT_SETTINGS_DEFAULTS,
  );
  const [keepCurrentRole, setKeepCurrentRole] = useState(false);
  const [conversationInstruction, setConversationInstruction] = useState("");
  const artifactPortRef = useRef<LearningArtifactPort>({
    clearChatArtifacts: () => undefined,
  });

  const bindArtifactPort = useCallback((port: LearningArtifactPort) => {
    artifactPortRef.current = port;
    return () => {
      if (artifactPortRef.current === port) {
        artifactPortRef.current = { clearChatArtifacts: () => undefined };
      }
    };
  }, []);
  const clearChatArtifacts = useCallback(
    () => artifactPortRef.current.clearChatArtifacts(),
    [],
  );

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

  const chatController = useChatController({
    chatSettings,
    chatSettingsDefaults: CHAT_SETTINGS_DEFAULTS,
    setChatSettings,
    ragSettings: options.evidence.ragSettings,
    ragSettingsDefaults: RAG_SETTINGS_DEFAULTS,
    setRagSettings: options.evidence.setRagSettings,
    ragEnabled: options.evidence.ragEnabled,
    setRagEnabled: options.evidence.setRagEnabled,
    keepCurrentRole,
    setKeepCurrentRole,
    conversationInstruction,
    setConversationInstruction,
    webLookupSource: options.evidence.webLookupSource,
    webLookupRunId: options.evidence.webLookupRunId,
    useWebLookup: options.evidence.useWebLookup,
    webPolicy: options.webPolicy,
    setUseWebLookup: options.evidence.setUseWebLookup,
    setInput: options.setInput,
    setOperationError: options.setOperationError,
    clearChatArtifacts,
    refresh: options.refresh,
    onResearchRunDiscovered: options.evidence.onResearchRunDiscovered,
  });

  const restore = useCallback(
    (recovery: LearningRecoveryInput | null) => {
      if (!recovery) {
        chatController.setMessages(seedMessages);
        return false;
      }

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

      const restoredThreadId =
        recovery.singleChatSessionId ?? recovery.sessionId ?? "";
      if (restoredThreadId) {
        void chatController.hydrateSession(
          restoredThreadId,
          recovery.cachedMessages,
        );
      } else {
        chatController.setMessages(seedMessages);
      }
      if (recovery.lastRoute) {
        chatController.setLastChat({
          reply: "",
          session_id:
            recovery.lastSessionId ?? restoredThreadId ?? "restored",
          route: recovery.lastRoute,
          rag: recovery.lastRag ?? createEmptyRag(),
        });
      }
      return restoredChatSettings;
    },
    [chatController, setLearningClosureRunId, setMemoryRunId],
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
        singleChatSessionId: chatController.threadId,
        memoryRunId,
        learningClosureRunId,
        chatSettings,
        keepCurrentRole,
        conversationInstruction,
        lastRoute: chatController.lastChat?.route,
        lastRag: chatController.lastChat?.rag,
        lastSessionId: chatController.lastChat?.session_id,
        cachedMessages: chatController.messages,
        isSending: chatController.isSending,
      },
      restore,
      hydrateRuntimeSettings,
    }),
    [
      chatController.threadId,
      chatController.lastChat,
      chatController.messages,
      chatController.isSending,
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
    chatController,
    bindArtifactPort,
    recovery,
  };
}

export type LearningSessionRuntime = ReturnType<
  typeof useLearningSessionRuntime
>;
