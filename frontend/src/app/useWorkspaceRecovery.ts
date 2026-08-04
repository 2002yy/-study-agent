import { useCallback, useEffect, useMemo, useRef } from "react";

import { createEmptyRag, useChatController } from "../features/chat/chatController";
import { seedMessages } from "../features/single-chat/chatHistory";
import type { ApiSnapshot } from "../types";
import type { EvidenceRecoveryPort } from "./useEvidenceRuntime";
import type { LearningRecoveryPort } from "./useLearningSessionRuntime";
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
  };
  setIds: {
    group: DirectSetter;
    tool: DirectSetter;
  };
  evidence: EvidenceRecoveryPort;
  learning: LearningRecoveryPort;
}) {
  const runtimeHydratedRef = useRef(false);
  const sessionSettingsRestoredRef = useRef(false);
  const { chatController, evidence, learning } = options;

  const restoreWorkspace = useCallback((parsed: WorkspaceRecovery | null) => {
    if (!parsed) {
      chatController.setMessages(seedMessages);
      return;
    }
    const restoredThreadId = parsed.singleChatSessionId ?? parsed.sessionId ?? "";
    if (parsed.wechatThreadId) options.setIds.group(parsed.wechatThreadId);
    if (parsed.toolRunId) options.setIds.tool(parsed.toolRunId);
    if (
      learning.restore({
        memoryRunId: parsed.memoryRunId,
        learningClosureRunId: parsed.learningClosureRunId,
        chatSettings: parsed.chatSettings,
        keepCurrentRole: parsed.keepCurrentRole,
        conversationInstruction: parsed.conversationInstruction,
      })
    ) {
      sessionSettingsRestoredRef.current = true;
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
  }, [chatController, options.setIds, evidence.restore, learning.restore]);

  useEffect(() => {
    const settings = options.snapshot.runtimeSettings?.settings;
    if (!settings || runtimeHydratedRef.current) return;
    runtimeHydratedRef.current = true;
    if (sessionSettingsRestoredRef.current) return;
    learning.hydrateRuntimeSettings(settings);
    evidence.hydrateRuntimeSettings(settings);
  }, [
    options.snapshot.runtimeSettings,
    evidence.hydrateRuntimeSettings,
    learning.hydrateRuntimeSettings,
  ]);

  const persistenceState = useMemo(
    () => ({
      singleChatSessionId: options.ids.singleChat,
      wechatThreadId: options.ids.group,
      toolRunId: options.ids.tool,
      ...learning.state,
      ...evidence.state,
      lastRoute: chatController.lastChat?.route,
      lastRag: chatController.lastChat?.rag,
      lastSessionId: chatController.lastChat?.session_id,
      cachedMessages: chatController.messages,
      isSending: chatController.isSending,
    }),
    [
      options.ids,
      learning.state,
      evidence.state,
      chatController.lastChat,
      chatController.messages,
      chatController.isSending,
    ]
  );
  useWorkspacePersistence({ state: persistenceState, onRestore: restoreWorkspace });
}
