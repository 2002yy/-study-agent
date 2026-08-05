import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const runtimeSource = readFileSync(
  fileURLToPath(new URL("./WorkspaceRuntime.tsx", import.meta.url)),
  "utf8",
);
const compositionSource = readFileSync(
  fileURLToPath(new URL("./useWorkspaceControllers.ts", import.meta.url)),
  "utf8",
);
const evidenceSource = readFileSync(
  fileURLToPath(new URL("./useEvidenceRuntime.ts", import.meta.url)),
  "utf8",
);
const learningSource = readFileSync(
  fileURLToPath(new URL("./useLearningSessionRuntime.ts", import.meta.url)),
  "utf8",
);
const extensionSource = readFileSync(
  fileURLToPath(new URL("./useExtensionRuntime.ts", import.meta.url)),
  "utf8",
);

const workspaceControllerHooks = [
  "useRoleController",
  "useSettingsController",
];
const extensionControllerHooks = [
  "useWorkflowController",
  "useGroupChatController",
  "useToolController",
];
const evidenceControllerHooks = [
  "useWebLookupController",
  "useRagController",
  "useUploadController",
];

describe("workspace controller composition boundary", () => {
  it("keeps remaining cross-domain controller construction outside WorkspaceRuntime", () => {
    for (const hook of workspaceControllerHooks) {
      expect(compositionSource).toContain(`${hook}(`);
      expect(runtimeSource).not.toContain(`${hook}(`);
      expect(runtimeSource).not.toMatch(new RegExp(`import .*${hook}`));
    }
  });

  it("makes ExtensionRuntime the only owner of extension controllers and views", () => {
    expect(runtimeSource).toContain("useExtensionRuntime({");
    expect(compositionSource).toContain(
      "const extensionCoordinator = options.extension.coordinator;",
    );
    expect(compositionSource).not.toContain("options.extension.view");
    for (const hook of extensionControllerHooks) {
      expect(extensionSource).toContain(`${hook}(`);
      expect(compositionSource).not.toContain(`${hook}(`);
      expect(runtimeSource).not.toContain(`${hook}(`);
    }
    for (const viewField of [
      "groupController",
      "toolController",
      "workflowController",
      "groupThreadId",
      "activeQuery",
    ]) {
      expect(compositionSource).not.toContain(viewField);
    }
  });

  it("makes EvidenceRuntime the only owner of research, RAG, and upload controllers", () => {
    expect(runtimeSource).toContain("useEvidenceRuntime({");
    for (const hook of evidenceControllerHooks) {
      expect(evidenceSource).toContain(`${hook}(`);
      expect(compositionSource).not.toContain(`${hook}(`);
      expect(runtimeSource).not.toContain(`${hook}(`);
    }
    for (const stateToken of [
      "useState<RagSettings>",
      "activeRagQueryRunId",
      "activeRagWriteRunId",
      "activeWebLookupRunId",
    ]) {
      expect(evidenceSource).toContain(stateToken);
      expect(runtimeSource).not.toContain(stateToken);
    }
    expect(evidenceSource).toContain("export type EvidenceLearningPort");
    expect(evidenceSource).toContain("const learning = useMemo<EvidenceLearningPort>");
  });

  it("makes LearningSessionRuntime the owner of chat, learning settings, closure runs, and MemoryController", () => {
    expect(runtimeSource).toContain("useLearningSessionRuntime({");
    expect(learningSource).toContain("useMemoryController({");
    expect(learningSource).toContain("useChatController({");
    expect(compositionSource).not.toContain("useMemoryController(");
    expect(compositionSource).not.toContain("useChatController(");
    expect(runtimeSource).not.toContain("useMemoryController(");
    expect(runtimeSource).not.toContain("useChatController(");
    expect(compositionSource).toContain("} = options.learning;");
    expect(compositionSource).toContain("memoryController,");
    expect(compositionSource).toContain("chatController,");

    for (const stateToken of [
      "useState<ChatSettings>",
      "activeMemoryRunId",
      "activeLearningClosureRunId",
      "SET_SESSION_SUMMARY",
    ]) {
      expect(learningSource).toContain(stateToken);
      expect(runtimeSource).not.toContain(stateToken);
      expect(compositionSource).not.toContain(stateToken);
    }
    for (const leakedSetter of [
      "setMemoryRunId",
      "setLearningClosureRunId",
      "setKeepCurrentRole",
      "setConversationInstruction",
    ]) {
      expect(runtimeSource).not.toContain(`const ${leakedSetter}`);
    }
  });

  it("loads the Sources drawer through EvidenceRuntime", () => {
    expect(evidenceSource).toContain('state.activeDrawer !== "sources"');
    expect(evidenceSource).toContain('options.loadFeature("rag")');
    expect(evidenceSource).toContain("uploadController.refreshDocuments()");
    expect(compositionSource).not.toContain('options.loadFeature("rag")');
    expect(compositionSource).not.toContain("refreshDocuments()");
  });

  it("does not rebuild the retired NewsController in the main workspace", () => {
    expect(compositionSource).not.toContain("useNewsController");
    expect(compositionSource).not.toContain("newsController");
    expect(evidenceSource).not.toContain("useNewsController");
    expect(learningSource).not.toContain("useNewsController");
    expect(extensionSource).not.toContain("useNewsController");
    expect(runtimeSource).not.toContain("useNewsController");
  });

  it("owns cross-feature coordination while consuming narrow extension ports", () => {
    expect(compositionSource).toContain("new WorkspaceCoordinator(");
    expect(compositionSource).toContain("options.extension.coordinator");
    expect(compositionSource).toContain("options.learning.bindArtifactPort({");
    expect(compositionSource).toContain("clearChatArtifacts:");
    expect(compositionSource).toContain('cancelChat: () => operationRegistry.invalidate("chat")');
    expect(compositionSource).not.toContain("onWorkspaceCancelled:");
    expect(compositionSource).not.toContain("operationRegistry.cancelAll()");
    expect(runtimeSource).not.toContain("new WorkspaceCoordinator(");
    expect(evidenceSource).not.toContain("new WorkspaceCoordinator(");
    expect(learningSource).not.toContain("new WorkspaceCoordinator(");
    expect(extensionSource).not.toContain("new WorkspaceCoordinator(");
  });
});
