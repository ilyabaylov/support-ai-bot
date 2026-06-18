"""Мини-аналитика на стандартном sqlite3 — без лишних зависимостей.

Пишем по одному событию на каждый вопрос (с исходом) и отдельное событие
на каждое обращение к администратору. Этого хватает для честной статистики
в админке: сколько спросили, на сколько ответили сами, сколько ушло людям.

sqlite3 синхронный, поэтому каждый вызов гоняем в отдельном потоке через
asyncio.to_thread — event loop бота не блокируется.
"""
from __future__ import annotations

import asyncio
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "stats.db"

# исходы вопроса (одно событие на вопрос)
ANSWERED = "answered"            # ответили по базе
LOW_CONFIDENCE = "low_confidence"  # не нашли в базе
NO_ANSWER = "no_answer"          # модель сама призналась, что ответа нет
HANDOFF = "handoff"              # клиента передали администратору

_QUESTION_KINDS = (ANSWERED, LOW_CONFIDENCE, NO_ANSWER)


class Stats:
    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        return sqlite3.connect(self._db_path)

    async def init(self) -> None:
        await asyncio.to_thread(self._init_sync)

    def _init_sync(self) -> None:
        con = self._connect()
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts       REAL    NOT NULL,
                    user_id  INTEGER,
                    username TEXT,
                    kind     TEXT    NOT NULL,
                    score    REAL,
                    question TEXT
                )
                """
            )
            con.commit()
        finally:
            con.close()

    async def log(
        self,
        *,
        user_id: int | None,
        username: str | None,
        kind: str,
        score: float | None = None,
        question: str | None = None,
    ) -> None:
        await asyncio.to_thread(self._log_sync, user_id, username, kind, score, question)

    def _log_sync(self, user_id, username, kind, score, question) -> None:
        con = self._connect()
        try:
            con.execute(
                "INSERT INTO events (ts, user_id, username, kind, score, question) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), user_id, username, kind, score, question),
            )
            con.commit()
        finally:
            con.close()

    async def summary(self) -> dict:
        return await asyncio.to_thread(self._summary_sync)

    def _summary_sync(self) -> dict:
        con = self._connect()
        try:
            cur = con.cursor()
            placeholders = ",".join("?" for _ in _QUESTION_KINDS)
            total = cur.execute(
                f"SELECT COUNT(*) FROM events WHERE kind IN ({placeholders})",
                _QUESTION_KINDS,
            ).fetchone()[0]
            answered = cur.execute(
                "SELECT COUNT(*) FROM events WHERE kind = ?", (ANSWERED,)
            ).fetchone()[0]
            handoffs = cur.execute(
                "SELECT COUNT(*) FROM events WHERE kind = ?", (HANDOFF,)
            ).fetchone()[0]
            users = cur.execute(
                "SELECT COUNT(DISTINCT user_id) FROM events"
            ).fetchone()[0]
            week_ago = time.time() - 7 * 86400
            last7 = cur.execute(
                f"SELECT COUNT(*) FROM events WHERE ts >= ? AND kind IN ({placeholders})",
                (week_ago, *_QUESTION_KINDS),
            ).fetchone()[0]
            return {
                "total": total,
                "answered": answered,
                "handoffs": handoffs,
                "users": users,
                "last7": last7,
            }
        finally:
            con.close()

    async def recent_handoffs(self, limit: int = 10) -> list[tuple[float, str | None, str | None]]:
        return await asyncio.to_thread(self._recent_sync, limit)

    def _recent_sync(self, limit: int):
        con = self._connect()
        try:
            return con.execute(
                "SELECT ts, username, question FROM events WHERE kind = ? "
                "ORDER BY id DESC LIMIT ?",
                (HANDOFF, limit),
            ).fetchall()
        finally:
            con.close()
