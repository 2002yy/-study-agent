import { useRef, useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { useWorkspaceBootstrap } from "./WorkspaceBootstrap";
import { useEvidenceRuntime } from "./useEvidenceRuntime";
import { useLearningSessionRuntime } from "./useLearningSessionRuntime";
import { useWorkspaceControllers } from "./useWorkspaceControllers";
import { useWorkspaceRecovery } from "./useWorkspaceRecovery";
import { WorkspaceView } from "./WorkspaceView";

export default function WorkspaceRuntime() {
  const { snapshot, setSnapshot, refresh, loadFeature } = useWorkspaceBootstrap();
  const { state: workspaceRuntime, dispatch: dispatchWorkspace } = useWorkspace();
  const [input, setInput] = useState("");
  const [operationError, setOperationError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const toolRunId = workspaceRuntime.activeToolRunId;
  const setWechatThreadId = (threadId?: string) =>
    dispatchWorkspace({ type: "SET_ACTIVE_GROUP_THREAD", threadId });
  const setToolRunId = (runId?: string) =>
    dispatchWorkspace({ type: "SET_ACTIVE_TOOL_RUN", runId });

  const evidence = useEvidenceRuntime({
    refresh,
    loadFeature,
    input,
    activeChatThreadId: workspaceRuntime.activeChatThreadId,
    setOperationError,
  });
  const learning = useLearningSessionRuntime({ refresh });
  const controllers = useWorkspaceControllers({
    snapshot,
    setSnapshot,
    refresh,
    loadFeature,
    input,
    setInput,
    operationError: setOperationError,
    activeGroupThreadId: workspaceRuntime.activeGroupThreadId,
    evidence,
    learning,
    runIds: {
      tool: toolRunId,
    },
    setGroupThreadId: setWechatThreadId,
    setRunId: {
      tool: setToolRunId,
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
    },
    setIds: {
      group: setWechatThreadId,
      tool: setToolRunId,
    },
    evidence: evidence.recovery,
    learning: learning.recovery,
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
        chatSettings: learning.chatSettings,
        setChatSettings: learning.setChatSettings,
        ragSettings: evidence.ragSettings,
        setRagSettings: evidence.setRagSettings,
        keepCurrentRole: learning.keepCurrentRole,
        setKeepCurrentRole: learning.setKeepCurrentRole,
        conversationInstruction: learning.conversationInstruction,
        setConversationInstruction: learning.setConversationInstruction,
        operationError,
        setOperationError,
      }}
    />
  );
}
