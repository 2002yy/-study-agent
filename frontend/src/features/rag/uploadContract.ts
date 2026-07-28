export const RAG_UPLOAD_EXTENSIONS = [".md", ".markdown", ".txt", ".pdf", ".docx"] as const;
export const RAG_UPLOAD_ACCEPT = RAG_UPLOAD_EXTENSIONS.join(",");
export const RAG_UPLOAD_MAX_FILE_BYTES = 10 * 1024 * 1024;
export const RAG_UPLOAD_MAX_BATCH_BYTES = 25 * 1024 * 1024;
export const RAG_UPLOAD_HELP_TEXT =
  "支持 Markdown、TXT、PDF、DOCX；单文件不超过 10 MiB，本次合计不超过 25 MiB。";

type UploadRejectionReason = "unsupported_type" | "empty" | "file_too_large" | "batch_too_large";

export type UploadRejection = {
  fileName: string;
  reason: UploadRejectionReason;
  message: string;
};

export type UploadValidationResult = {
  valid: boolean;
  files: File[];
  rejections: UploadRejection[];
  message: string;
};

function extensionOf(fileName: string): string {
  const dot = fileName.lastIndexOf(".");
  return dot >= 0 ? fileName.slice(dot).toLowerCase() : "";
}

export function validateRagUploadFiles(files: File[]): UploadValidationResult {
  const rejections: UploadRejection[] = [];
  for (const file of files) {
    const extension = extensionOf(file.name);
    if (!RAG_UPLOAD_EXTENSIONS.includes(extension as (typeof RAG_UPLOAD_EXTENSIONS)[number])) {
      rejections.push({
        fileName: file.name || "未命名文件",
        reason: "unsupported_type",
        message: `${file.name || "未命名文件"}：不支持该文件类型`,
      });
      continue;
    }
    if (file.size <= 0) {
      rejections.push({
        fileName: file.name,
        reason: "empty",
        message: `${file.name}：文件为空`,
      });
      continue;
    }
    if (file.size > RAG_UPLOAD_MAX_FILE_BYTES) {
      rejections.push({
        fileName: file.name,
        reason: "file_too_large",
        message: `${file.name}：超过单文件 10 MiB 限制`,
      });
    }
  }

  const totalBytes = files.reduce((sum, file) => sum + file.size, 0);
  if (totalBytes > RAG_UPLOAD_MAX_BATCH_BYTES) {
    rejections.push({
      fileName: "本次选择",
      reason: "batch_too_large",
      message: "本次选择的文件合计超过 25 MiB 限制",
    });
  }

  if (rejections.length) {
    return {
      valid: false,
      files: [],
      rejections,
      message: `未上传任何文件：${rejections.map((item) => item.message).join("；")}`,
    };
  }

  return {
    valid: files.length > 0,
    files,
    rejections: [],
    message: files.length ? "" : "请选择至少一个学习资料文件。",
  };
}
