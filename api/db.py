"""SQLite storage (plan, Section 5.4): posts and cached analyzer runs.

Hashtags are not stored; they are derived from captions when posts are loaded.
The engine works on posts in memory, so another database can replace this module
without touching the engine.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any

from contentiq_engine.models import Post

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id        TEXT PRIMARY KEY,
    account   TEXT NOT NULL,
    caption   TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    likes     INTEGER NOT NULL DEFAULT 0,
    comments  INTEGER NOT NULL DEFAULT 0,
    followers INTEGER,
    source    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    module      TEXT NOT NULL,
    params_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS runs_module ON runs (module, run_id);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._lock = threading.Lock()  # one writer at a time; SQLite allows concurrent readers
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ---- posts ----------------------------------------------------------------

    def upsert_posts(self, posts: Iterable[Post], source: str) -> int:
        rows = [
            (p.id, p.account, p.caption, p.timestamp.isoformat(), p.likes, p.comments, p.followers, source)
            for p in posts
        ]
        with self._lock, self._connect() as conn:
            conn.executemany(
                "INSERT INTO posts (id, account, caption, timestamp, likes, comments, followers, source) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET account=excluded.account, caption=excluded.caption, "
                "timestamp=excluded.timestamp, likes=excluded.likes, comments=excluded.comments, "
                "followers=excluded.followers, source=excluded.source",
                rows,
            )
        return len(rows)

    def count_posts(self) -> int:
        with self._connect() as conn:
            return conn.execute("SELECT COUNT(*) FROM posts").fetchone()[0]

    def list_posts(self, limit: int | None = None, offset: int = 0) -> list[Post]:
        sql = "SELECT * FROM posts ORDER BY timestamp, id"
        params: tuple = ()
        if limit is not None:
            sql += " LIMIT ? OFFSET ?"
            params = (limit, offset)
        with self._connect() as conn:
            return [_row_to_post(r) for r in conn.execute(sql, params)]

    def delete_posts(self) -> int:
        with self._lock, self._connect() as conn:
            return conn.execute("DELETE FROM posts").rowcount

    # ---- runs -----------------------------------------------------------------

    def save_run(self, module: str, params: dict[str, Any], result: dict[str, Any]) -> int:
        created = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO runs (module, params_json, result_json, created_at) VALUES (?, ?, ?, ?)",
                (module, json.dumps(params), json.dumps(result), created),
            )
            return int(cur.lastrowid)

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return _row_to_run(row) if row else None

    def latest_run(self, module: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE module = ? ORDER BY run_id DESC LIMIT 1", (module,)
            ).fetchone()
        return _row_to_run(row) if row else None


def _row_to_post(r: sqlite3.Row) -> Post:
    return Post(
        id=r["id"],
        account=r["account"],
        caption=r["caption"],
        timestamp=datetime.fromisoformat(r["timestamp"]),
        likes=r["likes"],
        comments=r["comments"],
        followers=r["followers"],
    )


def _row_to_run(r: sqlite3.Row) -> dict[str, Any]:
    return {
        "run_id": r["run_id"],
        "module": r["module"],
        "params": json.loads(r["params_json"]),
        "result": json.loads(r["result_json"]),
        "created_at": r["created_at"],
    }
