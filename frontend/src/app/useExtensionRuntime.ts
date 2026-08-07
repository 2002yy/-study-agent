import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type Dispatch,
  type SetStateAction,
} from "react";

import type { LocalKnowledgeInvocation } from "../api";
import {
  resolveExtensionCapability,
  selectExtensionSurface,
  type ExtensionCapabilityId,
  type ExtensionSurfaceId,
} from "../features/extensions/extensionDrawerContract";
import { useGroupChatController } from "../features/group-chat/groupChatController";
import { useToolController } from "../features/tools/toolController";
import type { ResearchLookupResponse } from "../features/web-lookup/researchApi";
import { useWorkflowController } from "../features/workflows/workflowController";
import type {
  ApiSnapshot,
  ChatSettings,
  RagSettings,
} from "../types";
import { selectActiveQuery } from "./activeQuerySelector";
import { operationRegistry } from "./operationRegistry";
import type { WorkspaceRecovery } from "./WorkspacePersistence";
import { useWorkspace } from "./WorkspaceProvider";
import type { WorkspaceFeature } from "./workspaceDataLoader";

type FeatureLoader = (
  feature: WorkspaceFeature,
  options?: { groupThreadId?: string },
) => Promise<Partial<ApiSnapshot>>;

type GroupController = ReturnType<typeof useGroupChatController>;
type ToolController = ReturnType<typeof useToolController>;
type WorkflowController = ReturnType<typeof useWorkflowController>;

export type ExtensionEvidenceViewPort = {
  result: ResearchLookupResponse | null;
  useInChat: boolean;
  setUseInChat: (enabled: boolean) => void;
};

export type ExtensionRecoveryInput = Pick<
  WorkspaceRecovery,
  "wechatThreadId" | "toolRunId"
>;

export type ExtensionRecoveryState = ExtensionRecoveryInput;

export type ExtensionRecoveryPort = {
  state: ExtensionRecoveryState;
  restore: (recovery: ExtensionRecoveryInput | null) => void;
};

export type ExtensionCoordinatorPort = {
  cancelGroup: () => void;
  invalidateTool: () => void;
  clearToolRun: () => void;
  clearWorkflow: () => void;
};

export type ExtensionViewModel = {
  activeSurface: ExtensionSurfaceId | null;
  activeCapability: ExtensionCapabilityId | null;
  selectCapability: (capability: ExtensionCapabilityId) => void;
  backToLab: () => void;
  activeQuery: string;
  group: {
    wechat: ApiSnapshot["wechat"];
    webLookup: ResearchLookupResponse | null;
    useWebLookup: boolean;
    setUseWebLookup: (enabled: boolean) => void;
    sessionId?: string;
    controller: GroupController;
  };
  tools: {
    toolCount: number;
    controller: ToolController;
  };
  timeline: {
    runs: ApiSnapshot["workflowRuns"];
    controller: WorkflowController;
  };
};

const EXTENSION_DRAWER_CONFIG: Record<
  ExtensionCapabilityId,
  { feature: WorkspaceFeature; label: string }
> = {
  group: { feature: "wechat", label: "群聊" },
  tools: { feature: "tools", label: "工具" },
  timeline: { feature: "workflows", label: "开发者诊断" },
};

