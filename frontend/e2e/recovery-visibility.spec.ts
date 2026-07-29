import { expect, test } from "@playwright/test";

import {
  installApiFixture,
  makeLearningSession,
  seedWorkspaceRecovery,
} from "./api-fixture";

const FAILED_QUESTION = "请解释一次失败后如何继续学习";

function longFailedSession() {
  const session = makeLearningSession();
  const messages: Array<Record<string, unknown>> = [];
  const turns: Array<Record<string, unknown>> = [];

  for (let index = 1; index <= 12; index += 1) {
    const turnId = `turn-history-${index}`;
    const question = `第 ${index} 轮：继续解释二分查找边界不变量。`;
    const answer = `第 ${index} 轮回答：目标若存在，始终留在更新后的候选区间中。`.repeat(3);
    messages.push(
      { role: "user", content: question, turnId, turnStatus: "completed" },
      { role: "assistant", content: answer, avatarRole: "nahida", turnId, turnStatus: "completed" },
    );
    turns.push({
      turn_id: turnId,
      status: "completed",
      user_message: question,
      assistant_message: answer,
      parent_turn_id: null,
      route_snapshot: session.detail.route,
      rag_snapshot: session.detail.rag,
      pedagogy_snapshot: session.detail.pedagogy,
    });
  }

  messages.push(
    { role: "user", content: FAILED_QUESTION, turnId: "turn-failed", turnStatus: "failed" },
    { role: "assistant", content: "", avatarRole: "auto", turnId: "turn-failed", turnStatus: "failed" },
  );
  turns.push({
    turn_id: "turn-failed",
    status: "failed",
    user_message: FAILED_QUESTION,
    assistant_message: "",
    parent_turn_id: null,
    route_snapshot: session.detail.route,
    rag_snapshot: session.detail.rag,
    pedagogy_snapshot: {
      learning_state_before: session.detail.learning_state,
    },
  });

  session.detail.messages = messages;
  session.detail.turns = turns;
  session.row.title = "长会话失败恢复";
  return session;
}

test("failed recovery remains visible inside the conversation viewport", async ({ page }) => {
  const session = longFailedSession();
  const fixture = await installApiFixture(page, { session });
  await seedWorkspaceRecovery(page, session.row.session_id);
  await page.goto("/");

  const conversation = page.getByRole("region", { name: "学习对话" });
  const recovery = page.getByRole("region", { name: "中断任务恢复" });
  await expect(recovery).toBeVisible();
  await expect(recovery.getByRole("button", { name: "从断点继续" })).toHaveCount(0);
  await expect(recovery.getByRole("button", { name: "重新生成" })).toBeVisible();
  await expect(page.locator(".interrupted-copy-shortcut")).toBeHidden();

  const conversationBox = await conversation.boundingBox();
  const recoveryBox = await recovery.boundingBox();
  expect(conversationBox).not.toBeNull();
  expect(recoveryBox).not.toBeNull();
  expect(recoveryBox!.y).toBeGreaterThanOrEqual(conversationBox!.y - 1);
  expect(recoveryBox!.y + recoveryBox!.height).toBeLessThanOrEqual(
    conversationBox!.y + conversationBox!.height + 1,
  );

  expect(fixture.unexpectedApiPaths).toEqual([]);
});
