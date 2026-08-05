import type { DrawerId } from "../../types";

export const EXTENSION_DRAWERS = ["group", "tools", "timeline"] as const;

export type ExtensionDrawerId = (typeof EXTENSION_DRAWERS)[number];

export function selectExtensionDrawer(
  drawer: DrawerId | null | undefined,
): ExtensionDrawerId | null {
  return EXTENSION_DRAWERS.includes(drawer as ExtensionDrawerId)
    ? (drawer as ExtensionDrawerId)
    : null;
}
