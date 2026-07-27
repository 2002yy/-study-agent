import {
  SessionNavigator,
  type SessionNavigatorProps,
} from "./SessionNavigator";

/**
 * Compatibility adapter for older composition boundaries.
 * SessionNavigator is the only implementation and interaction owner.
 */
export function SessionSidebar(props: Omit<SessionNavigatorProps, "variant">) {
  return <SessionNavigator {...props} variant="sidebar" />;
}
