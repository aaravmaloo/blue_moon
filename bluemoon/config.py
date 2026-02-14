from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    token: str
    client_id: int
    guild_id: int | None
    prefix: str
    database_path: str
    timezone: str


def load_settings() -> Settings:
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip()
    client_id = os.getenv("DISCORD_CLIENT_ID", "").strip()
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN is required")
    if not client_id.isdigit():
        raise RuntimeError("DISCORD_CLIENT_ID must be set to a numeric value")

    guild_raw = os.getenv("DISCORD_GUILD_ID", "").strip()
    guild_id = int(guild_raw) if guild_raw.isdigit() else None

    return Settings(
        token=token,
        client_id=int(client_id),
        guild_id=guild_id,
        prefix=os.getenv("BOT_PREFIX", "!").strip() or "!",
        database_path=os.getenv("DATABASE_PATH", "data/bluemoon.sqlite3").strip(),
        timezone=os.getenv("DEFAULT_TIMEZONE", "UTC").strip() or "UTC",
    )
