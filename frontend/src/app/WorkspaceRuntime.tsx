import { useRef, useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { useWorkspaceBootstrap } from "./WorkspaceBootstrap";
import { CHAT_SETTINGS_DEFAULTS } from "../features/settings/SettingsPanel";
import { useEvidenceRuntime } from "./useEvidenceRuntime";
import { useWorkspaceControllers } from "./useWorkspaceControllers";
import { useWorkspaceRecovery } from "./useWorkspaceRecovery";
import { WorkspaceView } from "./WorkspaceView";
import type { ChatSettings } from "../types";

export default function WorkspaceRuntime() {
  const { snapshot, setSnapshot, refresh, loadFeature } = useWorkspaceBootstrap();
  const { state: workspaceRuntime, dispatch: dispatchWorkspace } = useWorkspace();
  const [input, setInput] = useState("");
  const [chatSettings, setChatSettings] = useState<ChatSettings>(CHAT_SETTINGS_DEFAULTS);
  const [keepCurrentRole, setKeepCurrentRole] = useState(false);
  const [conversationInstruction, setConversationInstruction] = useState("");
  const [operationError, setOperationError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toolRunId = workspaceRuntime.activeToolRunId;
  const memoryRunId = workspaceRuntime.activeMemoryRunId;
  const learningClosureRunId = workspaceRuntime.activeLearningClosureRunId;
  const setWechatThreadId = (threadId?: string) =>
    dispatchWorkspace({ type: "SET_ACTIVE_GROUP_THREAD", threadId });
  const setToolRunId = (runId?: string) =>
    dispatchWorkspace({ type: "SET_ACTIVE_TOOL_RUN", runId });
  const setMemoryRunId = (runId?: string) =>
    dispatchWorkspace({ type: "SET_ACTIVE_MEMORY_RUN", runId });
  const setLearningClosureRunId = (runId?: string) =>
    dispatchWorkspace({ type: "SET_ACTIVE_LEARNING_CLOSURE_RUN", runId });

  const evidence = useEvidenceRuntime({
    refresh,
    loadFeature,
    input,
    activeChatThreadId: workspaceRuntime.activeChatThreadId,
    setOperationError,
  });
  const controllers = useWorkspaceControllers({
    snapshot,
    setSnapshot,
    refresh,
    loadFeature,
    input,
    setInput,
    chatSettings,
    setChatSettings,
    keepCurrentRole,
    setKeepCurrentRole,
    conversationInstruction,
    setConversationInstruction,
    operationError: setOperationError,
    activeGroupThreadId: workspaceRuntime.activeGroupThreadId,
    evidence,
    runIds: {
      tool: toolRunId,
      memory: memoryRunId,
      learningClosure: learningClosureRunId,
    },
    setGroupThreadId: setWechatThreadId,
    setRunId: {
      tool: setToolRunId,
      memory: setMemoryRunId,
      learningClosure: setLearningClosureRunId,
    },
  });
  const { groupThreadId: wechatThreadId, chatController } = controllers;

  useWorkspaceRecovery({
    snapshot,
    chatController,
    ids: {
      singleChat: chatController.threadId,
      group: wechatThreadId,
      tool: toolRunId,
      memory: memoryRunId,
      learningClosure: learningClosureRunId,
      ragQuery: evidence.ragQueryRunId,
      ragWrite: evidence.ragWriteRunId,
      webLookup: evidence.webLookupRunId,
    },
    setIds: {
      group: setWechatThreadId,
      tool: setToolRunId,
      memory: setMemoryRunId,
      learningClosure: setLearningClosureRunId,
      ragQuery: evidence.setRagQueryRunId,
      ragWrite: evidence.setRagWriteRunId,
      webLookup: evidence.setWebLookupRunId,
    },
    chatSettings,
    setChatSettings,
    ragSettings: evidence.ragSettings,
    setRagSettings: evidence.setRagSettings,
    ragEnabled: evidence.ragEnabled,
    setRagEnabled: evidence.setRagEnabled,
    keepCurrentRole,
    setKeepCurrentRole,
    conversationInstruction,
    setConversationInstruction,
  });

  return (
    <WorkspaceView
      snapshot={snapshot}
      refresh={refresh}
      fileInputRef={fileInputRef}
      controllers={controllers}
      ui={{
        input,
        setInput,
        ragEnabled: evidence.ragEnabled,
        setRagEnabled: evidence.setRagEnabled,
        chatSettings,
        setChatSettings,
        ragSettings: evidence.ragSettings,
        setRagSettings: evidence.setRagSettings,
        keepCurrentRole,
        setKeepCurrentRole,
        conversationInstruction,
        setConversationInstruction,
        operationError,
        setOperationError,
      }}
    />
  );
}
