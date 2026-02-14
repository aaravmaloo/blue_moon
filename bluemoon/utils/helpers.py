from __future__ import annotations

import random
import re
import string
from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def parse_duration_to_seconds(duration: str) -> int:
    match = re.fullmatch(r"(\d+)([smhd])", duration.lower().strip())
    if not match:
        raise ValueError("Use format like 30s, 10m, 2h, 3d")
    value = int(match.group(1))
    unit = match.group(2)
    scale = {"s": 1, "m": 60, "h": 3600, "d": 86400}[unit]
    return value * scale


def level_from_xp(xp: int) -> int:
    level = 0
    while xp >= xp_for_level(level + 1):
        level += 1
    return level


def xp_for_level(level: int) -> int:
    return 50 * level * level + 100 * level


def random_password(length: int = 16) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(alphabet) for _ in range(length))


def clean_caps_ratio(text: str) -> float:
    alpha = [c for c in text if c.isalpha()]
    if not alpha:
        return 0.0
    caps = [c for c in alpha if c.isupper()]
    return len(caps) / len(alpha)
