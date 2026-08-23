"""SQLite repository for G14 temporary session attachments."""

from __future__ import annotations

import json
from typing import Any

from src.domain.runtime_entities import SessionAttachment, utc_now
from src.infrastructure.sqlite.database import RuntimeDatabase


def _dump(value: Any) -> str:
    return json.dumps(list(value), ensure_ascii=False, sort_keys=True)


def _load_list(raw: str) -> tuple[dict[str, Any], ...]:
    try:
        parsed = json.loads(raw or "[]")
    except (TypeError, ValueError):
        return ()
    if not isinstance(parsed, list):
        return ()
    return tuple(item for item in parsed if isinstance(item, dict))


class SessionAttachmentRepository:
    def __init__(self, database: RuntimeDatabase):
        self.database = database
        self.database.initialize()

    def create(self, attachment: SessionAttachment) -> SessionAttachment:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO session_attachments(
                    id, thread_id, filename, content_hash, mime_type,
                    size_bytes, storage_path, status, stage_error,
                    stage_history, retry_count, promoted_rag_run_id,
                    external_calls, created_at, updated_at, version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attachment.id, attachment.thread_id, attachment.filename,
                    attachment.content_hash, attachment.mime_type,
                    attachment.size_bytes, attachment.storage_path,
                    attachment.status, attachment.stage_error,
                    _dump(attachment.stage_history), attachment.retry_count,
                    attachment.promoted_rag_run_id,
                    _dump(attachment.external_calls),
                    attachment.created_at, attachment.updated_at,
                    attachment.version,
                ),
            )
        return attachment

    def get(self, attachment_id: str) -> SessionAttachment | None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM session_attachments WHERE id = ?",
                (attachment_id,),
            ).fetchone()
        return _from_row(row) if row is not None else None

    def list_by_thread(self, thread_id: str) -> list[SessionAttachment]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM session_attachments WHERE thread_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (thread_id,),
            ).fetchall()
        return [_from_row(row) for row in rows]

    def count_by_thread(self, thread_id: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM session_attachments WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def total_bytes_by_thread(self, thread_id: str) -> int:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM session_attachments"
                " WHERE thread_id = ?",
                (thread_id,),
            ).fetchone()
        return int(row[0]) if row is not None else 0

    def find_hash_in_thread(
        self, thread_id: str, content_hash: str
    ) -> SessionAttachment | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM session_attachments
                WHERE thread_id = ? AND content_hash = ?
                ORDER BY created_at ASC LIMIT 1
                """,
                (thread_id, content_hash),
            ).fetchone()
        return _from_row(row) if row is not None else None

    def transition_status(
        self,
        attachment_id: str,
        *,
        expected_statuses: frozenset[str] | set[str],
        new_status: str,
        stage_entry: dict[str, Any] | None = None,
        stage_error: str = "",
    ) -> SessionAttachment:
        """CAS status transition that appends the stage history entry."""
        now = utc_now()
        with self.database.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT status FROM session_attachments WHERE id = ?",
                (attachment_id,),
            ).fetchone()
            if row is None:
                connection.rollback()
                raise ValueError(f"Session attachment not found: {attachment_id}")
            if row["status"] not in expected_statuses:
                connection.rollback()
                raise ValueError(
                    f"Session attachment {attachment_id} is not transitionable "
                    f"from {row['status']!r} to {new_status!r}"
                )
            history = _history_from_connection(connection, attachment_id)
            if stage_entry is not None:
                history = (*history, dict(stage_entry))
            cursor = connection.execute(
                """
                UPDATE session_attachments
                SET status = ?, stage_error = ?, stage_history = ?,
                    updated_at = ?, version = version + 1
                WHERE id = ?
                """,
                (
                    new_status, stage_error, _dump(history), now,
                    attachment_id,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise ValueError(
                    f"Session attachment update failed: {attachment_id}"
                )
            connection.commit()
        updated = self.get(attachment_id)
        if updated is None:
            raise ValueError(f"Session attachment not found: {attachment_id}")
        return updated

    def mark_promoted(self, attachment_id: str, rag_run_id: str) -> SessionAttachment:
        now = utc_now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE session_attachments
                SET promoted_rag_run_id = ?, updated_at = ?,
                    version = version + 1
                WHERE id = ?
                """,
                (rag_run_id, now, attachment_id),
            )
        if cursor.rowcount != 1:
            raise ValueError(
                f"Session attachment not found: {attachment_id}"
            )
        updated = self.get(attachment_id)
        if updated is None:
            raise ValueError(f"Session attachment not found: {attachment_id}")
        return updated

    def record_external_call(
        self, attachment_id: str, call: dict[str, Any]
    ) -> SessionAttachment:
        existing = self.get(attachment_id)
        if existing is None:
            raise ValueError(f"Session attachment not found: {attachment_id}")
        calls = (*existing.external_calls, dict(call))
        now = utc_now()
        with self.database.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE session_attachments
                SET external_calls = ?, updated_at = ?, version = version + 1
                WHERE id = ?
                """,
                (_dump(calls), now, attachment_id),
            )
        if cursor.rowcount != 1:
            raise ValueError(
                f"Session attachment not found: {attachment_id}"
            )
        updated = self.get(attachment_id)
        if updated is None:
            raise ValueError(f"Session attachment not found: {attachment_id}")
        return updated

    def delete(self, attachment_id: str) -> bool:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM session_attachments WHERE id = ?", (attachment_id,)
            )
        return cursor.rowcount == 1

    def delete_by_thread(self, thread_id: str) -> int:
        with self.database.connect() as connection:
            cursor = connection.execute(
                "DELETE FROM session_attachments WHERE thread_id = ?",
                (thread_id,),
            )
        return cursor.rowcount


def _history_from_connection(connection, attachment_id: str) -> tuple[
    dict[str, Any], ...
]:
    row = connection.execute(
        "SELECT stage_history FROM session_attachments WHERE id = ?",
        (attachment_id,),
    ).fetchone()
    if row is None:
        return ()
    return _load_list(row["stage_history"])


def _from_row(row) -> SessionAttachment:
    return SessionAttachment(
        id=row["id"],
        thread_id=row["thread_id"],
        filename=row["filename"],
        content_hash=row["content_hash"],
        mime_type=row["mime_type"],
        size_bytes=int(row["size_bytes"]),
        storage_path=row["storage_path"],
        status=row["status"],
        stage_error=row["stage_error"],
        stage_history=_load_list(row["stage_history"]),
        retry_count=int(row["retry_count"]),
        promoted_rag_run_id=row["promoted_rag_run_id"],
        external_calls=_load_list(row["external_calls"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        version=int(row["version"]),
    )
