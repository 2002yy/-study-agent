import type { NewsLookupResponse } from "../../types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";
const API_TOKEN = import.meta.env.VITE_STUDY_AGENT_API_TOKEN ?? "";

export type ResearchRunStatus =
  | "pending"
  | "running"
  | "completed"
  | "partial"
  | "failed"
  | "cancelled";

export type ResearchRunStage =
  | "planned"
  | "searching"
  | "assessing"
  | "reading"
  | "synthesizing"
  | "completed"
  | "failed"
  | "cancelled";

export type ResearchLookupResponse = NewsLookupResponse & {
  status: ResearchRunStatus;
  stage: ResearchRunStage;
  research_context: Record<string, unknown>;
  query_attempts: Array<Record<string, unknown>>;
  selected_sources: Array<Record<string, unknown>>;
  rejected_sources: Array<Record<string, unknown>>;
  provider_status: string;
  stop_reason: string;
  answer_confidence: string;
  error: string;
  max_items: number;
  active_operation_id?: string | null;
  active_operation_started_at?: string | null;
  stage_started_at?: string | null;
  cancel_requested_at?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
};

type ResearchRunPayload = {
  id: string;
  query: string;
  stage: ResearchRunStage;
  status: ResearchRunStatus;
  research_context: Record<string, unknown>;
  query_attempts: Array<Record<string, unknown>>;
  selected_sources: Array<Record<string, unknown>>;
  rejected_sources: Array<Record<string, unknown>>;
  provider_status: string;
  stop_reason: string;
  answer_confidence: string;
  items: Array<Record<string, unknown>>;
  source_block: string;
  warnings: string[];
  error: string;
  max_items: number;
  active_operation_id?: string | null;
  active_operation_started_at?: string | null;
  stage_started_at?: string | null;
  cancel_requested_at?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  completed_at?: string | null;
};

type ResearchRequestOptions = {
  signal?: AbortSignal;
};

type ResearchCancelOptions = ResearchRequestOptions & {
  pollIntervalMs?: number;
  timeoutMs?: number;
};

function authHeaders(): HeadersInit {
  return API_TOKEN ? { "X-Study-Agent-Token": API_TOKEN } : {};
}

async function requestJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...authHeaders(),
      ...(options?.headers ?? {}),
    },
    ...options,
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}${body ? `: ${body}` : ""}`);
  }
  return (await response.json()) as T;
}

function toResponse(run: ResearchRunPayload): ResearchLookupResponse {
  return {
    run_id: run.id,
    query_text: run.query,
    news_items: run.items,
    source_block: run.source_block,
    warnings: run.warnings,
    status: run.status,
    stage: run.stage,
    research_context: run.research_context,
    query_attempts: run.query_attempts,
    selected_sources: run.selected_sources,
    rejected_sources: run.rejected_sources,
    provider_status: run.provider_status,
    stop_reason: run.stop_reason,
    answer_confidence: run.answer_confidence,
    error: run.error,
    max_items: run.max_items,
    active_operation_id: run.active_operation_id,
    active_operation_started_at: run.active_operation_started_at,
    stage_started_at: run.stage_started_at,
    cancel_requested_at: run.cancel_requested_at,
    version: run.version,
    created_at: run.created_at,
    updated_at: run.updated_at,
    completed_at: run.completed_at,
  };
}

function abortError(): DOMException {
  return new DOMException("The operation was aborted", "AbortError");
}

function wait(milliseconds: number, signal?: AbortSignal): Promise<void> {
  if (signal?.aborted) return Promise.reject(abortError());
  return new Promise((resolve, reject) => {
    const timer = window.setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, Math.max(0, milliseconds));
    const onAbort = () => {
      window.clearTimeout(timer);
      signal?.removeEventListener("abort", onAbort);
      reject(abortError());
    };
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

export async function createResearchRun(
  query: string,
  maxItems = 8,
  requestOptions: ResearchRequestOptions = {},
): Promise<ResearchLookupResponse> {
  const run = await requestJson<ResearchRunPayload>("/research-runs", {
    method: "POST",
    signal: requestOptions.signal,
    body: JSON.stringify({ query, max_items: maxItems }),
  });
  return toResponse(run);
}

export async function executeResearchRun(
  runId: string,
  requestOptions: ResearchRequestOptions = {},
): Promise<ResearchLookupResponse> {
  const run = await requestJson<ResearchRunPayload>(
    `/research-runs/${encodeURIComponent(runId)}/search`,
    { method: "POST", signal: requestOptions.signal },
  );
  return toResponse(run);
}

export async function retryResearchRun(
  runId: string,
  requestOptions: ResearchRequestOptions = {},
): Promise<ResearchLookupResponse> {
  const run = await requestJson<ResearchRunPayload>(
    `/research-runs/${encodeURIComponent(runId)}/retry`,
    { method: "POST", signal: requestOptions.signal },
  );
  return toResponse(run);
}

export async function resumeResearchRun(
  runId: string,
  requestOptions: ResearchRequestOptions = {},
): Promise<ResearchLookupResponse> {
  const run = await requestJson<ResearchRunPayload>(
    `/research-runs/${encodeURIComponent(runId)}/resume`,
    { method: "POST", signal: requestOptions.signal },
  );
  return toResponse(run);
}

export async function loadResearchRun(
  runId: string,
  requestOptions: ResearchRequestOptions = {},
): Promise<ResearchLookupResponse> {
  const run = await requestJson<ResearchRunPayload>(
    `/research-runs/${encodeURIComponent(runId)}`,
    { signal: requestOptions.signal },
  );
  return toResponse(run);
}

export async function cancelResearchRun(
  runId: string,
  requestOptions: ResearchCancelOptions = {},
): Promise<ResearchLookupResponse> {
  let current = toResponse(
    await requestJson<ResearchRunPayload>(
      `/research-runs/${encodeURIComponent(runId)}/cancel`,
      { method: "POST", signal: requestOptions.signal },
    ),
  );
  if (current.status !== "running") return current;

  const pollIntervalMs = Math.max(0, requestOptions.pollIntervalMs ?? 100);
  const timeoutMs = Math.max(0, requestOptions.timeoutMs ?? 5000);
  const deadline = Date.now() + timeoutMs;

  while (current.status === "running") {
    if (Date.now() >= deadline) {
      throw new Error(
        `联网研究停止请求仍在处理中（${current.stage}）；刷新后可继续查看或重试。`,
      );
    }
    await wait(pollIntervalMs, requestOptions.signal);
    current = await loadResearchRun(runId, { signal: requestOptions.signal });
  }
  return current;
}

/**
 * G18 decision 12: inject mid-run steering into an active deep-research run.
 * Returns the refreshed run; the caller keeps polling separately.
 */
export async function steerResearchRun(
  runId: string,
  content: string,
  requestOptions: { signal?: AbortSignal } = {},
): Promise<ResearchLookupResponse> {
  const payload = await requestJson<ResearchRunPayload>(
    `/research-runs/${encodeURIComponent(runId)}/steer`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
      signal: requestOptions.signal,
    },
  );
  return toResponse(payload);
}
