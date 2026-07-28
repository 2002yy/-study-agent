// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ApiSnapshot, ChatSettings, RagSettings } from "../../types";
import { SettingsPanel } from "./SettingsPanel";

vi.mock("../../api", () => ({
  saveRuntimeSettings: vi.fn().mockResolvedValue({}),
}));

const snapshot = {
  health: { status: "ok" },
  error: "",
  runtimeSettings: {
    settings: {
      web_policy: "ask",
      cloud_context_policy: "question_only",
    },
  },
} as unknown as ApiSnapshot;

const chatSettings: ChatSettings = {
  selectedRole: "auto",
  selectedMode: "auto",
  selectedModel: "auto",
  relationshipMode: "standard",
  contextMode: "",
};

const ragSettings: RagSettings = {
  retrievalMode: "hybrid",
  topK: 5,
  chatTopK: 3,
  minScore: 0.01,
};

function renderPanel() {
  return render(
    <SettingsPanel
      snapshot={snapshot}
      ragEnabled
      ragUploadMode="upload"
      setRagUploadMode={vi.fn()}
      setRagEnabled={vi.fn()}
      chatSettings={chatSettings}
      setChatSettings={vi.fn()}
      ragSettings={ragSettings}
      setRagSettings={vi.fn()}
      onSaveSettings={vi.fn()}
      isSavingSettings={false}
      onLoadRole={vi.fn()}
      roleDetail={null}
      keepCurrentRole={false}
      setKeepCurrentRole={vi.fn()}
      conversationInstruction=""
      setConversationInstruction={vi.fn()}
      onNewSession={vi.fn()}
      isSending={false}
      refresh={vi.fn()}
      onUploadClick={vi.fn()}
      uploadState="idle"
      lastChat={null}
    />,
  );
}

describe("SettingsPanel progressive disclosure", () => {
  it("keeps ordinary settings focused on learning, material, privacy and tone", () => {
    renderPanel();

    expect(screen.getByRole("combobox", { name: "学习方式" })).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "互动氛围" })).toBeTruthy();
    expect(screen.getByRole("checkbox", { name: "回答时使用我的资料" })).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "联网策略" })).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "模型上下文" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "设为全局默认" })).toBeTruthy();

    expect(screen.queryByRole("combobox", { name: "角色" })).toBeNull();
    expect(screen.queryByRole("combobox", { name: "模型档位" })).toBeNull();
    expect(screen.queryByRole("combobox", { name: "上下文深度" })).toBeNull();
    expect(screen.queryByRole("combobox", { name: "检索方式" })).toBeNull();
    expect(screen.queryByLabelText("本会话微调")).toBeNull();
  });

  it("keeps all existing engineering controls reachable after opening advanced settings", () => {
    renderPanel();
    fireEvent.click(screen.getByText("高级设置"));

    expect(screen.getByRole("combobox", { name: "角色" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "强制保持当前角色" })).toBeTruthy();
    expect(screen.getByLabelText("本会话微调")).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "模型档位" })).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "上下文深度" })).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "检索方式" })).toBeTruthy();
    expect(screen.getByRole("spinbutton", { name: "候选来源" })).toBeTruthy();
    expect(screen.getByRole("spinbutton", { name: "回答引用" })).toBeTruthy();
    expect(screen.getByRole("spinbutton", { name: "最低相关度" })).toBeTruthy();
  });
});
