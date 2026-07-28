import { mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";

export const GOLDEN_JOURNEY_METRICS_PATH = resolve(
  "test-results/golden-journey-metrics.json",
);
export const GOLDEN_JOURNEY_SUCCESS_DIR = resolve(
  "test-results/success-journeys",
);
export const GOLDEN_JOURNEY_SUCCESS_MANIFEST_PATH = resolve(
  GOLDEN_JOURNEY_SUCCESS_DIR,
  "manifest.json",
);

export default function globalSetup() {
  rmSync(GOLDEN_JOURNEY_METRICS_PATH, { force: true });
  rmSync(GOLDEN_JOURNEY_SUCCESS_DIR, { recursive: true, force: true });
  mkdirSync(dirname(GOLDEN_JOURNEY_METRICS_PATH), { recursive: true });
  mkdirSync(GOLDEN_JOURNEY_SUCCESS_DIR, { recursive: true });
}
