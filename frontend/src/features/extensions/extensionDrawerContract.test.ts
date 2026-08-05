import { describe, expect, it } from "vitest";

import {
  EXTENSION_DRAWERS,
  resolveExtensionCapability,
  selectExtensionDrawer,
  selectExtensionSurface,
} from "./extensionDrawerContract";

describe("extension drawer contract", () => {
  it("recognizes legacy capability drawers", () => {
    expect(EXTENSION_DRAWERS).toEqual(["group", "tools", "timeline"]);
    expect(selectExtensionDrawer("group")).toBe("group");
    expect(selectExtensionDrawer("tools")).toBe("tools");
    expect(selectExtensionDrawer("timeline")).toBe("timeline");
  });

  it("recognizes the laboratory as the only new extension surface", () => {
    expect(selectExtensionSurface("lab" as never)).toBe("lab");
    expect(selectExtensionSurface("group")).toBe("group");
    expect(selectExtensionSurface("tools")).toBe("tools");
    expect(selectExtensionSurface("timeline")).toBe("timeline");
  });

  it("keeps the laboratory home dormant until a capability is selected", () => {
    expect(resolveExtensionCapability("lab", null)).toBeNull();
    expect(resolveExtensionCapability("lab", "group")).toBe("group");
    expect(resolveExtensionCapability("lab", "tools")).toBe("tools");
    expect(resolveExtensionCapability("lab", "timeline")).toBe("timeline");
    expect(resolveExtensionCapability("group", null)).toBe("group");
  });

  it("keeps ordinary and missing drawers outside Extension loading", () => {
    expect(selectExtensionSurface(null)).toBeNull();
    expect(selectExtensionSurface(undefined)).toBeNull();
    expect(selectExtensionSurface("sessions")).toBeNull();
    expect(selectExtensionSurface("memory")).toBeNull();
    expect(selectExtensionSurface("settings")).toBeNull();
    expect(selectExtensionSurface("sources")).toBeNull();
  });
});
