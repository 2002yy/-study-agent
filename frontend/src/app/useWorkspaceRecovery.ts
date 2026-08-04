import { useCallback, useEffect, useMemo, useRef } from "react";
import type { Dispatch, SetStateAction } from "react";

import { createEmptyRag, useChatController } from "../features/chat/chatController";
import {
  CHAT_SETTINGS_DEFAULTS,
  modeOptions,
} from "../features/settings/SettingsPanel";
import { seedMessages } from "../features/single-chat/chatHistory";
import type { ApiSnapshot, ChatSettings } from "../types";
import type { EvidenceRecoveryPort } from "./useEvidenceRuntime";
import {
  useWorkspacePersistence,
  type WorkspaceRecovery,
} from "./WorkspacePersistence";

type DirectSetter = (value?: string) => void;

export function useWorkspaceRecovery(options: {
  snapshot: ApiSnapshot;
  chatController: ReturnType<typeof useChatController>;
  ids: {
    singleChat?: string;
    group?: string;
    tool?: string;
    memory?: string;
    learningClosure?: string;
  };
  setIds: {
    group: DirectSetter;
    tool: DirectSetter;
    memory: DirectSetter;
    learningClosure: DirectSetter;
  };
  evidence: EvidenceRecoveryPort;
  chatSettings: ChatSettings;
  setChatSettings: Dispatch<SetStateAction<ChatSettings>>;
  keepCurrentRole: boolean;
  setKeepCurrentRole: Dispatch<SetStateAction<boolean>>;
  conversationInstruction: string;
  setConversationInstruction: Dispatch<SetStateAction<string>>;
}) {
  const runtimeHydratedRef = useRef(false);
  const sessionSettingsRestoredRef = useRef(false);
  const {
    chatController,
    chatSettings,
    keepCurrentRole,
    conversationInstruction,
    evidence,
  } = options;

  const restoreWorkspace = useCallback((parsed: WorkspaceRecovery | null) => {
    if (!parsed) {
      chatController.setMessages(seedMessages);
      return;
    }
    const restoredThreadId = parsed.singleChatSessionId ?? parsed.sessionId ?? "";
    if (parsed.wechatThreadId) options.setIds.group(parsed.wechatThreadId);
    if (parsed.toolRunId) options.setIds.tool(parsed.toolRunId);
    if (parsed.memoryRunId) options.setIds.memory(parsed.memoryRunId);
    if (parsed.learningClosureRunId) {
      options.setIds.learningClosure(parsed.learningClosureRunId);
    }
    if (
      evidence.restore({
        ragQueryRunId: parsed.ragQueryRunId,
        ragWriteRunId: parsed.ragWriteRunId,
        webLookupRunId: parsed.webLookupRunId,
        ragSettings: parsed.ragSettings,
        ragEnabled: parsed.ragEnabled,
      })
    ) {
      sessionSettingsRestoredRef.current = true;
    }
    if (parsed.chatSettings) {
      sessionSettingsRestoredRef.current = true;
      options.setChatSettings({
        ...CHAT_SETTINGS_DEFAULTS,
        ...parsed.chatSettings,
      });
    }
    if (typeof parsed.keepCurrentRole === "boolean") {
      options.setKeepCurrentRole(parsed.keepCurrentRole);
    }
    if (typeof parsed.conversationInstruction === "string") {
      options.setConversationInstruction(parsed.conversationInstruction);
    }
    if (restoredThreadId) {
      void chatController.hydrateSession(restoredThreadId, parsed.cachedMessages);
    } else {
      chatController.setMessages(seedMessages);
    }
    if (parsed.lastRoute) {
      chatController.setLastChat({
        reply: "",
        session_id: parsed.lastSessionId ?? restoredThreadId ?? "restored",
        route: parsed.lastRoute,
        rag: parsed.lastRag ?? createEmptyRag(),
      });
    }
  }, [chatController, options.setIds, evidence.restore]);

  useEffect(() => {
    const settings = options.snapshot.runtimeSettings?.settings;
    if (!settings || runtimeHydratedRef.current) return;
    runtimeHydratedRef.current = true;
    if (sessionSettingsRestoredRef.current) return;
    const visibleMode = modeOptions.some(([value]) => value === settings.selected_mode)
      ? settings.selected_mode
      : "auto";
    options.setChatSettings({
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
    evidence.hydrateRuntimeSettings(settings);
  }, [options.snapshot.runtimeSettings, evidence.hydrateRuntimeSettings]);

  const persistenceState = useMemo(
    () => ({
      singleChatSessionId: options.ids.singleChat,
      wechatThreadId: options.ids.group,
      toolRunId: options.ids.tool,
      memoryRunId: options.ids.memory,
      learningClosureRunId: options.ids.learningClosure,
      ...evidence.state,
      chatSettings,
      keepCurrentRole,
      conversationInstruction,
      lastRoute: chatController.lastChat?.route,
      lastRag: chatController.lastChat?.rag,
      lastSessionId: chatController.lastChat?.session_id,
      cachedMessages: chatController.messages,
      isSending: chatController.isSending,
    }),
    [
      options.ids,
      evidence.state,
      chatSettings,
      keepCurrentRole,
      conversationInstruction,
      chatController.lastChat,
      chatController.messages,
      chatController.isSending,
    ]
  );
  useWorkspacePersistence({ state: persistenceState, onRestore: restoreWorkspace });
}
