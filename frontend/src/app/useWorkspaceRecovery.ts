import { useCallback, useEffect, useMemo, useRef } from "react";

import type { ApiSnapshot } from "../types";
import type { EvidenceRecoveryPort } from "./useEvidenceRuntime";
import type { ExtensionRecoveryPort } from "./useExtensionRuntime";
import type { LearningRecoveryPort } from "./useLearningSessionRuntime";
import {
  useWorkspacePersistence,
  type WorkspaceRecovery,
} from "./WorkspacePersistence";

export function useWorkspaceRecovery(options: {
  snapshot: ApiSnapshot;
  evidence: EvidenceRecoveryPort;
  learning: LearningRecoveryPort;
  extension: ExtensionRecoveryPort;
}) {
  const runtimeHydratedRef = useRef(false);
  const sessionSettingsRestoredRef = useRef(false);
  const { evidence, learning, extension } = options;

  const restoreWorkspace = useCallback(
    (parsed: WorkspaceRecovery | null) => {
      if (!parsed) {
        extension.restore(null);
        learning.restore(null);
        return;
      }
      extension.restore(parsed);
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
    [extension.restore, evidence.restore, learning.restore],
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
      ...extension.state,
      ...learning.state,
      ...evidence.state,
    }),
    [extension.state, learning.state, evidence.state],
  );
  useWorkspacePersistence({ state: persistenceState, onRestore: restoreWorkspace });
}
