import { Cloud, Database, History, Search } from "lucide-react";

import type { ExternalDataPolicySnapshot, TurnEvidence } from "../../types";

type DisclosureSummary = {
  policy: ExternalDataPolicySnapshot;
  queries: string[];
  providers: string[];
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

function asPolicy(value: unknown): ExternalDataPolicySnapshot | null {
  const policy = asRecord(value);
  if (!Object.keys(policy).length) return null;
  return {
    web_policy: String(policy.web_policy ?? ""),
    cloud_context_policy: String(policy.cloud_context_policy ?? ""),
    task_source_policy: String(policy.task_source_policy ?? ""),
    web_allowed: policy.web_allowed === true,
    local_retrieval_allowed: policy.local_retrieval_allowed === true,
    history_allowed: policy.history_allowed === true,
    memory_allowed: policy.memory_allowed === true,
    local_evidence_to_model_allowed:
      policy.local_evidence_to_model_allowed === true,
    reason: String(policy.reason ?? ""),
    web_search_performed:
      typeof policy.web_search_performed === "boolean"
        ? policy.web_search_performed
        : undefined,
    history_sent_to_model:
      typeof policy.history_sent_to_model === "boolean"
        ? policy.history_sent_to_model
        : undefined,
    history_message_count: Number(policy.history_message_count ?? 0),
    learning_state_sent_to_model:
      typeof policy.learning_state_sent_to_model === "boolean"
        ? policy.learning_state_sent_to_model
        : undefined,
    memory_context_sent_to_model:
      typeof policy.memory_context_sent_to_model === "boolean"
        ? policy.memory_context_sent_to_model
        : undefined,
    local_evidence_sent_to_model:
      typeof policy.local_evidence_sent_to_model === "boolean"
        ? policy.local_evidence_sent_to_model
        : undefined,
    local_evidence_chunk_count: Number(policy.local_evidence_chunk_count ?? 0),
  };
}

function providerName(value: string): string {
  const normalized = value.split(":", 1)[0].trim();
  const labels: Record<string, string> = {
    searxng: "SearXNG",
    bing_rss: "Bing RSS",
    duckduckgo_html: "DuckDuckGo",
  };
  return labels[normalized] ?? normalized;
}

export function summarizeExternalData(evidence: TurnEvidence): DisclosureSummary | null {
  const rag = evidence.rag;
  const policy = asPolicy(
    rag?.external_data_policy ?? asRecord(evidence.route).external_data_policy,
  );
  if (!policy) return null;
  const queries = new Set<string>();
  const providers = new Set<string>();
  for (const call of rag?.web_tools?.calls ?? []) {
    const record = asRecord(call);
    if (record.name !== "web_search") continue;
    const args = asRecord(record.arguments);
    const result = asRecord(record.result);
    const query = String(args.query ?? result.query ?? "").trim();
    if (query) queries.add(query);
    const attempted = Array.isArray(result.providers_attempted)
      ? result.providers_attempted
      : [];
    for (const provider of attempted) {
      const label = providerName(String(provider));
      if (label) providers.add(label);
    }
  }
  for (const error of rag?.web_tools?.provider_errors ?? []) {
    const label = providerName(error);
    if (label) providers.add(label);
  }
  return { policy, queries: [...queries], providers: [...providers] };
}

export function ExternalDataDisclosure({ evidence }: { evidence: TurnEvidence }) {
  const summary = summarizeExternalData(evidence);
  if (!summary) return null;
  const { policy } = summary;
  return (
    <section className="external-data-disclosure" aria-label="本轮外发数据说明">
      <div className="external-data-disclosure-heading">
        <Cloud aria-hidden="true" size={14} />
        <strong>本轮外发数据说明</strong>
      </div>
      <ul>
        <li>
          <Search aria-hidden="true" size={13} />
          <span>
            联网搜索：
            {policy.web_search_performed === true
              ? "已发出搜索请求"
              : policy.web_search_performed === false
                ? "未发出搜索请求"
                : policy.web_allowed
                  ? "策略允许，缺少本轮执行记录"
                  : "未允许"}
            {summary.queries.length ? `；搜索词：${summary.queries.join("；")}` : "；本轮未记录搜索词"}
          </span>
        </li>
        <li>
          <History aria-hidden="true" size={13} />
          <span>
            最近对话：
            {policy.history_sent_to_model === true
              ? `已向模型发送 ${policy.history_message_count ?? 0} 条消息`
              : policy.history_sent_to_model === false
                ? "未发送给模型"
                : policy.history_allowed
                  ? "策略允许，缺少本轮执行记录"
                  : "未发送给模型"}
          </span>
        </li>
        <li>
          <Database aria-hidden="true" size={13} />
          <span>
            本地资料：
            {policy.local_evidence_sent_to_model === true
              ? `已向模型发送 ${policy.local_evidence_chunk_count ?? 0} 个相关片段，不展示正文`
              : policy.local_evidence_sent_to_model === false
                ? "未发送给模型"
                : policy.local_evidence_to_model_allowed
                  ? "策略允许，缺少本轮执行记录"
                  : "未发送给模型"}
            ；学习状态：
            {policy.learning_state_sent_to_model === true
              ? "已发送给模型"
              : policy.learning_state_sent_to_model === false
                ? "未发送给模型"
                : "缺少本轮执行记录"}
            ；长期记忆上下文：
            {policy.memory_context_sent_to_model === true ? "已发送给模型" : "未发送给模型"}
          </span>
        </li>
      </ul>
      <small>
        搜索源：{summary.providers.length ? summary.providers.join("、") : "本轮无可展示的 provider 记录"}
      </small>
    </section>
  );
}
