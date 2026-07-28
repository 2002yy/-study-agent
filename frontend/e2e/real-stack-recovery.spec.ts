import { expect, test, type Page } from "@playwright/test";

const API_BASE = "http://127.0.0.1:8000";
const STORAGE_KEY = "study-agent-react-session";
const INTERRUPT_QUESTION = "请生成一段可中断的二分查找边界讲解";
const INTERRUPT_REPLY =
  "第一部分：二分查找每轮先比较中点与目标值。第二部分：目标值更大时左边界移动到 mid + 1，因为 mid 已被排除。第三部分：持续缩小区间直到找到目标或区间为空。";
const FAIL_ONCE_QUESTION = "请触发一次可重试的确定性失败";
const RETRY_REPLY = "重试成功：这次回答只提交一次，并保留失败父回合作为可审计记录。";

type DurableTurn = {
  id: string;
  status: string;
  user_message: string;
  assistant_message: string;
  parent_turn_id?: string | null;
  route_snapshot: Record<string, unknown>;
  pedagogy_snapshot: Record<string, unknown>;
};

type DurableState = {
  thread: {
    id: string;
    learning_state: Record<string, unknown>;
  };
  turns: DurableTurn[];
};

test.beforeEach(async ({ request }) => {
  const response = await request.post(`${API_BASE}/__e2e__/reset`);
  expect(response.ok()).toBe(true);
});

async function send(page: Page, text: string) {
  const composer = page.getByLabel("输入学习问题");
  await composer.fill(text);
  await composer.press("Enter");
}

async function activeSessionId(page: Page): Promise<string> {
  await page.waitForFunction(
    ({ key }) => {
      const raw = window.localStorage.getItem(key);
      if (!raw) return false;
      try {
        const parsed = JSON.parse(raw) as {
          workspace?: { singleChatSessionId?: string; lastSessionId?: string };
        };
        return Boolean(
          parsed.workspace?.singleChatSessionId ?? parsed.workspace?.lastSessionId,
        );
      } catch {
        return false;
      }
    },
    { key: STORAGE_KEY },
  );
  return page.evaluate(({ key }) => {
    const parsed = JSON.parse(window.localStorage.getItem(key) ?? "{}") as {
      workspace?: { singleChatSessionId?: string; lastSessionId?: string };
    };
    const sessionId =
      parsed.workspace?.singleChatSessionId ?? parsed.workspace?.lastSessionId;
    if (!sessionId) throw new Error("Active session was not persisted");
    return sessionId;
  }, { key: STORAGE_KEY });
}

async function durableState(page: Page, sessionId: string): Promise<DurableState> {
  const response = await page.request.get(
    `${API_BASE}/__e2e__/state/${encodeURIComponent(sessionId)}`,
  );
  expect(response.ok()).toBe(true);
  return (await response.json()) as DurableState;
}

function assistantMessage(page: Page, text: string) {
  return page
    .getByRole("region", { name: "学习对话" })
    .locator("article.message.assistant")
    .filter({ hasText: text })
    .last()
    .getByText(text, { exact: true });
}

