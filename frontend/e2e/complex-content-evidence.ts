import { readFileSync, writeFileSync } from "node:fs";

import type { Page, TestInfo } from "@playwright/test";

import { GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH } from "./global-setup";
import { captureSuccessStep, type SuccessArtifact } from "./journey-metrics";

type ComplexSuccessArtifact = SuccessArtifact & {
  conversation_scroll_top: number;
  conversation_scroll_height: number;
  conversation_client_height: number;
  conversation_distance_from_bottom: number;
};

export async function captureComplexSuccessStep(
  page: Page,
  testInfo: TestInfo,
  journey: string,
  step: string,
): Promise<string> {
  const file = await captureSuccessStep(page, testInfo, journey, step);
  const position = await page.locator(".conversation").evaluate((element) => ({
    scrollTop: Math.round(element.scrollTop),
    scrollHeight: element.scrollHeight,
    clientHeight: element.clientHeight,
    distanceFromBottom: Math.round(
      element.scrollHeight - element.scrollTop - element.clientHeight,
    ),
  }));
  const manifest = JSON.parse(
    readFileSync(GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH, "utf8"),
  ) as Array<SuccessArtifact | ComplexSuccessArtifact>;
  const updated = manifest.map((item) =>
    item.file === file
      ? {
          ...item,
          conversation_scroll_top: position.scrollTop,
          conversation_scroll_height: position.scrollHeight,
          conversation_client_height: position.clientHeight,
          conversation_distance_from_bottom: position.distanceFromBottom,
        }
      : item,
  );
  writeFileSync(
    GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH,
    `${JSON.stringify(updated, null, 2)}\n`,
  );
  return file;
}
