import { describe, expect, it } from "vitest";

import {
  RAG_UPLOAD_ACCEPT,
  RAG_UPLOAD_MAX_BATCH_BYTES,
  RAG_UPLOAD_MAX_FILE_BYTES,
  validateRagUploadFiles,
} from "./uploadContract";

function file(name: string, size: number): File {
  return { name, size } as File;
}

describe("RAG upload client contract", () => {
  it("advertises every server-supported extension", () => {
    expect(RAG_UPLOAD_ACCEPT).toBe(".md,.markdown,.txt,.pdf,.docx");
  });

  it("accepts a valid mixed document batch", () => {
    const files = [file("notes.md", 10), file("chapter.pdf", 100), file("report.docx", 200)];

    expect(validateRagUploadFiles(files)).toEqual({
      valid: true,
      files,
      rejections: [],
      message: "",
    });
  });

  it("rejects the entire mixed batch when one file is unsupported or empty", () => {
    const result = validateRagUploadFiles([
      file("notes.md", 10),
      file("table.csv", 10),
      file("empty.txt", 0),
    ]);

    expect(result.valid).toBe(false);
    expect(result.files).toEqual([]);
    expect(result.message).toContain("未上传任何文件");
    expect(result.message).toContain("table.csv：不支持该文件类型");
    expect(result.message).toContain("empty.txt：文件为空");
  });

  it("enforces the 10 MiB per-file and 25 MiB batch limits", () => {
    const tooLarge = validateRagUploadFiles([
      file("large.pdf", RAG_UPLOAD_MAX_FILE_BYTES + 1),
    ]);
    expect(tooLarge.message).toContain("超过单文件 10 MiB 限制");

    const batch = validateRagUploadFiles([
      file("a.pdf", RAG_UPLOAD_MAX_BATCH_BYTES / 2 + 1),
      file("b.pdf", RAG_UPLOAD_MAX_BATCH_BYTES / 2 + 1),
    ]);
    expect(batch.message).toContain("合计超过 25 MiB 限制");
  });
});
