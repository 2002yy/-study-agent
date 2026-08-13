// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { WorkspaceTransitionDialog } from "./WorkspaceTransitionDialog";
import type { WorkspaceTransitionNotice } from "./workspaceTransitionGuard";

afterEach(() => cleanup());

const notice: WorkspaceTransitionNotice = {
  kind: "switch",
  title: "切换会话前确认未完成工作",
  description: "逐项说明处理方式。",
  confirmLabel: "仍然切换会话",
  issues: [
    {
      id: "memory_preview",
      label: "学习成果候选尚未确认",
      effect: "未确认内容不会写入长期记忆。",
    },
  ],
};

describe("WorkspaceTransitionDialog", () => {
  it("offers explicit stay and leave actions in an accessible modal", () => {
    const onCancel = vi.fn();
    const onConfirm = vi.fn();
    render(
      <WorkspaceTransitionDialog
        notice={notice}
        onCancel={onCancel}
        onConfirm={onConfirm}
      />,
    );

    expect(screen.getByRole("dialog", { name: notice.title })).toHaveAttribute(
      "aria-modal",
      "true",
    );
    expect(screen.getByText("学习成果候选尚未确认")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "留在当前会话" }));
    expect(onCancel).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByRole("button", { name: "仍然切换会话" }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });
});
