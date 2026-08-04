import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const runtimeSource = readFileSync(
  fileURLToPath(new URL("./WorkspaceRuntime.tsx", import.meta.url)),
  "utf8"
);
const recoverySource = readFileSync(
  fileURLToPath(new URL("./useWorkspaceRecovery.ts", import.meta.url)),
  "utf8"
);
const evidenceSource = readFileSync(
  fileURLToPath(new URL("./useEvidenceRuntime.ts", import.meta.url)),
  "utf8"
);
const viewSource = readFileSync(
  fileURLToPath(new URL("./WorkspaceView.tsx", import.meta.url)),
  "utf8"
);
const recoveryCall = runtimeSource.slice(
  runtimeSource.indexOf("useWorkspaceRecovery({"),
  runtimeSource.indexOf("\n\n  return ("),
);

describe("workspace recovery and view boundaries", () => {
  it("owns restore, server hydration and persistence outside Runtime", () => {
    for (const token of [
      "useWorkspacePersistence({",
      "hydrateSession(",
      "runtimeSettings?.settings",
      "sessionSettingsRestoredRef",
    ]) {
      expect(recoverySource).toContain(token);
      expect(runtimeSource).not.toContain(token);
    }
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
