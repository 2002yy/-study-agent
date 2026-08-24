import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import { useRagController } from "../features/rag/ragController";
import { useUploadController } from "../features/rag/uploadController";
import { RAG_SETTINGS_DEFAULTS } from "../features/settings/SettingsPanel";
import { useWebLookupController } from "../features/web-lookup/webLookupController";
import type { ApiSnapshot, RagSettings } from "../types";
import { useResetResearchSelectionOnSessionChange } from "./useResetResearchSelectionOnSessionChange";
import type { WorkspaceRecovery } from "./WorkspacePersistence";
import { useWorkspace } from "./WorkspaceProvider";
import type { WorkspaceFeature } from "./workspaceDataLoader";

type FeatureLoader = (
  feature: WorkspaceFeature,
  options?: { groupThreadId?: string },
) => Promise<Partial<ApiSnapshot>>;

type OperationErrorSetter = Dispatch<SetStateAction<string>>;
type RuntimeSettings = NonNullable<ApiSnapshot["runtimeSettings"]>["settings"];

export type EvidenceRecoveryInput = Pick<
  WorkspaceRecovery,
  | "ragQueryRunId"
  | "ragWriteRunId"
  | "webLookupRunId"
  | "ragSettings"
  | "ragEnabled"
>;

export type EvidenceRecoveryState = {
  ragQueryRunId?: string;
  ragWriteRunId?: string;
  webLookupRunId?: string;
  ragSettings: RagSettings;
  ragEnabled: boolean;
};

export type EvidenceRecoveryPort = {
  state: EvidenceRecoveryState;
  restore: (recovery: EvidenceRecoveryInput) => boolean;
  hydrateRuntimeSettings: (settings: RuntimeSettings) => void;
};

export type EvidenceLearningPort = {
  ragEnabled: boolean;
  setRagEnabled: Dispatch<SetStateAction<boolean>>;
  ragSettings: RagSettings;
  setRagSettings: Dispatch<SetStateAction<RagSettings>>;
  webLookupSource: string;
  webLookupRunId?: string;
  useWebLookup: boolean;
  setUseWebLookup: Dispatch<SetStateAction<boolean>>;
  onResearchRunDiscovered: (runId: string, forceRefresh?: boolean) => void;
};

