import { useRef, useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { useWorkspaceBootstrap } from "./WorkspaceBootstrap";
import {
  CHAT_SETTINGS_DEFAULTS,
  RAG_SETTINGS_DEFAULTS,
} from "../features/settings/SettingsPanel";
import { useResetResearchSelectionOnSessionChange } from "./useResetResearchSelectionOnSessionChange";
import { useWorkspaceControllers } from "./useWorkspaceControllers";
import { useWorkspaceRecovery } from "./useWorkspaceRecovery";
import { WorkspaceView } from "./WorkspaceView";
import type {
  ChatSettings,
  RagSettings
} from "../types";

export default function WorkspaceRuntime() {
  const { snapshot, setSnapshot, refresh, loadFeature } = useWorkspaceBootstrap();
  const { state: workspaceRuntime, dispatch: dispatchWorkspace } = useWorkspace();
  const [input, setInput] = useState("");
  const [ragEnabled, setRagEnabled] = useState(true);
  const [chatSettings, setChatSettings] = useState<ChatSettings>(CHAT_SETTINGS_DEFAULTS);
  const [ragSettings, setRagSettings] = useState<RagSettings>(RAG_SETTINGS_DEFAULTS);
  const [keepCurrentRole, setKeepCurrentRole] = useState(false);
  const [conversationInstruction, setConversationInstruction] = useState("");
  const toolRunId = workspaceRuntime.activeToolRunId;
  const memoryRunId = workspaceRuntime.activeMemoryRunId;
  const learningClosureRunId = workspaceRuntime.activeLearningClosureRunId;
  const ragQueryRunId = workspaceRuntime.activeRagQueryRunId;
  const ragWriteRunId = workspaceRuntime.activeRagWriteRunId;
  const webLookupRunId = workspaceRuntime.activeWebLookupRunId;
  const setWechatThreadId = (threadId?: string) => dispatchWorkspace({ type: "SET_ACTIVE_GROUP_THREAD", threadId });
  const setToolRunId = (runId?: string) => dispatchWorkspace({ type: "SET_ACTIVE_TOOL_RUN", runId });
  const setMemoryRunId = (runId?: string) => dispatchWorkspace({ type: "SET_ACTIVE_MEMORY_RUN", runId });
  const setLearningClosureRunId = (runId?: string) => dispatchWorkspace({ type: "SET_ACTIVE_LEARNING_CLOSURE_RUN", runId });
  const setRagQueryRunId = (runId?: string) => dispatchWorkspace({ type: "SET_ACTIVE_RAG_QUERY_RUN", runId });
  const setRagWriteRunId = (runId?: string) => dispatchWorkspace({ type: "SET_ACTIVE_RAG_WRITE_RUN", runId });
  const setWebLookupRunId = (runId?: string) => dispatchWorkspace({ type: "SET_ACTIVE_WEB_LOOKUP_RUN", runId });
  const [operationError, setOperationError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const controllers = useWorkspaceControllers({
    snapshot,
    setSnapshot,
    refresh,
    loadFeature,
    input,
    setInput,
    chatSettings,
    setChatSettings,
    ragSettings,
    setRagSettings,
    ragEnabled,
    setRagEnabled,
    keepCurrentRole,
    setKeepCurrentRole,
    conversationInstruction,
    setConversationInstruction,
    operationError: setOperationError,
    activeGroupThreadId: workspaceRuntime.activeGroupThreadId,
    runIds: {
      tool: toolRunId, memory: memoryRunId,
      learningClosure: learningClosureRunId,
      ragQuery: ragQueryRunId, ragWrite: ragWriteRunId,
      webLookup: webLookupRunId,
    },
    setGroupThreadId: setWechatThreadId,
    setRunId: {
      tool: setToolRunId, memory: setMemoryRunId,
      learningClosure: setLearningClosureRunId,
      ragQuery: setRagQueryRunId, ragWrite: setRagWriteRunId,
      webLookup: setWebLookupRunId,
    },
  });
  const {
    groupThreadId: wechatThreadId,
    chatController,
    webLookupController,
  } = controllers;

  useResetResearchSelectionOnSessionChange(
    workspaceRuntime.activeChatThreadId,
    webLookupController.setUseInChat,
  );

  useWorkspaceRecovery({
    snapshot,
    chatController,
    ids: {
      singleChat: chatController.threadId,
      group: wechatThreadId,
      tool: toolRunId,
      memory: memoryRunId,
      learningClosure: learningClosureRunId,
      ragQuery: ragQueryRunId,
      ragWrite: ragWriteRunId,
      webLookup: webLookupRunId,
    },
    setIds: {
      group: setWechatThreadId,
      tool: setToolRunId,
      memory: setMemoryRunId,
      learningClosure: setLearningClosureRunId,
      ragQuery: setRagQueryRunId,
      ragWrite: setRagWriteRunId,
      webLookup: setWebLookupRunId,
    },
    chatSettings,
    setChatSettings,
    ragSettings,
    setRagSettings,
    ragEnabled,
    setRagEnabled,
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
        ragEnabled,
        setRagEnabled,
        chatSettings,
        setChatSettings,
        ragSettings,
        setRagSettings,
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
