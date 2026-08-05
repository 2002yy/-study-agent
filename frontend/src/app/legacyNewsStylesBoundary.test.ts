import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const appDir = dirname(fileURLToPath(import.meta.url));
const sourceRoot = join(appDir, "..");
const stylesPath = join(sourceRoot, "styles.css");
const legacyNewsClasses = ["news-form", "news-result", "news-list", "news-item"] as const;

type SourceFile = { path: string; source: string };

function productionTypeScriptSources(directory: string): SourceFile[] {
  const sources: SourceFile[] = [];
  for (const entry of readdirSync(directory)) {
    const path = join(directory, entry);
    const stats = statSync(path);
    if (stats.isDirectory()) {
      sources.push(...productionTypeScriptSources(path));
      continue;
    }
    if (!/\.tsx?$/.test(entry) || /\.test\.tsx?$/.test(entry)) continue;
    sources.push({ path: relative(sourceRoot, path), source: readFileSync(path, "utf8") });
  }
  return sources;
}

function staticClassNameTokens(source: string): Set<string> {
  const tokens = new Set<string>();
  for (const match of source.matchAll(/className\s*=\s*["'`]([^"'`]*)["'`]/g)) {
    for (const token of match[1].split(/\s+/).filter(Boolean)) tokens.add(token);
  }
  return tokens;
}

describe("retired NewsWorkspace style boundary", () => {
  it("does not keep NewsWorkspace selectors after the product surface is removed", () => {
    expect(existsSync(stylesPath)).toBe(true);
    const styles = readFileSync(stylesPath, "utf8");
    for (const className of legacyNewsClasses) {
      expect(styles).not.toContain(`.${className}`);
    }
  });

  it("does not reintroduce retired NewsWorkspace class names in production DOM source", () => {
    const offenders = productionTypeScriptSources(sourceRoot).flatMap(({ path, source }) => {
      const classNames = staticClassNameTokens(source);
      return legacyNewsClasses
        .filter((className) => classNames.has(className))
        .map((className) => `${path}:${className}`);
    });
    expect(offenders).toEqual([]);
  });
});
