import { readdirSync, readFileSync, statSync } from "node:fs";
import { relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const srcRoot = fileURLToPath(new URL("../", import.meta.url));
const terms = [
  /github/i,
  /repository[_A-Z]?url/i,
  /repo[_A-Z]?url/i,
  /symbol[_A-Z]?(mapping|path|name)/i,
  /ci[_A-Z]?association/i,
  /source[_A-Z]?artifact/i,
];

function walk(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = resolve(dir, name);
    if (statSync(path).isDirectory()) return walk(path);
    if (!/\.(ts|tsx)$/.test(name) || /\.(test|spec)\.(ts|tsx)$/.test(name)) return [];
    return [path];
  });
}

describe("GitHub evidence production owner inventory", () => {
  it("prints every production reference before the owner boundary is finalized", () => {
    const matches = walk(srcRoot).flatMap((path) => {
      const lines = readFileSync(path, "utf8").split("\n");
      return lines.flatMap((line, index) =>
        terms.some((term) => term.test(line))
          ? [`${relative(srcRoot, path)}:${index + 1}: ${line.trim()}`]
          : [],
      );
    });

    expect(matches, `GITHUB_EVIDENCE_INVENTORY\n${matches.join("\n")}`).toEqual([]);
  });
});
