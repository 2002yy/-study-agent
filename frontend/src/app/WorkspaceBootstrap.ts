import { useCallback, useEffect, useState } from "react";

import type { ApiSnapshot } from "../types";
import { serverQueryCache } from "./serverQueryCache";
import {
  loadCoreWorkspaceSnapshot,
  loadWorkspaceFeature,
  type WorkspaceFeature,
} from "./workspaceDataLoader";

const EMPTY_SNAPSHOT: ApiSnapshot = {
  health: null,
  ragStatus: null,
  tools: [],
  workflowRuns: [],
  sessions: [],
  runtimeSettings: null,
  memoryStatus: null,
  wechat: null,
  error: "",
  errors: {},
};

export function useWorkspaceBootstrap() {
  const [snapshot, setSnapshot] = useState<ApiSnapshot>(EMPTY_SNAPSHOT);
  const refresh = useCallback(async () => {
    const core = await serverQueryCache.query(
      "snapshot:core",
      loadCoreWorkspaceSnapshot,
      1_500,
    );
    setSnapshot((current) => ({ ...current, ...core }));
  }, []);
  const loadFeature = useCallback(
    async (
      feature: WorkspaceFeature,
      options: { groupThreadId?: string } = {},
    ) => {
      const suffix = options.groupThreadId ? `:${options.groupThreadId}` : "";
      const patch = await serverQueryCache.query(
        `snapshot:feature:${feature}${suffix}`,
        () => loadWorkspaceFeature(feature, options),
        1_500,
      );
      setSnapshot((current) => ({ ...current, ...patch }));
      return patch;
    },
    [],
  );

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { snapshot, setSnapshot, refresh, loadFeature };
}
