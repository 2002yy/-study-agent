// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen, type RenderResult } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SemanticSessionRow } from "../sessions/sessionNavigation";
import type { TaskIntent } from "../task/taskContract";
import { RestoreCard } from "./RestoreCard";

type RenderOptions = {
  session?: SemanticSessionRow | null;
  streamRecovery?: {
    question: string;
    reply: string;
    reason: string;
    sessionId?: string;
    turnId?: string | null;
  } | null;
  onSelectEntry?: (intent: TaskIntent, prompt: string) => void;
  onContinueHere?: (prompt: string) => void;
  onContinueInterrupted?: () => void;
  onRetryInterrupted?: () => void;
  onAbandonInterrupted?: () => Promise<void> | void;
};

function renderCard(options: RenderOptions = {}): RenderResult {
  return render(
    <RestoreCard
      session={options.session ?? null}
      streamRecovery={options.streamRecovery ?? null}
      onSelectEntry={options.onSelectEntry ?? (() => undefined)}
      onUpload={() => undefined}
      onContinueHere={options.onContinueHere ?? (() => undefined)}
      onStartNewTopic={() => undefined}
      onContinueInterrupted={options.onContinueInterrupted ?? (() => undefined)}
      onRetryInterrupted={options.onRetryInterrupted ?? (() => undefined)}
      onAbandonInterrupted={options.onAbandonInterrupted ?? (() => undefined)}
    />,
  );
}

afterEach(() => cleanup());

describe("RestoreCard", () => {
  it("keeps direct input primary and shows only learning plus upload by default", () => {
    const onSelectEntry = vi.fn<(intent: TaskIntent, prompt: string) => void>();
    renderCard({ onSelectEntry });

    expect(screen.getByRole("heading", { name: "直接输入问题即可开始" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: /快速问答/ })).toBeNull();
    expect(screen.getByRole("button", { name: /系统学习/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /上传资料/ })).toBeTruthy();
    expect(screen.getByRole("button", { name: /联网研究/, hidden: true })).not.toBeVisible();
    expect(screen.getByRole("button", { name: /项目推进/, hidden: true })).not.toBeVisible();

    fireEvent.click(screen.getByRole("button", { name: /系统学习/ }));
    expect(onSelectEntry).toHaveBeenCalledWith("learn", "我想系统学习：");
  });

  it("keeps explicit research and project overrides in a secondary disclosure", () => {
    const onSelectEntry = vi.fn<(intent: TaskIntent, prompt: string) => void>();
    renderCard({ onSelectEntry });

    fireEvent.click(screen.getByText("更多开始方式"));
    const research = screen.getByRole("button", { name: /联网研究/ });
    const project = screen.getByRole("button", { name: /项目推进/ });
    expect(research).toBeVisible();
    expect(project).toBeVisible();

    fireEvent.click(research);
    fireEvent.click(project);
    expect(onSelectEntry).toHaveBeenNthCalledWith(1, "research", "请联网研究：");
    expect(onSelectEntry).toHaveBeenNthCalledWith(2, "project_execution", "我想推进这个项目：");
  });

  it("shows committed learning restore facts for returning users", () => {
    const onContinueHere = vi.fn<(prompt: string) => void>();
    const session: SemanticSessionRow = {
      session_id: "session-learning",
      kind: "current",
      name: "session-learning.md",
      path: "",
      size_bytes: 0,
      mtime_ns: 0,
      title: "二分查找复习",
      task_intent: "learn",
      objective: "理解二分查找复杂度",
      unresolved_gap: "边界条件",
      confirmed_points: ["区间每轮减半"],
      next_action: "完成一次边界迁移练习",
      has_completed_turns: true,
      summary: {
        thread_id: "session-learning",
        status: "needs_update",
        can_summarize: true,
      },
    };
    const { container } = renderCard({ session, onContinueHere });
    const text = container.textContent ?? "";

    expect(text).toContain("理解二分查找复杂度");
    expect(text).toContain("区间每轮减半");
    expect(text).toContain("边界条件");
    expect(text).toContain("完成一次边界迁移练习");
    expect(text).toContain("有新增内容");

    fireEvent.click(screen.getByRole("button", { name: /继续这里/ }));
    expect(onContinueHere).toHaveBeenCalledWith(
      "继续当前任务，下一步是：完成一次边界迁移练习",
    );
  });

  it("shows disclosed sources instead of mastery points for research", () => {
    const session: SemanticSessionRow = {
      session_id: "session-research",
      kind: "current",
      name: "session-research.md",
      path: "",
      size_bytes: 0,
      mtime_ns: 0,
      title: "Python 研究",
      task_intent: "research",
      research_summary: "核对 Python 发布时间",
      disclosed_sources: [
        { source_id: "s1", type: "web", citation: "Python 官方发布说明" },
      ],
      has_completed_turns: true,
    };
    const { container } = renderCard({ session });
    const text = container.textContent ?? "";

    expect(text).toContain("已披露来源");
    expect(text).toContain("Python 官方发布说明");
    expect(text).not.toContain("已确认点");
  });

  it("prioritizes interrupted recovery actions over normal session restore", () => {
    const onContinueInterrupted = vi.fn<() => void>();
    const onRetryInterrupted = vi.fn<() => void>();
    const onAbandonInterrupted = vi.fn<() => void>();
    const { container } = renderCard({
      session: {
        session_id: "session-1",
        kind: "current",
        name: "session-1.md",
        path: "",
        size_bytes: 0,
        mtime_ns: 0,
        title: "已有会话",
        has_completed_turns: true,
      },
      streamRecovery: {
        question: "问题",
        reply: "部分回答",
        reason: "网络中断",
        sessionId: "session-1",
        turnId: "turn-1",
      },
      onContinueInterrupted,
      onRetryInterrupted,
      onAbandonInterrupted,
    });

    fireEvent.click(screen.getByRole("button", { name: /从断点继续/ }));
    fireEvent.click(screen.getByRole("button", { name: /重新生成/ }));
    fireEvent.click(screen.getByRole("button", { name: /放弃恢复/ }));

    expect(onContinueInterrupted).toHaveBeenCalledTimes(1);
    expect(onRetryInterrupted).toHaveBeenCalledTimes(1);
    expect(onAbandonInterrupted).toHaveBeenCalledTimes(1);
    expect(container.textContent ?? "").not.toContain("已有会话");
  });
});
