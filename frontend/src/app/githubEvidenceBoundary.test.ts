import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const read = (path: string) =>
  readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8");

const runtimeSources = [
  read("./WorkspaceRuntime.tsx"),
  read("./useEvidenceRuntime.ts"),
  read("./useWorkspaceControllers.ts"),
];
const evidenceHelpers = read("../features/evidence/evidenceHelpers.ts");
const evidenceTrail = read("../features/evidence/EvidenceTrail.tsx");
const journeyAudit = read("../product-flow/goldenJourneyAudit.ts");

describe("GitHub source-learning evidence boundary", () => {
  it("keeps source learning on the generic server evidence contract", () => {
    expect(evidenceHelpers).toContain(
      'const SERVER_EVIDENCE_SCHEMA = "evidence-snapshot-v1"',
    );
    expect(evidenceHelpers).toContain("function serverEvidenceRefs(");
    expect(evidenceTrail).toContain("normalizeEvidence(evidence)");
    expect(journeyAudit).toContain("GitHub 源码学习 -> 阅读源码 -> 回到学习目标");
  });

  it("does not create a second GitHub-specific runtime or durable owner", () => {
    const combined = runtimeSources.join("\n");
    for (const forbiddenOwner of [
      "GitHubEvidenceRuntime",
      "GithubEvidenceRuntime",
      "useGitHubController",
      "useGithubController",
      "githubController",
      "activeGitHubRunId",
      "activeGithubRunId",
      "SET_ACTIVE_GITHUB_RUN",
      "repositoryUrl",
      "repoUrl",
      "symbolMapping",
    ]) {
      expect(combined).not.toContain(forbiddenOwner);
    }
  });
});
