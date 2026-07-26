import { CheckCircle2, ChevronDown, ChevronRight, Clipboard, FileText, Search, XCircle } from "lucide-react";
import { useState } from "react";
import { moveLabel, protocolLabel } from "../pedagogy/pedagogyLabels";
import { buildCitations, evidenceSummary, normalizeEvidence, summarizeWebCalls } from "./evidenceHelpers";
import type { TurnEvidence } from "../../types";
import type { EvidenceRef } from "./evidenceHelpers";

const STATUS_LABELS: Record<EvidenceRef["status"], string> = {
  selected: "已采用",
  read: "已阅读",
  candidate: "候选",
  rejected: "已排除",
};

const STATUS_ORDER: EvidenceRef["status"][] = ["selected", "read", "candidate", "rejected"];

function formatEvidencePlainText(
  pedagogy: TurnEvidence["pedagogy"],
  refs: EvidenceRef[],
): string {
  const lines: string[] = ["证据轨迹"];
  if (pedagogy) {
    lines.push(`${protocolLabel(pedagogy.mode)} · ${moveLabel(pedagogy.move)}`);
  }
  lines.push("");
  for (const ref of refs) {
    const tag = `[${STATUS_LABELS[ref.status]}]`;
    const typeTag = ref.type === "local" ? "本地" : ref.type === "web_search" ? "搜索" : ref.type === "web_read" ? "阅读" : "研究";
    const score = ref.score > 0 ? ` score=${ref.score.toFixed(2)}` : "";
    const link = ref.url || ref.source || ref.title;
    lines.push(`${tag} ${ref.title || link} (${typeTag})${ref.url ? ` ${ref.url}` : ""}${score}`);
  }
  return lines.join("\n");
}

export function EvidenceTrail({ evidence }: { evidence: TurnEvidence }) {
  const [open, setOpen] = useState(false);
  const pedagogy = evidence.pedagogy;
  const rag = evidence.rag;
  const web = rag
    ? summarizeWebCalls((rag.web_tools?.calls as never) ?? [])
    : { searches: [], reads: [] };
  const citations = rag ? buildCitations(rag) : [];
  const evidenceRefs = normalizeEvidence(evidence);
  const summary = evidenceSummary(evidenceRefs);
  const supportedIds = new Set(pedagogy?.evidence_ids ?? []);
  const successfulReads = web.reads.filter((read) => read.ok).length;
  const webUsed = web.searches.length > 0 || web.reads.length > 0;
  const webError = rag?.web_tools?.error;
  const recoveredResearchUsed = Boolean(rag?.web_context?.used && rag.web_context.run_id);
  if (!pedagogy && citations.length === 0 && !webUsed && !webError && !recoveredResearchUsed) return null;
  return (
    <div className="evidence-trail">
      <button className="evidence-toggle" onClick={() => setOpen((v) => !v)} type="button">
        {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        证据轨迹
        {pedagogy ? (
          <span className="move-badge">
            {protocolLabel(pedagogy.mode)} · {moveLabel(pedagogy.move)}
          </span>
        ) : null}
        {web.searches.length ? <span className="web-flag">查询 {web.searches.length}</span> : null}
        {successfulReads ? <span className="web-flag">阅读 {successfulReads}</span> : null}
        {recoveredResearchUsed ? <span className="web-flag">恢复研究来源</span> : null}
        {citations.length ? <span className="cite-flag">本地引用 {citations.length}</span> : null}
        {summary.total ? (
          <span className="evidence-summary-flag">
            统一证据 {summary.total}（本地 {summary.local} · 联网 {summary.web}）
          </span>
        ) : null}
      </button>
      {open ? (
        <div className="evidence-detail">
          {webError ? <div className="evidence-error">联网工具错误：{webError}</div> : null}
          {recoveredResearchUsed ? (
            <div className="web-call-card" data-research-run-id={rag?.web_context?.run_id}>
              本轮回答采用了已恢复的联网研究证据。
            </div>
          ) : null}
          {evidenceRefs.length ? (
            <div className="evidence-unified">
              <div className="evidence-unified-header">
                <span>统一证据（去重后 {evidenceRefs.length} 条）</span>
                <button
                  className="ghost-action compact"
                  onClick={() => navigator.clipboard.writeText(formatEvidencePlainText(pedagogy, evidenceRefs))}
                  type="button"
                  title="复制纯正文"
                >
                  <Clipboard size={12} /> 复制
                </button>
              </div>
              {STATUS_ORDER.filter((s) => evidenceRefs.some((r) => r.status === s)).map((status) => (
                <div key={status} className="evidence-status-group">
                  <div className="evidence-status-label">
                    {status === "selected" ? <CheckCircle2 size={12} /> : status === "rejected" ? <XCircle size={12} /> : null}
                    {STATUS_LABELS[status]}
                  </div>
                  {evidenceRefs
                    .filter((r) => r.status === status)
                    .map((ref, i) => (
                      <div key={`${ref.id}-${i}`} className="evidence-ref-row">
                        {supportedIds.has(ref.id) ? <span className="evidence-ref-supported" title="教学法引用">引</span> : null}
                        <span className="evidence-ref-type">
                          {ref.type === "local" ? "本地" : ref.type === "web_search" ? "搜索" : ref.type === "web_read" ? "阅读" : "研究"}
                        </span>
                        {ref.url ? (
                          <a className="evidence-ref-link" href={ref.url} target="_blank" rel="noreferrer">{ref.title || ref.url}</a>
                        ) : (
                          <span className="evidence-ref-title">{ref.title || ref.source}</span>
                        )}
                        {ref.score > 0 ? <span className="evidence-ref-score">{ref.score.toFixed(2)}</span> : null}
                      </div>
                    ))}
                </div>
              ))}
            </div>
          ) : null}
          {web.searches.map((s, i) => (
            <div key={`s${i}`} className="web-call-card">
              <div className="web-call-head">
                <Search size={13} /> 搜索 “{s.query}”
              </div>
              {s.results.length ? (
                s.results.slice(0, 3).map((r, j) => (
                  <a key={`${r.url ?? r.title ?? j}`} className="web-result" href={r.url} target="_blank" rel="noreferrer">
                    {r.title || r.url}
                    {r.url ? <span className="web-url">{r.url}</span> : null}
                  </a>
                ))
              ) : (
                <p className="web-preview">本次查询没有返回可展示的结果。</p>
              )}
            </div>
          ))}
          {web.reads.map((r, i) => (
            <div key={`r${i}`} className="web-call-card">
              <div className="web-call-head">
                <FileText size={13} /> 阅读 {r.url}
              </div>
              <p className="web-preview">{r.error ? `读取失败：${r.error}` : r.preview}</p>
            </div>
          ))}
          {citations.length ? (
            <ol className="citation-list">
              {citations.map((c, i) => (
                <li key={`${c.source}-${c.title}`}>
                  <strong>[{i + 1}]</strong> {c.title} <span className="cite-src">{c.source}</span>{" "}
                  <span className="cite-score">{c.score.toFixed(2)}</span>
                </li>
              ))}
            </ol>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
