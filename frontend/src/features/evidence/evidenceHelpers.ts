import type { ChatResponse, PedagogySummary, TurnEvidence, WebToolCall } from "../../types";

export type WebSearchSummary = {
  query: string;
  results: { title?: string; url?: string; snippet?: string }[];
};
export type WebReadSummary = { url: string; ok: boolean; preview: string; error?: string };
export type WebCallsSummary = { searches: WebSearchSummary[]; reads: WebReadSummary[] };

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" ? (value as Record<string, unknown>) : {};
}

export function summarizeWebCalls(calls: WebToolCall[] | undefined): WebCallsSummary {
  const out: WebCallsSummary = { searches: [], reads: [] };
  for (const call of calls ?? []) {
    if (call.name === "web_search") {
      const rawResults = Array.isArray((call.result as { results?: unknown }).results)
        ? ((call.result as { results: unknown[] }).results ?? [])
        : [];
      const results = rawResults.flatMap((value) => {
        const result = asRecord(value);
        const title = String(result.title ?? "").trim();
        const url = String(result.url ?? "").trim();
        const snippet = String(result.snippet ?? "").trim();
        if (!title && !url) return [];
        return [{ title: title || undefined, url: url || undefined, snippet: snippet || undefined }];
      });
      const query = String(call.arguments.query ?? "").trim();
      if (query || results.length) out.searches.push({ query, results });
    } else if (call.name === "web_read") {
      const r = asRecord(call.result);
      const url = String(call.arguments.url ?? r.url ?? "").trim();
      const ok = r.ok === true || r.ok === "true";
      const preview = String(r.content ?? "").slice(0, 300);
      const error = String(r.error ?? "").trim() || undefined;
      if (url || preview || error) out.reads.push({ url, ok, preview, error });
    }
  }
  return out;
}

export type Citation = { title: string; source: string; score: number };

function basename(path: string): string {
  const parts = path.split(/[\\/]/).filter(Boolean);
  return parts[parts.length - 1] ?? path;
}

export function buildCitations(rag: ChatResponse["rag"]): Citation[] {
  const results = (rag.results ?? []) as Array<Record<string, unknown>>;
  const seen = new Set<string>();
  return results.flatMap((result) => {
    const chunk = asRecord(result.chunk);
    const source = String(
      chunk.source_path ?? result.source_path ?? result.source ?? ""
    ).trim();
    const rawTitle = String(chunk.title ?? result.title ?? "").trim();
    const score = Number(result.score ?? 0);
    if ((!rawTitle && !source) || !Number.isFinite(score) || score <= 0) return [];
    const title = rawTitle || basename(source);
    const key = `${source}\u0000${title}`;
    if (seen.has(key)) return [];
    seen.add(key);
    return [{ title, source, score }];
  });
}

export function evidenceFromResponse(resp: ChatResponse): TurnEvidence {
  return { pedagogy: resp.pedagogy, rag: resp.rag, route: resp.route };
}

export type EvidenceRef = {
  id: string;
  type: "local" | "web_search" | "web_read" | "research";
  title: string;
  source: string;
  domain: string;
  url: string;
  score: number;
  status: "candidate" | "read" | "selected" | "rejected";
};

const STATUS_PRIORITY: Record<EvidenceRef["status"], number> = {
  selected: 0,
  read: 1,
  rejected: 2,
  candidate: 3,
};

function domainOf(url: string): string {
  try {
    return new URL(url).hostname || "";
  } catch {
    return "";
  }
}

