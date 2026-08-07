import { describe, expect, it } from "vitest";

import {
  EXTENSION_CAPABILITIES,
  resolveExtensionCapability,
  selectExtensionSurface,
} from "./extensionDrawerContract";

describe("extension drawer contract", () => {
  it("keeps capability ids separate from drawer surfaces", () => {
    expect(EXTENSION_CAPABILITIES).toEqual(["group", "tools", "timeline"]);
  });

  it("recognizes laboratory as the only extension drawer surface", () => {
    expect(selectExtensionSurface("lab")).toBe("lab");
    expect(selectExtensionSurface("group" as never)).toBeNull();
    expect(selectExtensionSurface("tools" as never)).toBeNull();
    expect(selectExtensionSurface("timeline" as never)).toBeNull();
  });

  it("keeps laboratory dormant until a capability is selected", () => {
    expect(resolveExtensionCapability("lab", null)).toBeNull();
    expect(resolveExtensionCapability("lab", "group")).toBe("group");
    expect(resolveExtensionCapability("lab", "tools")).toBe("tools");
    expect(resolveExtensionCapability("lab", "timeline")).toBe("timeline");
    expect(resolveExtensionCapability(null, "group")).toBeNull();
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
