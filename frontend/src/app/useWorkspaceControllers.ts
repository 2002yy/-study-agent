import { useEffect, useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";

import type { LocalKnowledgeInvocation } from "../api";
import { createEmptyRag, useChatController } from "../features/chat/chatController";
import { useGroupChatController } from "../features/group-chat/groupChatController";
import { useMemoryController } from "../features/learning-memory/memoryController";
import { useRoleController } from "../features/roles/roleController";
import {
  CHAT_SETTINGS_DEFAULTS,
  RAG_SETTINGS_DEFAULTS,
} from "../features/settings/SettingsPanel";
import { useSettingsController } from "../features/settings/settingsController";
import { useToolController } from "../features/tools/toolController";
import { useWorkflowController } from "../features/workflows/workflowController";
import type { ApiSnapshot, ChatSettings } from "../types";
import type { EvidenceRuntime } from "./useEvidenceRuntime";
import { operationRegistry } from "./operationRegistry";
import { WorkspaceCoordinator } from "./WorkspaceCoordinator";
import { useWorkspace } from "./WorkspaceProvider";
import type { WorkspaceFeature } from "./workspaceDataLoader";

type ValueSetter<T> = Dispatch<SetStateAction<T>>;
type DirectSetter<T> = (value: T) => void;

type FeatureLoader = (
  feature: WorkspaceFeature,
  options?: { groupThreadId?: string },
) => Promise<Partial<ApiSnapshot>>;

export function useWorkspaceControllers(options: {
  snapshot: ApiSnapshot;
  setSnapshot: React.Dispatch<React.SetStateAction<ApiSnapshot>>;
  refresh: () => Promise<void>;
  loadFeature: FeatureLoader;
  input: string;
  setInput: ValueSetter<string>;
  chatSettings: ChatSettings;
  setChatSettings: ValueSetter<ChatSettings>;
  keepCurrentRole: boolean;
  setKeepCurrentRole: ValueSetter<boolean>;
  conversationInstruction: string;
  setConversationInstruction: ValueSetter<string>;
  operationError: ValueSetter<string>;
  activeGroupThreadId?: string;
  evidence: EvidenceRuntime;
  runIds: {
    tool?: string;
    memory?: string;
    learningClosure?: string;
  };
  setGroupThreadId: DirectSetter<string | undefined>;
  setRunId: {
    tool: DirectSetter<string | undefined>;
    memory: DirectSetter<string | undefined>;
    learningClosure: DirectSetter<string | undefined>;
  };
}) {
  const { state, dispatch } = useWorkspace();
  const {
    ragEnabled,
    setRagEnabled,
    ragSettings,
    setRagSettings,
    webLookupController,
    ragController,
    uploadController,
  } = options.evidence;
  const roleController = useRoleController(options.chatSettings.selectedRole);
  const workflowController = useWorkflowController();
  const settingsController = useSettingsController({
    chatSettings: options.chatSettings,
    ragSettings,
    ragEnabled,
    setRuntimeSettings: (runtimeSettings) =>
      options.setSnapshot((current) => ({ ...current, runtimeSettings })),
    setOperationError: options.operationError,
    refresh: options.refresh,
  });
  const groupThreadId =
    options.activeGroupThreadId ?? options.snapshot.wechat?.group_thread_id;
  const groupController = useGroupChatController({
    wechat: options.snapshot.wechat,
    setWechat: (wechat) =>
      options.setSnapshot((current) => ({ ...current, wechat })),
    chatSettings: options.chatSettings,
    ragSettings,
    ragEnabled,
  });
  const memoryController = useMemoryController({
    activeRunId: options.runIds.memory,
    setActiveRunId: options.setRunId.memory,
    activeClosureRunId: options.runIds.learningClosure,
    setActiveClosureRunId: options.setRunId.learningClosure,
    onMemoryChanged: options.refresh,
    onSummaryChanged: (summary) =>
      dispatch({ type: "SET_SESSION_SUMMARY", summary }),
  });
  const workspaceCoordinator = useMemo(
    () =>
      new WorkspaceCoordinator(
        {
          cancelChat: () => operationRegistry.invalidate("chat"),
          cancelGroup: groupController.cancelWorkspace,
          cancelWebLookup: webLookupController.cancel,
          invalidateTool: () => operationRegistry.invalidate("tool"),
        },
        {
          clearRag: ragController.clear,
          clearToolRun: () => options.setRunId.tool(undefined),
          clearWorkflow: workflowController.clear,
        }
      ),
    [
      groupController.cancelWorkspace,
      webLookupController.cancel,
      ragController.clear,
      workflowController.clear,
      options.setRunId.tool,
    ]
  );
  const runtimeSettings = (options.snapshot.runtimeSettings?.settings ?? {}) as Record<string, unknown>;
  const webPolicy = String(runtimeSettings.web_policy ?? "auto");
  const chatController = useChatController({
    chatSettings: options.chatSettings,
    chatSettingsDefaults: CHAT_SETTINGS_DEFAULTS,
    setChatSettings: options.setChatSettings,
    ragSettings,
    ragSettingsDefaults: RAG_SETTINGS_DEFAULTS,
    setRagSettings,
    ragEnabled,
    setRagEnabled,
    keepCurrentRole: options.keepCurrentRole,
    setKeepCurrentRole: options.setKeepCurrentRole,
    conversationInstruction: options.conversationInstruction,
    setConversationInstruction: options.setConversationInstruction,
    webLookupSource: webLookupController.result?.source_block ?? "",
    webLookupRunId: webLookupController.result?.run_id,
    useWebLookup: webLookupController.useInChat,
    webPolicy,
    setUseWebLookup: webLookupController.setUseInChat,
    setInput: options.setInput,
    setOperationError: options.operationError,
    clearChatArtifacts:
      workspaceCoordinator.clearChatArtifacts.bind(workspaceCoordinator),
    refresh: options.refresh,
    onResearchRunDiscovered: (runId, forceRefresh = false) => {
      options.evidence.setWebLookupRunId(runId);
      if (forceRefresh) void webLookupController.refreshRun(runId);
    },
  });
  const activeQuery =
    options.input.trim() || chatController.lastChat?.rag?.query || "";
  const currentToolInvocation: LocalKnowledgeInvocation = {
    query: activeQuery,
    retrievalMode: ragSettings.retrievalMode,
    topK: ragSettings.chatTopK,
    minScore: ragSettings.minScore,
  };
  const toolController = useToolController({
    invocation: currentToolInvocation,
    activeRunId: options.runIds.tool,
    setActiveRunId: options.setRunId.tool,
    onCalled: options.refresh,
  });

  useEffect(() => {
    const serverThreadId = options.snapshot.wechat?.group_thread_id;
    if (serverThreadId && options.activeGroupThreadId !== serverThreadId) {
      options.setGroupThreadId(serverThreadId);
    }
  }, [
    options.snapshot.wechat?.group_thread_id,
    options.activeGroupThreadId,
    options.setGroupThreadId,
  ]);

  useEffect(() => {
    const drawer = state.activeDrawer;
    if (!drawer || drawer === "sources") return;
    let active = true;
    const load = async () => {
      try {
        if (drawer === "group") {
          await options.loadFeature("wechat", { groupThreadId });
        } else if (drawer === "tools") {
          await options.loadFeature("tools");
        } else if (drawer === "timeline") {
          await options.loadFeature("workflows");
        } else if (drawer === "memory") {
          await options.loadFeature("memory");
        }
      } catch (error) {
        if (!active) return;
        const labels: Partial<Record<typeof drawer, string>> = {
          group: "群聊",
          tools: "工具",
          timeline: "开发者诊断",
          memory: "学习成果",
        };
        options.operationError(
          `${labels[drawer] ?? "功能"}加载失败：${error instanceof Error ? error.message : "读取失败"}`,
        );
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [state.activeDrawer, options.loadFeature]);

  return {
    activeQuery,
    groupThreadId,
    roleController,
    workflowController,
    settingsController,
    groupController,
    webLookupController,
    memoryController,
    ragController,
    uploadController,
    chatController,
    toolController,
    createEmptyRag,
  };
}
