import {
  useCallback,
  useEffect,
  useMemo,
  type Dispatch,
  type SetStateAction,
} from "react";

import type { LocalKnowledgeInvocation } from "../api";
import { useGroupChatController } from "../features/group-chat/groupChatController";
import { useToolController } from "../features/tools/toolController";
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
}) {
  const { state, dispatch } = useWorkspace();
  const setGroupThreadId = useCallback(
    (threadId?: string) =>
      dispatch({ type: "SET_ACTIVE_GROUP_THREAD", threadId }),
    [dispatch],
  );
  const setToolRunId = useCallback(
    (runId?: string) => dispatch({ type: "SET_ACTIVE_TOOL_RUN", runId }),
    [dispatch],
  );

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
    const drawer = state.activeDrawer;
    if (!drawer || !["group", "tools", "timeline"].includes(drawer)) return;
    let active = true;
    const load = async () => {
      try {
        if (drawer === "group") {
          await options.loadFeature("wechat", { groupThreadId });
        } else if (drawer === "tools") {
          await options.loadFeature("tools");
        } else if (drawer === "timeline") {
          await options.loadFeature("workflows");
        }
      } catch (error) {
        if (!active) return;
        const label =
          drawer === "group"
            ? "群聊"
            : drawer === "tools"
              ? "工具"
              : "开发者诊断";
        options.operationError(
          `${label}加载失败：${error instanceof Error ? error.message : "读取失败"}`,
        );
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [state.activeDrawer, options.loadFeature]);

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

  return {
    activeQuery,
    groupThreadId,
    groupController,
    toolController,
    workflowController,
    recovery,
    coordinator,
  };
}

export type ExtensionRuntime = ReturnType<typeof useExtensionRuntime>;