export function useEvidenceRuntime(options: {
  refresh: () => Promise<void>;
  loadFeature: FeatureLoader;
  input: string;
  activeChatThreadId?: string;
  setOperationError: OperationErrorSetter;
}) {
  const { state, dispatch } = useWorkspace();
  const [ragEnabled, setRagEnabled] = useState(true);
  const [ragSettings, setRagSettings] = useState<RagSettings>(RAG_SETTINGS_DEFAULTS);

  const ragQueryRunId = state.activeRagQueryRunId;
  const ragWriteRunId = state.activeRagWriteRunId;
  const webLookupRunId = state.activeWebLookupRunId;
  const setRagQueryRunId = useCallback(
    (runId?: string) => dispatch({ type: "SET_ACTIVE_RAG_QUERY_RUN", runId }),
    [dispatch],
  );
  const setRagWriteRunId = useCallback(
    (runId?: string) => dispatch({ type: "SET_ACTIVE_RAG_WRITE_RUN", runId }),
    [dispatch],
  );
  const setWebLookupRunId = useCallback(
    (runId?: string) => dispatch({ type: "SET_ACTIVE_WEB_LOOKUP_RUN", runId }),
    [dispatch],
  );

  const webLookupController = useWebLookupController({
    query: options.input,
    setOperationError: options.setOperationError,
    activeRunId: webLookupRunId,
    setActiveRunId: setWebLookupRunId,
    activeThreadId: options.activeChatThreadId,
  });
  const ragController = useRagController({
    settings: ragSettings,
    activeRunId: ragQueryRunId,
    setActiveRunId: setRagQueryRunId,
    setOperationError: options.setOperationError,
  });
  const uploadController = useUploadController({
    activeRunId: ragWriteRunId,
    setActiveRunId: setRagWriteRunId,
    setOperationError: options.setOperationError,
    onChanged: options.refresh,
  });

  const onResearchRunDiscovered = useCallback(
    (runId: string, forceRefresh = false) => {
      setWebLookupRunId(runId);
      if (forceRefresh) void webLookupController.refreshRun(runId);
    },
    [setWebLookupRunId, webLookupController.refreshRun],
  );

  const restore = useCallback(
    (recovery: EvidenceRecoveryInput) => {
      if (recovery.ragQueryRunId) setRagQueryRunId(recovery.ragQueryRunId);
      if (recovery.ragWriteRunId) setRagWriteRunId(recovery.ragWriteRunId);
      if (recovery.webLookupRunId) setWebLookupRunId(recovery.webLookupRunId);

      let restoredSessionSettings = false;
      if (recovery.ragSettings) {
        setRagSettings({ ...RAG_SETTINGS_DEFAULTS, ...recovery.ragSettings });
        restoredSessionSettings = true;
      }
      if (typeof recovery.ragEnabled === "boolean") {
        setRagEnabled(recovery.ragEnabled);
        restoredSessionSettings = true;
      }
      return restoredSessionSettings;
    },
    [setRagQueryRunId, setRagWriteRunId, setWebLookupRunId],
  );

  const hydrateRuntimeSettings = useCallback((settings: RuntimeSettings) => {
    setRagEnabled(settings.rag_enabled);
    setRagSettings({
      retrievalMode: settings.rag_retrieval_mode,
      topK: settings.rag_search_top_k ?? settings.rag_top_k,
      chatTopK: settings.rag_chat_top_k ?? settings.rag_top_k,
      minScore: settings.rag_min_score,
    });
  }, []);

  const recovery = useMemo<EvidenceRecoveryPort>(
    () => ({
      state: {
        ragQueryRunId,
        ragWriteRunId,
        webLookupRunId,
        ragSettings,
        ragEnabled,
      },
      restore,
      hydrateRuntimeSettings,
    }),
    [
      ragQueryRunId,
      ragWriteRunId,
      webLookupRunId,
      ragSettings,
      ragEnabled,
      restore,
      hydrateRuntimeSettings,
    ],
  );

  const learning = useMemo<EvidenceLearningPort>(
    () => ({
      ragEnabled,
      setRagEnabled,
      ragSettings,
      setRagSettings,
      webLookupSource: webLookupController.result?.source_block ?? "",
      webLookupRunId: webLookupController.result?.run_id,
      useWebLookup: webLookupController.useInChat,
      setUseWebLookup: webLookupController.setUseInChat,
      onResearchRunDiscovered,
    }),
    [
      ragEnabled,
      ragSettings,
      webLookupController.result,
      webLookupController.useInChat,
      webLookupController.setUseInChat,
      onResearchRunDiscovered,
    ],
  );

  useResetResearchSelectionOnSessionChange(
    options.activeChatThreadId,
    webLookupController.setUseInChat,
  );

  useEffect(() => {
    if (state.activeDrawer !== "sources") return;
    let active = true;
    const load = async () => {
      try {
        await Promise.all([
          options.loadFeature("rag"),
          uploadController.refreshDocuments(),
        ]);
      } catch (error) {
        if (!active) return;
        options.setOperationError(
          `资料与来源加载失败：${error instanceof Error ? error.message : "读取失败"}`,
        );
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [state.activeDrawer, options.loadFeature]);

  return {
    ragEnabled,
    setRagEnabled,
    ragSettings,
    setRagSettings,
    ragQueryRunId,
    ragWriteRunId,
    webLookupRunId,
    setRagQueryRunId,
    setRagWriteRunId,
    setWebLookupRunId,
    webLookupController,
    ragController,
    uploadController,
    recovery,
    learning,
  };
}

export type EvidenceRuntime = ReturnType<typeof useEvidenceRuntime>;
