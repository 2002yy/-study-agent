"""Global runtime schema migration for P2-D semantic closure and resume links."""

from __future__ import annotations


LEARNING_SEMANTIC_MIGRATION_V18 = """
CREATE TABLE learning_goal_contexts (
    goal_id TEXT PRIMARY KEY REFERENCES learning_goals(id),
    thread_id TEXT NOT NULL REFERENCES chat_threads(id),
    focused_at TEXT NOT NULL,
    focus_pinned INTEGER NOT NULL DEFAULT 0 CHECK(focus_pinned IN (0, 1))
);

CREATE INDEX idx_learning_goal_contexts_thread_focus
    ON learning_goal_contexts(thread_id, focused_at DESC, goal_id);

CREATE UNIQUE INDEX idx_learning_goal_contexts_one_pinned_per_thread
    ON learning_goal_contexts(thread_id)
    WHERE focus_pinned = 1;

CREATE TABLE learning_goal_claim_revisions (
    goal_id TEXT NOT NULL REFERENCES learning_goals(id),
    claim_revision_id TEXT NOT NULL REFERENCES claim_revisions(id),
    created_at TEXT NOT NULL,
    PRIMARY KEY(goal_id, claim_revision_id)
);

CREATE INDEX idx_learning_goal_claim_revisions_revision
    ON learning_goal_claim_revisions(claim_revision_id, goal_id);
"""
