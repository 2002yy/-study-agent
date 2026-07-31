import { expect, test, type Page } from "@playwright/test";

const API = "http://127.0.0.1:8000";
const STORE = "study-agent-react-session";
const QUERY = "Python object construction boundaries";

test.beforeEach(async ({ request }) => {
  expect((await request.post(`${API}/__e2e__/reset`)).ok()).toBe(true);
});

async function open(page: Page, item: string, title: string) {
  await page.locator("summary[aria-label='打开更多学习工具']").click();
  await page.getByRole("menuitem").filter({ hasText: item }).click();
  return page.getByRole("dialog", { name: title });
}

async function storedRunId(page: Page) {
  await page.waitForFunction((key) => {
    const raw = localStorage.getItem(key);
    if (!raw) return false;
    return Boolean(JSON.parse(raw).workspace?.webLookupRunId);
  }, STORE);
  return page.evaluate((key) => JSON.parse(localStorage.getItem(key) ?? "{}").workspace.webLookupRunId, STORE) as Promise<string>;
}

async function run(page: Page, id: string) {
  const response = await page.request.get(`${API}/research-runs/${id}`);
  expect(response.ok()).toBe(true);
  return response.json();
}

test("research stop survives refresh and retries the same run", async ({ page }) => {
  await page.goto("/");
  const news = await open(page, "新闻研究", "新闻");
  await news.getByLabel("联网检索").fill(QUERY);
  await news.getByRole("button", { name: "研究并用于下一轮聊天" }).click();
  const stop = news.getByRole("button", { name: "停止研究" });
  await expect(stop).toBeVisible();
  const id = await storedRunId(page);
  await stop.click();

  await expect.poll(async () => (await run(page, id)).status).toBe("cancelled");
  const cancelled = await run(page, id);
  expect(cancelled).toMatchObject({
    id,
    query: QUERY,
    stage: "cancelled",
    stop_reason: "user_cancelled",
  });
  expect(cancelled.cancel_requested_at).toBeTruthy();
  expect(cancelled.completed_at).toBeTruthy();

  await page.reload();
  const group = await open(page, "群聊讨论", "群聊");
  await expect(group.getByText("研究已停止", { exact: true })).toBeVisible();
  await expect(group.getByLabel("仅用于下一轮单人聊天")).toBeDisabled();
  expect(await storedRunId(page)).toBe(id);

  await group.getByLabel("联网检索").fill(QUERY);
  await group.getByRole("button", { name: "研究并用于下一轮聊天" }).click();
  await expect.poll(async () => (await run(page, id)).status).toBe("completed");
  const completed = await run(page, id);
  expect(completed.id).toBe(id);
  expect(completed.query_attempts.length).toBeGreaterThanOrEqual(2);
  expect(completed.source_block).not.toBe("");
  await expect(group.getByText("研究完成", { exact: true })).toBeVisible();
  await expect(group.getByLabel("仅用于下一轮单人聊天")).toBeChecked();
});
