"""SQLite storage. OWNER: Person C.

Deliberately dumb: one table, the whole issue stored as JSON under its id.
The JSON shape is the contract in fixtures/sample_issue.json, so nobody has to
run a migration when a field is added at 2pm.
"""

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

DB_PATH = os.environ.get("REPAIRRECORD_DB", "repairrecord.db")


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS issues (
                id          TEXT PRIMARY KEY,
                created_at  TEXT NOT NULL,
                data        TEXT NOT NULL
            )
            """
        )


def now_iso() -> str:
    """Server time. Never trust a client-supplied timestamp — that is the whole
    point of this product."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def new_id(prefix: str = "iss") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def save(issue: dict[str, Any]) -> dict[str, Any]:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO issues (id, created_at, data) VALUES (?, ?, ?)",
            (issue["id"], issue["created_at"], json.dumps(issue)),
        )
    return issue


def get(issue_id: str) -> dict[str, Any] | None:
    with _conn() as conn:
        row = conn.execute("SELECT data FROM issues WHERE id = ?", (issue_id,)).fetchone()
    return json.loads(row["data"]) if row else None


def list_all() -> list[dict[str, Any]]:
    with _conn() as conn:
        rows = conn.execute("SELECT data FROM issues ORDER BY created_at DESC").fetchall()
    return [json.loads(r["data"]) for r in rows]


def add_event(issue: dict[str, Any], type_: str, note: str) -> dict[str, Any]:
    issue.setdefault("events", []).append({"type": type_, "at": now_iso(), "note": note})
    return issue
