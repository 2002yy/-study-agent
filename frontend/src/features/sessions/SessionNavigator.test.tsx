// @vitest-environment jsdom

import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { SessionRow } from "../../types";
import { SessionNavigator } from "./SessionNavigator";

vi.mock("./sessionApi", () => ({
  updateSessionTitle: vi.fn().mockResolvedValue({}),
}));

const sessions: SessionRow[] = [
  {
    session_id: "chat-active",
    kind: "current",
    name: "chat-active.md",
    path: "",
    size_bytes: 10,
    mtime_ns: 2,
    title: "索引激活学习",
    objective: "理解 active 与 staging 的边界",
    unresolved_gap: "解释失败不激活",
    task_intent: "learn",
  } as SessionRow,
  {
    session_id: "chat-history",
    kind: "archived",
    name: "history.md",
    path: "",
    size_bytes: 10,
    mtime_ns: 1,
    title: "证据充分性",
    objective: "练习拒答判断",
    task_intent: "explain_back",
  } as SessionRow,
];

afterEach(() => cleanup());

describe("SessionNavigator", () => {
  it("owns search and restore behavior for both presentation variants", () => {
    const onRestore = vi.fn();
    render(
      <SessionNavigator
        activeSessionId="chat-active"
        onRestore={onRestore}
        sessions={sessions}
        variant="panel"
      />,
    );

    fireEvent.change(screen.getByLabelText("搜索学习会话"), {
      target: { value: "证据充分性" },
    });
    expect(screen.queryByText("索引激活学习")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: /证据充分性/ }));
    expect(onRestore).toHaveBeenCalledWith("chat-history");
  });

  it("routes archive through the workspace transition owner", () => {
    const onArchive = vi.fn();
    render(
      <SessionNavigator
        activeSessionId="chat-active"
        onArchive={onArchive}
        sessions={sessions}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "归档当前会话" }));
    expect(onArchive).toHaveBeenCalledWith("chat-active");
  });

  it("shares one interaction state across sidebar and drawer surfaces", () => {
    render(
      <>
        <SessionNavigator activeSessionId="chat-active" sessions={sessions} />
        <SessionNavigator
          activeSessionId="chat-active"
          sessions={sessions}
          variant="panel"
        />
      </>,
    );

    const searches = screen.getAllByLabelText("搜索学习会话") as HTMLInputElement[];
    expect(searches).toHaveLength(2);
    fireEvent.change(searches[0], { target: { value: "证据充分性" } });

    expect(searches[0].value).toBe("证据充分性");
    expect(searches[1].value).toBe("证据充分性");
    expect(screen.queryByText("索引激活学习")).toBeNull();
    expect(screen.getAllByText("证据充分性", { exact: true })).toHaveLength(2);
  });
});
