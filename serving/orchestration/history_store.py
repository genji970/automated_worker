from __future__ import annotations

import json
import time
import uuid
from typing import Any

import aiosqlite

from inference.config import STATE_DIR


DB_PATH = STATE_DIR / "conversation_history.sqlite3"


async def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT,
                payload_json TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id)
            )
            """
        )
        await conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_conversation_time
            ON messages(conversation_id, created_at)
            """
        )
        await conn.commit()


async def ensure_conversation(conversation_id: str | None = None) -> str:
    await init_db()

    now = time.time()
    cid = conversation_id or str(uuid.uuid4())

    async with aiosqlite.connect(DB_PATH) as conn:
        row_cursor = await conn.execute(
            "SELECT id FROM conversations WHERE id = ?",
            (cid,),
        )
        row = await row_cursor.fetchone()
        await row_cursor.close()

        if row is None:
            await conn.execute(
                "INSERT INTO conversations (id, created_at, updated_at) VALUES (?, ?, ?)",
                (cid, now, now),
            )
        else:
            await conn.execute(
                "UPDATE conversations SET updated_at = ? WHERE id = ?",
                (now, cid),
            )

        await conn.commit()

    return cid


async def append_message(
    *,
    conversation_id: str,
    role: str,
    content: str | None,
    payload: dict[str, Any] | None = None,
) -> None:
    await init_db()

    now = time.time()
    message_id = str(uuid.uuid4())

    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """
            INSERT INTO messages (
                id, conversation_id, role, content, payload_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                conversation_id,
                role,
                content,
                json.dumps(payload or {}, ensure_ascii=False),
                now,
            ),
        )
        await conn.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        await conn.commit()


async def load_history(
    *,
    conversation_id: str,
    limit: int = 20,
) -> list[dict[str, Any]]:
    await init_db()

    async with aiosqlite.connect(DB_PATH) as conn:
        conn.row_factory = aiosqlite.Row

        cursor = await conn.execute(
            """
            SELECT role, content, payload_json
            FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (conversation_id, limit),
        )
        rows = await cursor.fetchall()
        await cursor.close()

    messages: list[dict[str, Any]] = []

    for row in reversed(rows):
        payload: dict[str, Any] = {}

        if row["payload_json"]:
            try:
                payload = json.loads(row["payload_json"])
            except json.JSONDecodeError:
                payload = {}

        message = {
            "role": row["role"],
            "content": row["content"] or "",
        }
        message.update(payload)
        messages.append(message)

    return messages


def extract_last_user_message(
    messages: list[dict[str, Any]],
) -> dict[str, Any] | None:
    for message in reversed(messages):
        if message.get("role") == "user":
            return message
    return None
