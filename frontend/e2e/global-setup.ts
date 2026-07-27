import { mkdirSync, rmSync } from "node:fs";
import { dirname, resolve } from "node:path";

export const GOLDEN_JOURNEY_METRICS_PATH = resolve(
  "test-results/golden-journey-metrics.json",
);

export default function globalSetup() {
  rmSync(GOLDEN_JOURNEY_METRICS_PATH, { force: true });
  mkdirSync(dirname(GOLDEN_JOURNEY_METRICS_PATH), { recursive: true });
}
