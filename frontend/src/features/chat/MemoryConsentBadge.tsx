import { ShieldCheck, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import {
  loadSessionDetail,
  revokeSessionMemoryConsent,
} from "../../api";

// G16 decision 11: visible revocation for the per-session memory grant.
// Shown only when the ask policy is active and the session has granted;
// revoking clears the backend grant immediately (CAS) and the next
// first question re-confirms.
export function MemoryConsentBadge({
  sessionId,
  memoryPolicy,
  revision,
  onChanged,
}: {
  sessionId?: string | null;
  memoryPolicy?: string;
  revision?: number;
  onChanged?: () => void;
}) {
  const [granted, setGranted] = useState(false);
  const [busy, setBusy] = useState(false);

  const resolve = useCallback(async () => {
    if (!sessionId || memoryPolicy !== "ask") {
      setGranted(false);
      return;
    }
    try {
      const detail = await loadSessionDetail(sessionId);
      setGranted(Boolean(detail.settings?.memory_consent_granted));
    } catch {
      setGranted(false);
    }
  }, [sessionId, memoryPolicy]);

  useEffect(() => {
    void resolve();
  }, [resolve, revision]);

  if (!granted) return null;

  const revoke = async () => {
    if (!sessionId) return;
    setBusy(true);
    try {
      await revokeSessionMemoryConsent(sessionId);
      setGranted(false);
      onChanged?.();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="memory-consent-badge" role="status">
      <ShieldCheck size={14} />
      <span>本会话已启用跨会话记忆</span>
      <button
        aria-label="撤销本会话记忆授权"
        disabled={busy}
        onClick={() => void revoke()}
        title="撤销后立即生效；下次首次使用时会再次询问"
        type="button"
      >
        <X size={13} />
        撤销
      </button>
    </div>
  );
}
