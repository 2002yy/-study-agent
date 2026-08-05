import { useEffect, useMemo } from "react";
import type { Dispatch, SetStateAction } from "react";

import { useRoleController } from "../features/roles/roleController";
import { useSettingsController } from "../features/settings/settingsController";
import type { ApiSnapshot } from "../types";
import type { EvidenceRuntime } from "./useEvidenceRuntime";
import type { ExtensionRuntime } from "./useExtensionRuntime";
import type { LearningSessionRuntime } from "./useLearningSessionRuntime";
import { operationRegistry } from "./operationRegistry";
import { WorkspaceCoordinator } from "./WorkspaceCoordinator";
import { useWorkspace } from "./WorkspaceProvider";

type ValueSetter<T> = Dispatch<SetStateAction<T>>;
type MemoryFeatureLoader = (
  feature: "memory",
) => Promise<Partial<ApiSnapshot>>;

export function useWorkspaceControllers(options: {
  setSnapshot: React.Dispatch<React.SetStateAction<ApiSnapshot>>;
  refresh: () => Promise<void>;
  loadFeature: MemoryFeatureLoader;
  operationError: ValueSetter<string>;
  evidence: EvidenceRuntime;
  learning: LearningSessionRuntime;
  extension: ExtensionRuntime;
}) {
  const { state } = useWorkspace();
  const {
    ragEnabled,
    ragSettings,
    webLookupController,
    ragController,
    uploadController,
  } = options.evidence;
  const {
    chatSettings,
    memoryController,
    chatController,
  } = options.learning;
  const extensionCoordinator = options.extension.coordinator;
  const roleController = useRoleController(chatSettings.selectedRole);
  const settingsController = useSettingsController({
    chatSettings,
    ragSettings,
    ragEnabled,
    setRuntimeSettings: (runtimeSettings) =>
      options.setSnapshot((current) => ({ ...current, runtimeSettings })),
    setOperationError: options.operationError,
    refresh: options.refresh,
  });
  const workspaceCoordinator = useMemo(
    () =>
      new WorkspaceCoordinator(
        {
          cancelChat: () => operationRegistry.invalidate("chat"),
          cancelGroup: extensionCoordinator.cancelGroup,
          cancelWebLookup: webLookupController.cancel,
          invalidateTool: extensionCoordinator.invalidateTool,
        },
        {
          clearRag: ragController.clear,
          clearToolRun: extensionCoordinator.clearToolRun,
          clearWorkflow: extensionCoordinator.clearWorkflow,
        },
      ),
    [
      extensionCoordinator,
      webLookupController.cancel,
      ragController.clear,
    ],
  );

  useEffect(
    () =>
      options.learning.bindArtifactPort({
        clearChatArtifacts:
          workspaceCoordinator.clearChatArtifacts.bind(workspaceCoordinator),
      }),
    [options.learning.bindArtifactPort, workspaceCoordinator],
  );

  useEffect(() => {
    if (state.activeDrawer !== "memory") return;
    let active = true;
    const load = async () => {
      try {
        await options.loadFeature("memory");
      } catch (error) {
        if (!active) return;
        options.operationError(
          `学习成果加载失败：${error instanceof Error ? error.message : "读取失败"}`,
        );
      }
    };
    void load();
    return () => {
      active = false;
    };
  }, [state.activeDrawer, options.loadFeature]);

  return {
    roleController,
    settingsController,
    webLookupController,
    memoryController,
    ragController,
    uploadController,
    chatController,
  };
}
