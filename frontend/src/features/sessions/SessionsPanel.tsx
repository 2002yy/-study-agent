import {
  SessionNavigator,
  type SessionNavigatorProps,
} from "./SessionNavigator";

export { sessionIdFromRow } from "./sessionNavigation";

/**
 * Compatibility adapter for the existing Inspector boundary.
 * SessionNavigator owns search, grouping, rename, restore and archive behavior.
 */
export function SessionsPanel(props: Omit<SessionNavigatorProps, "variant">) {
  return <SessionNavigator {...props} variant="panel" />;
}
