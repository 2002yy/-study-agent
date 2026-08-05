import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const runtimeSource = readFileSync(
  fileURLToPath(new URL("./WorkspaceRuntime.tsx", import.meta.url)),
  "utf8",
);
const recoverySource = readFileSync(
  fileURLToPath(new URL("./useWorkspaceRecovery.ts", import.meta.url)),
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
const viewSource = readFileSync(
  fileURLToPath(new URL("./WorkspaceView.tsx", import.meta.url)),
  "utf8",
);
const recoveryCall = runtimeSource.slice(
  runtimeSource.indexOf("useWorkspaceRecovery({"),
  runtimeSource.indexOf("\n\n  return ("),
);

describe("workspace recovery and view boundaries", () => {
  it("owns persistence orchestration outside Runtime while Learning owns chat hydration", () => {
    for (const token of [
      "useWorkspacePersistence({",
      "sessionSettingsRestoredRef",
    ]) {
      expect(recoverySource).toContain(token);
      expect(runtimeSource).not.toContain(token);
    }
    expect(recoverySource).toContain("runtimeSettings?.settings");
    expect(runtimeSource).toContain(
      "snapshot.runtimeSettings?.settings?.web_policy",
    );
    expect(runtimeSource).not.toContain("hydrateRuntimeSettings(");
    expect(learningSource).toContain("chatController.hydrateSession(");
    expect(recoverySource).not.toContain("hydrateSession(");
    expect(runtimeSource).not.toContain("hydrateSession(");
  });

  it("consumes one evidence recovery port instead of evidence setters", () => {
    expect(recoveryCall).toContain("evidence: evidence.recovery");
    for (const leakedBinding of [
      "ragQuery: evidence.ragQueryRunId",
      "ragWrite: evidence.ragWriteRunId",
      "webLookup: evidence.webLookupRunId",
      "ragQuery: evidence.setRagQueryRunId",
      "ragWrite: evidence.setRagWriteRunId",
      "webLookup: evidence.setWebLookupRunId",
      "ragSettings: evidence.ragSettings",
      "setRagSettings: evidence.setRagSettings",
      "ragEnabled: evidence.ragEnabled",
      "setRagEnabled: evidence.setRagEnabled",
    ]) {
      expect(recoveryCall).not.toContain(leakedBinding);
    }

    expect(recoverySource).toContain("evidence: EvidenceRecoveryPort");
    expect(recoverySource).toContain("evidence.restore({");
    expect(recoverySource).toContain("evidence.hydrateRuntimeSettings(settings)");
    expect(recoverySource).toContain("...evidence.state");
    expect(recoverySource).not.toContain("setRagSettings");
    expect(recoverySource).not.toContain("setRagEnabled");
    expect(recoverySource).not.toContain("setRagQueryRunId");
    expect(recoverySource).not.toContain("setRagWriteRunId");
    expect(recoverySource).not.toContain("setWebLookupRunId");

    expect(evidenceSource).toContain("export type EvidenceRecoveryPort");
    expect(evidenceSource).toContain("const recovery = useMemo<EvidenceRecoveryPort>");
    expect(evidenceSource).toContain("restore,");
    expect(evidenceSource).toContain("hydrateRuntimeSettings,");
  });

  it("consumes one learning recovery port for learning and chat state", () => {
    expect(recoveryCall).toContain("learning: learning.recovery");
    expect(recoveryCall).not.toContain("chatController");
    for (const leakedBinding of [
      "memory: learning.memoryRunId",
      "learningClosure: learning.learningClosureRunId",
      "memory: learning.setMemoryRunId",
      "learningClosure: learning.setLearningClosureRunId",
      "chatSettings: learning.chatSettings",
      "setChatSettings: learning.setChatSettings",
      "keepCurrentRole: learning.keepCurrentRole",
      "setKeepCurrentRole: learning.setKeepCurrentRole",
      "conversationInstruction: learning.conversationInstruction",
      "setConversationInstruction: learning.setConversationInstruction",
    ]) {
      expect(recoveryCall).not.toContain(leakedBinding);
    }

    expect(recoverySource).toContain("learning: LearningRecoveryPort");
    expect(recoverySource).toContain("learning.restore({");
    expect(recoverySource).toContain("learning.restore(null)");
    expect(recoverySource).toContain("learning.hydrateRuntimeSettings(settings)");
    expect(recoverySource).toContain("...learning.state");
    expect(recoverySource).not.toContain("chatController");
    expect(recoverySource).not.toContain("setChatSettings");
    expect(recoverySource).not.toContain("setKeepCurrentRole");
    expect(recoverySource).not.toContain("setConversationInstruction");
    expect(recoverySource).not.toContain("setMemoryRunId");
    expect(recoverySource).not.toContain("setLearningClosureRunId");

    expect(learningSource).toContain("export type LearningRecoveryPort");
    expect(learningSource).toContain("singleChatSessionId: chatController.threadId");
    expect(learningSource).toContain("cachedMessages: chatController.messages");
    expect(learningSource).toContain("const recovery = useMemo<LearningRecoveryPort>");
    expect(learningSource).toContain("restore,");
    expect(learningSource).toContain("hydrateRuntimeSettings,");
  });

  it("consumes one extension recovery port for group and tool ids", () => {
    expect(recoveryCall).toContain("extension: extension.recovery");
    expect(recoveryCall).not.toContain("setWechatThreadId");
    expect(recoveryCall).not.toContain("setToolRunId");
    expect(recoverySource).toContain("extension: ExtensionRecoveryPort");
    expect(recoverySource).toContain("extension.restore(parsed)");
    expect(recoverySource).toContain("extension.restore(null)");
    expect(recoverySource).toContain("...extension.state");
    expect(recoverySource).not.toContain("setIds");
    expect(extensionSource).toContain("export type ExtensionRecoveryPort");
    expect(extensionSource).toContain("wechatThreadId: groupThreadId");
    expect(extensionSource).toContain("toolRunId: state.activeToolRunId");
    expect(extensionSource).toContain("const recovery = useMemo<ExtensionRecoveryPort>");
  });

  it("owns feature view binding outside Runtime", () => {
    for (const component of [
      "<SettingsPanel",
      "<ChatPanel",
      "<SessionNavigator",
      "<LearningStrip",
      "<SlideOver",
      "<GlobalNotices",
    ]) {
      expect(viewSource).toContain(component);
      expect(runtimeSource).not.toContain(component);
    }
  });
});
