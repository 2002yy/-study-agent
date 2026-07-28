import { expect, test, type Page } from "@playwright/test";

const API_BASE = "http://127.0.0.1:8000";
const STORAGE_KEY = "study-agent-react-session";

const FIRST_QUESTION = "带我系统学习二分查找复杂度";
const FIRST_REPLY =
  "我们先建立目标：理解为什么二分查找是 O(log n)。请说明每一轮会怎样改变候选区间？";
const BARE_REPLY =
  "只说“懂了”还不足以确认掌握。请用因果关系解释候选区间怎样变化？";
const CORRECT_EXPLANATION =
  "所以二分查找每轮把候选范围减半，因此问题规模按一半递减，查找次数是对数级，因为只需重复减半直到剩一个元素。";
const CORRECT_REPLY =
  "这段解释已经通过理解验证；下一步把减半过程迁移到查找次数估算。";

type DurableState = {
  database_path: string;
  thread: {
    id: string;
    learning_state: {
      phase?: string;
      confirmed_points?: string[];
      payload?: Record<string, unknown>;
    };
  };
  turns: Array<{
    id: string;
    status: string;
    user_message: string;
    assistant_message: string;
  }>;
};

test.beforeEach(async ({ request }) => {
  const response = await request.post(`${API_BASE}/__e2e__/reset`);
  expect(response.ok()).toBe(true);
});

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

async function send(page: Page, text: string) {
  const composer = page.getByLabel("输入学习问题");
  await composer.fill(text);
  await composer.press("Enter");
}

test("first learning turn crosses React, FastAPI and SQLite then restores", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "学习工作台" })).toBeVisible();

  await send(page, FIRST_QUESTION);
  await expect(page.getByText(FIRST_REPLY, { exact: true })).toBeVisible();

  const sessionId = await activeSessionId(page);
  const stored = await durableState(page, sessionId);
  expect(stored.database_path).toContain("real-stack-runtime");
  expect(stored.thread.id).toBe(sessionId);
  expect(stored.turns).toHaveLength(1);
  expect(stored.turns[0]).toMatchObject({
    status: "completed",
    user_message: FIRST_QUESTION,
    assistant_message: FIRST_REPLY,
  });
  expect(stored.thread.learning_state.confirmed_points ?? []).toEqual([]);

  await page.reload();
  await expect(page.getByText(FIRST_REPLY, { exact: true })).toBeVisible();
  await expect(page.getByRole("region", { name: "继续当前任务" })).toBeVisible();

  const restored = await durableState(page, sessionId);
  expect(restored.turns).toEqual(stored.turns);
  expect(restored.thread.learning_state).toEqual(stored.thread.learning_state);
});

test("bare understanding is rejected before a reasoned claim commits", async ({
  page,
}) => {
  await page.goto("/");
  await send(page, FIRST_QUESTION);
  await expect(page.getByText(FIRST_REPLY, { exact: true })).toBeVisible();

  const sessionId = await activeSessionId(page);
  await send(page, "懂了");
  await expect(page.getByText(BARE_REPLY, { exact: true })).toBeVisible();

  const rejected = await durableState(page, sessionId);
  expect(rejected.turns).toHaveLength(2);
  expect(rejected.turns.at(-1)).toMatchObject({
    status: "completed",
    user_message: "懂了",
    assistant_message: BARE_REPLY,
  });
  expect(rejected.thread.learning_state.confirmed_points ?? []).toEqual([]);
  expect(rejected.thread.learning_state.payload?.state_advance_blocked).toBe(true);

  await send(page, CORRECT_EXPLANATION);
  await expect(page.getByText(CORRECT_REPLY, { exact: true })).toBeVisible();

  const accepted = await durableState(page, sessionId);
  expect(accepted.turns).toHaveLength(3);
  expect(accepted.turns.at(-1)).toMatchObject({
    status: "completed",
    user_message: CORRECT_EXPLANATION,
    assistant_message: CORRECT_REPLY,
  });
  expect(accepted.thread.learning_state.phase).toBe("transfer");
  expect(accepted.thread.learning_state.confirmed_points).toContain(
    CORRECT_EXPLANATION,
  );

  await page.reload();
  await expect(page.getByText(CORRECT_REPLY, { exact: true })).toBeVisible();
  const restoreCard = page.getByRole("region", { name: "继续当前任务" });
  await expect(restoreCard.getByText(CORRECT_EXPLANATION, { exact: true })).toBeVisible();

  const restored = await durableState(page, sessionId);
  expect(restored.thread.learning_state).toEqual(accepted.thread.learning_state);
  expect(restored.turns).toEqual(accepted.turns);
});