test("stopped stream restores partial truth and completes the same turn once", async ({
  page,
}) => {
  await page.goto("/");
  await send(page, INTERRUPT_QUESTION);

  await expect(page.getByText(/第一部分：二分查找/)).toBeVisible();
  await page.getByRole("button", { name: "停止" }).click();

  const recovery = page.getByRole("region", { name: "中断任务恢复" });
  await expect(recovery).toBeVisible();
  await expect(recovery.getByRole("button", { name: "从断点继续" })).toBeVisible();
  const sessionId = await activeSessionId(page);

  await expect
    .poll(async () => (await durableState(page, sessionId)).turns.at(-1)?.status)
    .toBe("interrupted");
  const interrupted = await durableState(page, sessionId);
  expect(interrupted.turns).toHaveLength(1);
  const interruptedTurn = interrupted.turns[0];
  expect(interruptedTurn.user_message).toBe(INTERRUPT_QUESTION);
  expect(interruptedTurn.assistant_message.length).toBeGreaterThan(0);
  expect(INTERRUPT_REPLY.startsWith(interruptedTurn.assistant_message)).toBe(true);
  expect(interrupted.thread.learning_state).toEqual(
    interruptedTurn.pedagogy_snapshot.learning_state_before,
  );

  await page.reload();
  const restoredRecovery = page.getByRole("region", { name: "中断任务恢复" });
  await expect(restoredRecovery).toBeVisible();
  await expect(
    restoredRecovery.getByText(interruptedTurn.assistant_message, { exact: true }),
  ).toBeVisible();

  await restoredRecovery.getByRole("button", { name: "从断点继续" }).click();
  await expect(assistantMessage(page, INTERRUPT_REPLY)).toBeVisible();

  await expect
    .poll(async () => (await durableState(page, sessionId)).turns.at(-1)?.status)
    .toBe("completed");
  const completed = await durableState(page, sessionId);
  expect(completed.turns).toHaveLength(1);
  expect(completed.turns[0]).toMatchObject({
    id: interruptedTurn.id,
    status: "completed",
    user_message: INTERRUPT_QUESTION,
    assistant_message: INTERRUPT_REPLY,
  });
  expect(completed.turns[0].route_snapshot).toMatchObject({
    is_continuation: true,
    is_continuation_resolved: true,
  });
  expect(completed.thread.learning_state).toEqual(
    completed.turns[0].pedagogy_snapshot.committed_learning_state,
  );

  await page.reload();
  await expect(assistantMessage(page, INTERRUPT_REPLY)).toBeVisible();
  await expect(page.getByRole("region", { name: "中断任务恢复" })).toHaveCount(0);
});

test("zero-token failure retries as one child commit and supersedes its parent", async ({
  page,
}) => {
  await page.goto("/");
  await send(page, FAIL_ONCE_QUESTION);

  const recovery = page.getByRole("region", { name: "中断任务恢复" });
  await expect(recovery).toBeVisible();
  await expect(recovery.getByRole("button", { name: "从断点继续" })).toHaveCount(0);
  await expect(recovery.getByRole("button", { name: "重新生成" })).toBeVisible();
  const sessionId = await activeSessionId(page);

  await expect
    .poll(async () => (await durableState(page, sessionId)).turns.at(-1)?.status)
    .toBe("failed");
  const failed = await durableState(page, sessionId);
  expect(failed.turns).toHaveLength(1);
  const failedTurn = failed.turns[0];
  expect(failedTurn).toMatchObject({
    status: "failed",
    user_message: FAIL_ONCE_QUESTION,
    assistant_message: "",
  });
  expect(failed.thread.learning_state).toEqual(
    failedTurn.pedagogy_snapshot.learning_state_before,
  );

  await recovery.getByRole("button", { name: "重新生成" }).click();
  await expect(assistantMessage(page, RETRY_REPLY)).toBeVisible();

  await expect
    .poll(async () => (await durableState(page, sessionId)).turns.length)
    .toBe(2);
  const retried = await durableState(page, sessionId);
  const parent = retried.turns.find((turn) => turn.id === failedTurn.id);
  const child = retried.turns.find((turn) => turn.parent_turn_id === failedTurn.id);
  expect(parent).toMatchObject({ status: "superseded" });
  expect(child).toMatchObject({
    status: "completed",
    user_message: FAIL_ONCE_QUESTION,
    assistant_message: RETRY_REPLY,
    parent_turn_id: failedTurn.id,
  });
  expect(retried.turns.filter((turn) => turn.status === "completed")).toHaveLength(1);
  expect(retried.thread.learning_state).toEqual(
    child?.pedagogy_snapshot.committed_learning_state,
  );

  await page.reload();
  await expect(assistantMessage(page, RETRY_REPLY)).toBeVisible();
  await expect(page.getByRole("region", { name: "中断任务恢复" })).toHaveCount(0);
});
