// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RoadmapPanel } from "./RoadmapPanel";

describe("RoadmapPanel", () => {
  it("renders the panel with heading and subtitle", () => {
    render(<RoadmapPanel />);

    expect(screen.getByRole("heading", { name: "核心能力边界" })).toBeInTheDocument();
    expect(screen.getByText("围绕主学习闭环持续收口")).toBeInTheDocument();
  });

  it("lists every roadmap item", () => {
    const { container } = render(<RoadmapPanel />);

    const items = container.querySelectorAll(".roadmap-list li");
    expect(items).toHaveLength(3);
    expect(items[0]).toHaveTextContent("群聊、新闻、RAG 与学习记忆已接入可恢复的服务端流程。");
    expect(items[1]).toHaveTextContent("当前优先收口核心学习闭环、恢复语义与窄屏体验。");
    expect(items[2]).toHaveTextContent("产品前端统一为 React，旧 Streamlit 运行层已移除。");
  });
});
