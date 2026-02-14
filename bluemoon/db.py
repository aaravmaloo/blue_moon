from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import aiosqlite


DEFAULT_GUILD_SETTINGS: dict[str, Any] = {
    "log_channel_id": None,
    "welcome_channel_id": None,
    "goodbye_channel_id": None,
    "staff_role_id": None,
    "dj_role_id": None,
    "autorole_id": None,
    "profanity_filter": True,
    "link_filter": False,
    "caps_threshold": 0.8,
    "anti_spam_msgs": 6,
    "anti_spam_window": 8,
    "anti_alt_hours": 24,
    "anti_join_spam_per_min": 10,
    "ticket_category_id": None,
    "ticket_transcript_channel": None,
    "ticket_feedback_channel": None,
    "ticket_sla_minutes": 60,
    "xp_rate": 1.0,
    "xp_voice_rate": 1.0,
    "economy_daily": 200,
    "economy_weekly": 1000,
    "economy_work_min": 50,
    "economy_work_max": 220,
    "economy_crime_win": 0.45,
    "economy_currency": "MoonCoin",
    "stats_channel_id": None,
    "confession_channel_id": None,
    "anonymous_channel_id": None,
    "auto_thread_channel_id": None,
}


def now_ts() -> int:
    return int(time.time())


@dataclass
class Balance:
    wallet: int
    bank: int


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                PRIMARY KEY (guild_id, key)
            );

            CREATE TABLE IF NOT EXISTS user_state (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                wallet INTEGER NOT NULL DEFAULT 0,
                bank INTEGER NOT NULL DEFAULT 0,
                xp INTEGER NOT NULL DEFAULT 0,
                level INTEGER NOT NULL DEFAULT 0,
                voice_seconds INTEGER NOT NULL DEFAULT 0,
                reputation INTEGER NOT NULL DEFAULT 0,
                thanks_count INTEGER NOT NULL DEFAULT 0,
                birthday TEXT,
                notes_json TEXT NOT NULL DEFAULT '[]',
                todos_json TEXT NOT NULL DEFAULT '[]',
                inventory_json TEXT NOT NULL DEFAULT '[]',
                last_daily INTEGER,
                last_weekly INTEGER,
                last_work INTEGER,
                last_crime INTEGER,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS bad_words (
                guild_id INTEGER NOT NULL,
                word TEXT NOT NULL,
                PRIMARY KEY (guild_id, word)
            );

            CREATE TABLE IF NOT EXISTS regex_filters (
                guild_id INTEGER NOT NULL,
                pattern TEXT NOT NULL,
                PRIMARY KEY (guild_id, pattern)
            );

            CREATE TABLE IF NOT EXISTS level_roles (
                guild_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (guild_id, level)
            );

            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                remind_at INTEGER NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scheduled_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                send_at INTEGER NOT NULL,
                created_by INTEGER NOT NULL,
                sent INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                opener_id INTEGER NOT NULL,
                ticket_type TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_staff_id INTEGER,
                created_at INTEGER NOT NULL,
                closed_at INTEGER
            );

            CREATE TABLE IF NOT EXISTS custom_commands (
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                response TEXT NOT NULL,
                PRIMARY KEY (guild_id, name)
            );

            CREATE TABLE IF NOT EXISTS auto_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                trigger_text TEXT NOT NULL,
                response_text TEXT NOT NULL,
                open_ticket INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                author_id INTEGER NOT NULL,
                quote_text TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS analytics_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                actor_id INTEGER,
                event_type TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS integration_feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                feed_type TEXT NOT NULL,
                source TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                last_item_id TEXT
            );

            CREATE TABLE IF NOT EXISTS role_buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                label TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                style INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                message_id INTEGER,
                prize TEXT NOT NULL,
                end_at INTEGER NOT NULL,
                winner_count INTEGER NOT NULL DEFAULT 1,
                entrants_json TEXT NOT NULL DEFAULT '[]',
                ended INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def execute(self, query: str, params: tuple[Any, ...] = ()) -> None:
        assert self.conn
        await self.conn.execute(query, params)
        await self.conn.commit()

    async def fetchone(self, query: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        assert self.conn
        async with self.conn.execute(query, params) as cur:
            return await cur.fetchone()

    async def fetchall(self, query: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        assert self.conn
        async with self.conn.execute(query, params) as cur:
            rows = await cur.fetchall()
        return rows

    async def set_setting(self, guild_id: int, key: str, value: Any) -> None:
        encoded = json.dumps(value)
        await self.execute(
            """
            INSERT INTO guild_settings (guild_id, key, value)
            VALUES (?, ?, ?)
            ON CONFLICT(guild_id, key) DO UPDATE SET value=excluded.value
            """,
            (guild_id, key, encoded),
        )

    async def get_setting(self, guild_id: int, key: str) -> Any:
        row = await self.fetchone(
            "SELECT value FROM guild_settings WHERE guild_id = ? AND key = ?",
            (guild_id, key),
        )
        if row is None:
            return DEFAULT_GUILD_SETTINGS.get(key)
        return json.loads(row["value"])

    async def get_user_row(self, guild_id: int, user_id: int) -> aiosqlite.Row:
        await self.execute(
            """
            INSERT INTO user_state (guild_id, user_id)
            VALUES (?, ?)
            ON CONFLICT(guild_id, user_id) DO NOTHING
            """,
            (guild_id, user_id),
        )
        row = await self.fetchone(
            "SELECT * FROM user_state WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        assert row is not None
        return row

    async def add_balance(self, guild_id: int, user_id: int, wallet_delta: int = 0, bank_delta: int = 0) -> Balance:
        row = await self.get_user_row(guild_id, user_id)
        new_wallet = max(0, row["wallet"] + wallet_delta)
        new_bank = max(0, row["bank"] + bank_delta)
        await self.execute(
            "UPDATE user_state SET wallet = ?, bank = ? WHERE guild_id = ? AND user_id = ?",
            (new_wallet, new_bank, guild_id, user_id),
        )
        return Balance(wallet=new_wallet, bank=new_bank)

    async def set_user_field(self, guild_id: int, user_id: int, field: str, value: Any) -> None:
        allowed = {
            "xp",
            "level",
            "voice_seconds",
            "reputation",
            "thanks_count",
            "birthday",
            "notes_json",
            "todos_json",
            "inventory_json",
            "last_daily",
            "last_weekly",
            "last_work",
            "last_crime",
        }
        if field not in allowed:
            raise ValueError(f"Unsupported field update: {field}")
        await self.get_user_row(guild_id, user_id)
        await self.execute(
            f"UPDATE user_state SET {field} = ? WHERE guild_id = ? AND user_id = ?",
            (value, guild_id, user_id),
        )

    async def log_event(self, guild_id: int, event_type: str, payload: dict[str, Any], actor_id: int | None = None) -> None:
        await self.execute(
            """
            INSERT INTO analytics_events (guild_id, actor_id, event_type, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, actor_id, event_type, json.dumps(payload), now_ts()),
        )

    async def get_bad_words(self, guild_id: int) -> set[str]:
        rows = await self.fetchall("SELECT word FROM bad_words WHERE guild_id = ?", (guild_id,))
        return {r["word"].lower() for r in rows}

    async def get_regex_filters(self, guild_id: int) -> list[str]:
        rows = await self.fetchall("SELECT pattern FROM regex_filters WHERE guild_id = ?", (guild_id,))
        return [r["pattern"] for r in rows]

    async def add_warning(self, guild_id: int, user_id: int, moderator_id: int, reason: str) -> None:
        await self.execute(
            """
            INSERT INTO warnings (guild_id, user_id, moderator_id, reason, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (guild_id, user_id, moderator_id, reason, now_ts()),
        )

    async def get_warnings(self, guild_id: int, user_id: int) -> list[aiosqlite.Row]:
        return await self.fetchall(
            "SELECT * FROM warnings WHERE guild_id = ? AND user_id = ? ORDER BY id DESC",
            (guild_id, user_id),
        )

    async def add_inventory_item(self, guild_id: int, user_id: int, item_name: str) -> list[str]:
        row = await self.get_user_row(guild_id, user_id)
        inventory = json.loads(row["inventory_json"])
        inventory.append(item_name)
        await self.set_user_field(guild_id, user_id, "inventory_json", json.dumps(inventory))
        return inventory

    async def get_inventory(self, guild_id: int, user_id: int) -> list[str]:
        row = await self.get_user_row(guild_id, user_id)
        return json.loads(row["inventory_json"])

    async def get_notes(self, guild_id: int, user_id: int) -> list[str]:
        row = await self.get_user_row(guild_id, user_id)
        return json.loads(row["notes_json"])

    async def set_notes(self, guild_id: int, user_id: int, notes: list[str]) -> None:
        await self.set_user_field(guild_id, user_id, "notes_json", json.dumps(notes))

    async def get_todos(self, guild_id: int, user_id: int) -> list[dict[str, Any]]:
        row = await self.get_user_row(guild_id, user_id)
        return json.loads(row["todos_json"])

    async def set_todos(self, guild_id: int, user_id: int, todos: list[dict[str, Any]]) -> None:
        await self.set_user_field(guild_id, user_id, "todos_json", json.dumps(todos))
