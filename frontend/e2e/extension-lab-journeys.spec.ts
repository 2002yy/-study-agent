import { expect, test } from "@playwright/test";

import { installApiFixture } from "./api-fixture";

const EXTENSION_PATHS = new Set(["/wechat", "/tools", "/workflows/runs"]);

test("laboratory stays dormant until selection and restores focus on return", async ({
  page,
}) => {
  const requestedExtensions: string[] = [];
  page.on("request", (request) => {
    const path = new URL(request.url()).pathname;
    if (EXTENSION_PATHS.has(path)) requestedExtensions.push(path);
  });
  const fixture = await installApiFixture(page);
  await page.goto("/");

  await page.getByLabel("打开更多学习工具").click();
  const labEntry = page.getByRole("menuitem", { name: /实验室/ });
  await expect(labEntry).toBeVisible();
  await expect(page.getByRole("menuitem", { name: /群聊讨论/ })).toHaveCount(0);
  await expect(page.getByRole("menuitem", { name: /受控工具/ })).toHaveCount(0);
  await expect(page.getByRole("menuitem", { name: /开发者诊断/ })).toHaveCount(0);
  await labEntry.click();

  const lab = page.getByRole("dialog", { name: "实验室" });
  await expect(lab).toBeVisible();
  await expect(lab.getByRole("button", { name: /群聊讨论/ })).toBeVisible();
  await expect(lab.getByRole("button", { name: /受控工具/ })).toBeVisible();
  await expect(lab.getByRole("button", { name: /开发者诊断/ })).toBeVisible();
  expect(requestedExtensions).toEqual([]);

  const groupChoice = lab.getByRole("button", { name: /群聊讨论/ });
  await groupChoice.click();
  await expect(page.getByRole("dialog", { name: "群聊" })).toBeVisible();
  await expect.poll(() => requestedExtensions).toEqual(["/wechat"]);

  await page.getByRole("button", { name: "返回实验室" }).click();
  const restoredLab = page.getByRole("dialog", { name: "实验室" });
  await expect(restoredLab).toBeVisible();
  await expect(
    restoredLab.getByRole("button", { name: /群聊讨论/ }),
  ).toBeFocused();

  expect(fixture.unexpectedApiPaths).toEqual([]);
});
