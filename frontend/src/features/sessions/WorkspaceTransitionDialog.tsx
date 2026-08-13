import { AlertTriangle } from "lucide-react";

import { SlideOver } from "../../components/SlideOver";
import type { WorkspaceTransitionNotice } from "./workspaceTransitionGuard";

export function WorkspaceTransitionDialog({
  notice,
  onCancel,
  onConfirm,
}: {
  notice: WorkspaceTransitionNotice | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <SlideOver open={Boolean(notice)} title={notice?.title ?? "处理未完成工作"} onClose={onCancel}>
      {notice ? (
        <section className="workspace-transition-dialog" aria-describedby="workspace-transition-description">
          <p id="workspace-transition-description">{notice.description}</p>
          <ul className="workspace-transition-issues">
            {notice.issues.map((issue) => (
              <li key={issue.id}>
                <AlertTriangle aria-hidden="true" size={16} />
                <div>
                  <strong>{issue.label}</strong>
                  <span>{issue.effect}</span>
                </div>
              </li>
            ))}
          </ul>
          <div className="workspace-transition-actions">
            <button className="ghost-action" onClick={onCancel} type="button">
              留在当前会话
            </button>
            <button className="primary-action danger" onClick={onConfirm} type="button">
              {notice.confirmLabel}
            </button>
          </div>
        </section>
      ) : null}
    </SlideOver>
  );
}
