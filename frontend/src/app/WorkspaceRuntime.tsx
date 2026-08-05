import { useRef, useState } from "react";
import { useWorkspace } from "./WorkspaceProvider";
import { useWorkspaceBootstrap } from "./WorkspaceBootstrap";
import { useEvidenceRuntime } from "./useEvidenceRuntime";
import { useExtensionRuntime } from "./useExtensionRuntime";
import { useLearningSessionRuntime } from "./useLearningSessionRuntime";
import { useWorkspaceControllers } from "./useWorkspaceControllers";
import { useWorkspaceRecovery } from "./useWorkspaceRecovery";
import { WorkspaceView } from "./WorkspaceView";

export default function WorkspaceRuntime() {
  const { snapshot, setSnapshot, refresh, loadFeature } = useWorkspaceBootstrap();
  const { state: workspaceRuntime } = useWorkspace();
  const [input, setInput] = useState("");
  const [operationError, setOperationError] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const evidence = useEvidenceRuntime({
    refresh,
    loadFeature,
    input,
    activeChatThreadId: workspaceRuntime.activeChatThreadId,
    setOperationError,
  });
  const webPolicy = String(
    snapshot.runtimeSettings?.settings?.web_policy ?? "auto",
  );
  const learning = useLearningSessionRuntime({
    refresh,
    sessions: snapshot.sessions,
    setInput,
    setOperationError,
    evidence: evidence.learning,
    webPolicy,
  });
  const extension = useExtensionRuntime({
    snapshot,
    setSnapshot,
    refresh,
    loadFeature,
    input,
    operationError: setOperationError,
    lastRagQuery: learning.chatController.lastChat?.rag?.query,
    chatSettings: learning.chatSettings,
    ragSettings: evidence.ragSettings,
    ragEnabled: evidence.ragEnabled,
  });
  const controllers = useWorkspaceControllers({
    setSnapshot,
    refresh,
    loadFeature,
    operationError: setOperationError,
    evidence,
    learning,
    extension,
  });

  useWorkspaceRecovery({
    evidence: evidence.recovery,
    learning: learning.recovery,
    extension: extension.recovery,
    snapshot,
  });

  return (
    <WorkspaceView
      snapshot={snapshot}
      refresh={refresh}
      fileInputRef={fileInputRef}
      controllers={controllers}
      learningView={learning.view}
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