export function useExtensionRuntime(options: {
  snapshot: ApiSnapshot;
  setSnapshot: Dispatch<SetStateAction<ApiSnapshot>>;
  refresh: () => Promise<void>;
  loadFeature: FeatureLoader;
  input: string;
  operationError: Dispatch<SetStateAction<string>>;
  lastRagQuery?: string;
  chatSettings: ChatSettings;
  ragSettings: RagSettings;
  ragEnabled: boolean;
  webLookup: ExtensionEvidenceViewPort;
}) {
  const { state, dispatch } = useWorkspace();
  const activeSurface = selectExtensionSurface(state.activeDrawer);
  const [selectedCapability, setSelectedCapability] =
    useState<ExtensionCapabilityId | null>(null);
  const activeCapability = resolveExtensionCapability(
    activeSurface,
    selectedCapability,
  );
  const setGroupThreadId = useCallback(
    (threadId?: string) =>
      dispatch({ type: "SET_ACTIVE_GROUP_THREAD", threadId }),
    [dispatch],
  );
  const setToolRunId = useCallback(
    (runId?: string) => dispatch({ type: "SET_ACTIVE_TOOL_RUN", runId }),
    [dispatch],
  );
  const selectCapability = useCallback(
    (capability: ExtensionCapabilityId) => setSelectedCapability(capability),
    [],
  );
  const backToLab = useCallback(() => setSelectedCapability(null), []);

  const workflowController = useWorkflowController();
  const groupController = useGroupChatController({
    wechat: options.snapshot.wechat,
    setWechat: (wechat) =>
      options.setSnapshot((current) => ({ ...current, wechat })),
    chatSettings: options.chatSettings,
    ragSettings: options.ragSettings,
    ragEnabled: options.ragEnabled,
  });
  const groupThreadId = groupController.threadId;
  const activeQuery = selectActiveQuery({
    input: options.input,
    lastRagQuery: options.lastRagQuery,
  });
  const currentToolInvocation: LocalKnowledgeInvocation = {
    query: activeQuery,
    retrievalMode: options.ragSettings.retrievalMode,
    topK: options.ragSettings.chatTopK,
    minScore: options.ragSettings.minScore,
  };
  const toolController = useToolController({
    invocation: currentToolInvocation,
    activeRunId: state.activeToolRunId,
    setActiveRunId: setToolRunId,
    onCalled: options.refresh,
  });

  useEffect(() => {
    if (activeSurface !== "lab") setSelectedCapability(null);
  }, [activeSurface]);

  useEffect(() => {
    const serverThreadId = options.snapshot.wechat?.group_thread_id;
    if (serverThreadId && state.activeGroupThreadId !== serverThreadId) {
      setGroupThreadId(serverThreadId);
    }
  }, [
    options.snapshot.wechat?.group_thread_id,
    state.activeGroupThreadId,
    setGroupThreadId,
  ]);

  useEffect(() => {
    if (!activeCapability) return;
    const config = EXTENSION_DRAWER_CONFIG[activeCapability];
    let active = true;
    const load = async () => {
      try {
        if (config.feature === "wechat") {
          await options.loadFeature(config.feature, { groupThreadId });
        } else {
          await options.loadFeature(config.feature);
        }
      } catch (error) {
        if (!active) return;
        options.operationError(
          `${config.label}加载失败：${error instanceof Error ? error.message : "读取失败"}`,
        );
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [activeCapability, options.loadFeature]);

  const restore = useCallback(
    (recovery: ExtensionRecoveryInput | null) => {
      if (!recovery) return;
      if (recovery.wechatThreadId) {
        setGroupThreadId(recovery.wechatThreadId);
      }
      if (recovery.toolRunId) {
        setToolRunId(recovery.toolRunId);
      }
    },
    [setGroupThreadId, setToolRunId],
  );
  const recovery = useMemo<ExtensionRecoveryPort>(
    () => ({
      state: {
        wechatThreadId: groupThreadId,
        toolRunId: state.activeToolRunId,
      },
      restore,
    }),
    [groupThreadId, state.activeToolRunId, restore],
  );
  const coordinator = useMemo<ExtensionCoordinatorPort>(
    () => ({
      cancelGroup: groupController.cancelWorkspace,
      invalidateTool: () => operationRegistry.invalidate("tool"),
      clearToolRun: () => setToolRunId(undefined),
      clearWorkflow: workflowController.clear,
    }),
    [
      groupController.cancelWorkspace,
      setToolRunId,
      workflowController.clear,
    ],
  );
  const view: ExtensionViewModel = {
    activeSurface,
    activeCapability,
    selectCapability,
    backToLab,
    activeQuery,
    group: {
      wechat: options.snapshot.wechat,
      webLookup: options.webLookup.result,
      useWebLookup: options.webLookup.useInChat,
      setUseWebLookup: options.webLookup.setUseInChat,
      sessionId: groupThreadId,
      controller: groupController,
    },
    tools: {
      toolCount: options.snapshot.tools.length,
      controller: toolController,
    },
    timeline: {
      runs: options.snapshot.workflowRuns,
      controller: workflowController,
    },
  };

  return {
    view,
    recovery,
    coordinator,
  };
}

export type ExtensionRuntime = ReturnType<typeof useExtensionRuntime>;