/** Normalize a TurnEvidence into a unified, deduped, filtered EvidenceRef list (G13). */
export function normalizeEvidence(evidence: TurnEvidence): EvidenceRef[] {
  const rag = evidence.rag;
  const refs: EvidenceRef[] = [];

  for (const item of (rag?.results ?? []) as Array<Record<string, unknown>>) {
    // Current RagResult keeps source identity inside `chunk`. Top-level fields are
    // retained only as a compatibility fallback for historical snapshots.
    const chunk = asRecord(item.chunk);
    const chunkId = String(chunk.chunk_id ?? item.chunk_id ?? "").trim();
    const source = String(
      chunk.source_path ?? item.source_path ?? item.source ?? ""
    ).trim();
    const rawTitle = String(chunk.title ?? item.title ?? "").trim();
    const title = rawTitle || (source ? basename(source) : "");
    refs.push({
      id: chunkId || source || title,
      type: "local",
      title,
      source,
      domain: "",
      url: "",
      score: Number(item.score ?? 0),
      status: "candidate",
    });
  }

  for (const call of rag?.web_tools?.calls ?? []) {
    const name = String(call.name ?? "");
    const arguments_ = asRecord(call.arguments);
    const result = asRecord(call.result);
    if (name === "web_search") {
      const results = Array.isArray(result.results) ? (result.results as Array<Record<string, unknown>>) : [];
      for (const r of results) {
        const title = String(r.title ?? "");
        const url = String(r.url ?? "");
        if (!title && !url) continue;
        refs.push({ id: url || title, type: "web_search", title, source: "", domain: domainOf(url), url, score: 0, status: "candidate" });
      }
    } else if (name === "web_read") {
      const url = String(arguments_.url ?? result.url ?? "");
      if (!url) continue;
      refs.push({ id: url, type: "web_read", title: url, source: "", domain: domainOf(url), url, score: 0, status: "read" });
    }
  }

  // filter placeholders
  const filtered = refs.filter((r) => {
    if (!r.id || (!r.title && !r.url && !r.source)) return false;
    if (r.type === "local" && (!Number.isFinite(r.score) || r.score <= 0)) return false;
    return true;
  });

  // Keep stable evidence-unit identity when available. This prevents two chunks
  // from the same source from collapsing into the wrong pedagogy evidence id.
  // Historical local snapshots without chunk ids still fall back to source/title.
  const best = new Map<string, EvidenceRef>();
  for (const ref of filtered) {
    const key = ref.url
      ? `url:${ref.url}`
      : ref.id
        ? `id:${ref.type}:${ref.id}`
        : ref.source
          ? `src:${ref.type}:${ref.source}`
          : `title:${ref.type}:${ref.title}`;
    const existing = best.get(key);
    if (!existing) {
      best.set(key, ref);
      continue;
    }
    if (STATUS_PRIORITY[ref.status] < STATUS_PRIORITY[existing.status]) {
      best.set(key, ref);
    } else if (STATUS_PRIORITY[ref.status] === STATUS_PRIORITY[existing.status] && ref.score > existing.score) {
      best.set(key, ref);
    }
  }
  return Array.from(best.values());
}

export type EvidenceSummary = {
  local: number;
  web: number;
  selected: number;
  rejected: number;
  total: number;
};

export function evidenceSummary(refs: EvidenceRef[]): EvidenceSummary {
  return {
    local: refs.filter((r) => r.type === "local").length,
    web: refs.filter((r) => r.type === "web_search" || r.type === "web_read").length,
    selected: refs.filter((r) => r.status === "selected").length,
    rejected: refs.filter((r) => r.status === "rejected").length,
    total: refs.length,
  };
}

export function pedagogySummaryFromSnapshot(snap: unknown): PedagogySummary | undefined {
  if (!snap || typeof snap !== "object") return undefined;
  const o = snap as Record<string, unknown>;
  if (typeof o.mode !== "string" && typeof o.move !== "string") return undefined;
  const evidenceIds = Array.isArray(o.evidence_ids)
    ? o.evidence_ids.map((value) => String(value).trim()).filter(Boolean)
    : [];
  return {
    mode: String(o.mode ?? ""),
    phase: String(o.phase ?? ""),
    move: String(o.move ?? ""),
    disclosure_level: Number(o.disclosure_level ?? 0),
    ...(evidenceIds.length ? { evidence_ids: evidenceIds } : {}),
  };
}

type SessionTurn = {
  turn_id: string;
  pedagogy_snapshot?: Record<string, unknown>;
  route_snapshot?: Record<string, unknown>;
  rag_snapshot?: Record<string, unknown>;
};

export function evidenceFromSessionTurns(turns: SessionTurn[]): Map<string, TurnEvidence> {
  const map = new Map<string, TurnEvidence>();
  for (const turn of turns) {
    const pedagogy = pedagogySummaryFromSnapshot(turn.pedagogy_snapshot);
    const rag =
      turn.rag_snapshot && Object.keys(turn.rag_snapshot).length
        ? (turn.rag_snapshot as ChatResponse["rag"])
        : undefined;
    const route =
      turn.route_snapshot && Object.keys(turn.route_snapshot).length
        ? turn.route_snapshot
        : undefined;
    if (pedagogy || rag || route) {
      map.set(turn.turn_id, { pedagogy, rag, route });
    }
  }
  return map;
}
