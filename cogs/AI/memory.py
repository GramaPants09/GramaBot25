"""SQLite-backed conversation memory for the AgentBrain.

Replaces the old whole-file-rewrite ``cogs/jsonfiles/memory.json`` pattern.
Turns are keyed by ``(user_id, channel_id)`` so the same person has separate
context in different channels, plus an optional rolling summary per key.

Pure-stdlib (sqlite3) so it imports and tests anywhere.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time


class Memory:
    def __init__(self, db_path: str = "data/brain.db"):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS turns (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                ts         REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_turns_key ON turns(user_id, channel_id, id);
            CREATE TABLE IF NOT EXISTS summaries (
                user_id    TEXT NOT NULL,
                channel_id TEXT NOT NULL,
                summary    TEXT NOT NULL,
                PRIMARY KEY (user_id, channel_id)
            );
            """
        )
        self._conn.commit()

    def add_turn(self, user_id: str, channel_id: str, role: str, content: str) -> None:
        self._conn.execute(
            "INSERT INTO turns(user_id, channel_id, role, content, ts) VALUES (?,?,?,?,?)",
            (str(user_id), str(channel_id), role, content, time.time()),
        )
        self._conn.commit()

    def history(self, user_id: str, channel_id: str, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            """
            SELECT role, content FROM turns
            WHERE user_id = ? AND channel_id = ?
            ORDER BY id DESC LIMIT ?
            """,
            (str(user_id), str(channel_id), limit),
        ).fetchall()
        return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]

    def clear(self, user_id: str, channel_id: str) -> int:
        """Wipe turns + summary for one (user, channel). Returns rows deleted."""
        cur = self._conn.execute(
            "DELETE FROM turns WHERE user_id = ? AND channel_id = ?",
            (str(user_id), str(channel_id)),
        )
        self._conn.execute(
            "DELETE FROM summaries WHERE user_id = ? AND channel_id = ?",
            (str(user_id), str(channel_id)),
        )
        self._conn.commit()
        return cur.rowcount

    def get_summary(self, user_id: str, channel_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT summary FROM summaries WHERE user_id = ? AND channel_id = ?",
            (str(user_id), str(channel_id)),
        ).fetchone()
        return row["summary"] if row else None

    def set_summary(self, user_id: str, channel_id: str, summary: str) -> None:
        self._conn.execute(
            """
            INSERT INTO summaries(user_id, channel_id, summary) VALUES (?,?,?)
            ON CONFLICT(user_id, channel_id) DO UPDATE SET summary = excluded.summary
            """,
            (str(user_id), str(channel_id), summary),
        )
        self._conn.commit()

    @classmethod
    def import_json(cls, json_path: str, db_path: str) -> int:
        """Migrate the legacy memory.json into SQLite under channel ``"legacy"``.

        The old format stored a list of strings per key, where user turns were
        prefixed ``"User: "`` and everything else was an assistant turn. Returns
        the number of turns imported (0 if the file is missing/empty).
        """
        mem = cls(db_path=db_path)
        if not os.path.exists(json_path):
            return 0
        try:
            with open(json_path, "r") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return 0

        count = 0
        for key, items in (data or {}).items():
            if not isinstance(items, list):
                continue
            for item in items:
                text = str(item)
                if text.startswith("User: "):
                    role, content = "user", text[len("User: "):]
                else:
                    role, content = "assistant", text
                mem.add_turn(key, "legacy", role, content)
                count += 1
        return count
