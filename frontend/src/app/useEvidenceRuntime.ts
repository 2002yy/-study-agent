import { useEffect, useState, type Dispatch, type SetStateAction } from "react";

import { useRagController } from "../features/rag/ragController";
import { useUploadController } from "../features/rag/uploadController";
import { RAG_SETTINGS_DEFAULTS } from "../features/settings/SettingsPanel";
import { useWebLookupController } from "../features/web-lookup/webLookupController";
import type { ApiSnapshot, RagSettings } from "../types";
import { useResetResearchSelectionOnSessionChange } from "./useResetResearchSelectionOnSessionChange";
import { useWorkspace } from "./WorkspaceProvider";
import type { WorkspaceFeature } from "./workspaceDataLoader";

type FeatureLoader = (
  feature: WorkspaceFeature,
  options?: { groupThreadId?: string },
) => Promise<Partial<ApiSnapshot>>;

type OperationErrorSetter = Dispatch<SetStateAction<string>>;

export function useEvidenceRuntime(options: {
  snapshot: ApiSnapshot;
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
  const setRagQueryRunId = (runId?: string) =>
    dispatch({ type: "SET_ACTIVE_RAG_QUERY_RUN", runId });
  const setRagWriteRunId = (runId?: string) =>
    dispatch({ type: "SET_ACTIVE_RAG_WRITE_RUN", runId });
  const setWebLookupRunId = (runId?: string) =>
    dispatch({ type: "SET_ACTIVE_WEB_LOOKUP_RUN", runId });

  const webLookupController = useWebLookupController({
    query: options.input,
    setOperationError: options.setOperationError,
    activeRunId: webLookupRunId,
    setActiveRunId: setWebLookupRunId,
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
  };
}

export type EvidenceRuntime = ReturnType<typeof useEvidenceRuntime>;
