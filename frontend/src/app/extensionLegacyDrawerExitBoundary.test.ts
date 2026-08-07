import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const sourceOf = (relativePath: string) => {
  const path = fileURLToPath(new URL(relativePath, import.meta.url));
  return existsSync(path) ? readFileSync(path, "utf8") : "";
};

const typesSource = sourceOf("../types.ts");
const contractSource = sourceOf("../features/extensions/extensionDrawerContract.ts");
const runtimeSource = sourceOf("./useExtensionRuntime.ts");
const drawersSource = sourceOf("./ExtensionDrawers.tsx");
const launcherSource = sourceOf("../features/extensions/ExtensionLauncher.tsx");

function drawerTypeBlock() {
  return typesSource.split("export type DrawerId =", 2)[1]?.split(";", 1)[0] ?? "";
}

describe("legacy extension drawer exit boundary", () => {
  it("makes laboratory the only extension DrawerId surface", () => {
    const drawerIds = drawerTypeBlock();
    expect(drawerIds).toContain('"lab"');
    expect(drawerIds).not.toContain('"group"');
    expect(drawerIds).not.toContain('"tools"');
    expect(drawerIds).not.toContain('"timeline"');
  });

  it("does not keep legacy drawer restoration adapters", () => {
    expect(contractSource).toContain('export const LAB_DRAWER: DrawerId = "lab"');
    expect(contractSource).not.toContain("selectExtensionDrawer");
    expect(contractSource).not.toContain("legacy capability drawer");
    expect(runtimeSource).not.toContain("isLegacySurface");
    expect(runtimeSource).not.toContain("selectExtensionDrawer");
    expect(drawersSource).not.toContain("isLegacySurface");
  });

  it("keeps live experimental capability owners behind the laboratory", () => {
    expect(runtimeSource).toContain('from "../features/group-chat/groupChatController"');
    expect(runtimeSource).toContain('from "../features/tools/toolController"');
    expect(runtimeSource).toContain('from "../features/workflows/workflowController"');
    expect(runtimeSource).toContain("if (!activeCapability) return;");
    expect(launcherSource).toContain("onOpen(LAB_DRAWER");
    expect(launcherSource).not.toContain('onOpen("group"');
    expect(launcherSource).not.toContain('onOpen("tools"');
    expect(launcherSource).not.toContain('onOpen("timeline"');
  });
});
