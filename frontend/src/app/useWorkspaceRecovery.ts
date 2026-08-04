import { useCallback, useEffect, useMemo, useRef } from "react";

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
  ids: {
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
  const { evidence, learning } = options;

  const restoreWorkspace = useCallback(
    (parsed: WorkspaceRecovery | null) => {
      if (!parsed) {
        learning.restore(null);
        return;
      }
      if (parsed.wechatThreadId) options.setIds.group(parsed.wechatThreadId);
      if (parsed.toolRunId) options.setIds.tool(parsed.toolRunId);
      if (
        learning.restore({
          singleChatSessionId: parsed.singleChatSessionId,
          sessionId: parsed.sessionId,
          memoryRunId: parsed.memoryRunId,
          learningClosureRunId: parsed.learningClosureRunId,
          chatSettings: parsed.chatSettings,
          keepCurrentRole: parsed.keepCurrentRole,
          conversationInstruction: parsed.conversationInstruction,
          lastRoute: parsed.lastRoute,
          lastRag: parsed.lastRag,
          lastSessionId: parsed.lastSessionId,
          cachedMessages: parsed.cachedMessages,
          isSending: parsed.isSending,
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
    },
    [options.setIds, evidence.restore, learning.restore],
  );

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
      wechatThreadId: options.ids.group,
      toolRunId: options.ids.tool,
      ...learning.state,
      ...evidence.state,
    }),
    [options.ids, learning.state, evidence.state],
  );
  useWorkspacePersistence({ state: persistenceState, onRestore: restoreWorkspace });
}
