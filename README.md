# Blue Moon

All-in-one Discord bot in Python (`discord.py`) with modular cogs and local SQLite persistence.

This repository is Python-only and stores runtime data in `data/bluemoon.sqlite3` by default.

## Table Of Contents

1. Overview
2. Architecture
3. Feature Coverage
4. Requirements
5. Setup
6. Add The Bot To Your Server
7. Configuration
8. Data Storage
9. Command Reference
10. Running And Operations
11. Troubleshooting
12. Security Notes
13. Project Structure

## Overview

Blue Moon is designed as a single bot that combines moderation, server management, economy, leveling, music, tickets, automation, analytics, social tools, and external feed integrations.

The current implementation is a strong foundation with many working modules and some intentionally simple/stubbed subsystems for later extension.

## Architecture

- Runtime: `discord.py` app commands (slash commands) + event listeners.
- Storage: local SQLite via `aiosqlite`.
- Bot core:
  - `bot.py`: entry point
  - `bluemoon/bot.py`: bot class, cog loading, command sync
  - `bluemoon/config.py`: environment configuration
  - `bluemoon/db.py`: schema and data access
- Features are separated by cogs in `bluemoon/cogs/`.

## Feature Coverage

Status meaning:
- `Implemented`: usable now
- `Baseline`: implemented with simpler logic (extendable)
- `Planned`: not fully implemented yet

### 1) Moderation & Security

- Implemented: spam/link/caps/profanity filtering, bad-word/regex filters, warnings, timeout/kick/ban/tempban/softban, lock/unlock, mod logs, appeal channel.
- Baseline: anti-alt and anti-join-spam protections.
- Planned: full anti-nuke heuristics, advanced role-policy engine.

### 2) Server Management

- Implemented: welcome/goodbye, autorole, button/reaction role panels, channel clone, mass role add/remove, backup snapshot + restore channels, auto-thread, server stats channel rename.
- Baseline: template export/import for guild bot settings.

### 3) Economy & Leveling

- Implemented: wallet/bank, daily/weekly/work/crime/rob/gamble, shop, buy/inventory, XP from messages and voice, rank, leaderboard, XP rates, level role rewards.
- Baseline: trading is currently represented by user-to-user payments.

### 4) Music

- Implemented: queue playback, play/pause/resume/skip/loop/volume, 24/7 toggle, DJ role gate, lyrics lookup.
- Notes: YouTube/query playback works through `yt-dlp` + `ffmpeg`.
- Baseline: Spotify links are not directly streamed; use title search or YouTube URLs.

### 5) Fun & Games

- Implemented: trivia, hangman, truth/dare, WYR, guess game, polls, roast/compliment, lightweight RPG, pet/farming mini loop.
- Baseline: chess command is a placeholder integration hook.

### 6) Utility & Productivity

- Implemented: reminders, timers, notes, todos, calculator, unit converter, weather, timezone, translation, QR generation, password generation, scheduled messages.

### 7) Ticket & Support

- Implemented: ticket panel (support/report/appeal), private ticket channels, assign/close, transcripts, SLA warnings, feedback.
- Baseline: auto-close inactivity workflow.

### 8) Logging & Analytics

- Implemented: join/leave logs, edit/delete logs, role update logs, growth chart, activity heatmap, staff stats.
- Baseline: metrics are query-based summaries from event logs.

### 9) Custom Commands & Automation

- Implemented: custom prefix commands, trigger auto-responses, workflow example (`help` trigger opening ticket), webhook sender.

### 10) Social & Community

- Implemented: profiles, reputation, thanks/karma-style counts, birthdays, confessions, anonymous posts, matchmaking, quotes.

### 11) Integrations

- Implemented: feed integrations (RSS/GitHub/YouTube/Reddit-style sources) and webhook testing.
- Baseline: integrations are feed-poll based, not full OAuth app integrations.

## Requirements

- Python 3.11+ (tested in your environment on Python 3.14)
- FFmpeg installed and available on PATH (required for music playback)
- A Discord application and bot token

Dependencies are listed in `requirements.txt`.

## Setup

1. Create virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

2. Create `.env` from `.env.example`:

```bash
copy .env.example .env
```

3. Fill `.env` values:
- `DISCORD_BOT_TOKEN`
- `DISCORD_CLIENT_ID`
- optional `DISCORD_GUILD_ID` (recommended in development for instant slash sync)

4. Start the bot:

```bash
python bot.py
```

If startup is successful, you should see:
- `Logged in as ...`

## Add The Bot To Your Server

If you already have an installation link from Discord Developer Portal, use that link directly.

Manual method (Portal):
1. Open Discord Developer Portal.
2. Select your app -> `Bot` tab:
   - Enable `MESSAGE CONTENT INTENT`
   - Enable `SERVER MEMBERS INTENT`
3. Go to `OAuth2` -> `URL Generator`.
4. Scopes:
   - `bot`
   - `applications.commands`
5. Permissions (recommended minimum for current features):
   - View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
   - Manage Messages
   - Manage Channels
   - Manage Roles
   - Kick Members
   - Ban Members
   - Moderate Members
   - Move Members
   - Connect
   - Speak
6. Open generated URL, choose your server, authorize.
7. Run the bot process locally (`python bot.py`).

## Configuration

Environment variables:

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `DISCORD_BOT_TOKEN` | Yes | - | Bot token used to login |
| `DISCORD_CLIENT_ID` | Yes | - | Application client ID |
| `DISCORD_GUILD_ID` | No | empty | Dev guild for faster slash sync |
| `BOT_PREFIX` | No | `!` | Prefix for custom text commands |
| `DATABASE_PATH` | No | `data/bluemoon.sqlite3` | SQLite DB location |
| `DEFAULT_TIMEZONE` | No | `UTC` | Utility timezone fallback |

## Data Storage

- Local DB path: `data/bluemoon.sqlite3`
- Schema is initialized automatically on startup by `bluemoon/db.py`.
- `data/` is gitignored so server/runtime state stays local.

## Command Reference

Top-level slash groups:

- `/mod` moderation and security
- `/manage` server configuration and maintenance
- `/economy` currency/shop/bank commands
- `/level` rank/leaderboard/xp config
- `/music` playback and queue controls
- `/games` fun and minigames
- `/utility` reminders/tools/productivity
- `/ticket` support system
- `/analytics` reporting and server metrics
- `/automation` custom commands and triggers
- `/social` community/profile tools
- `/integrations` external feed/webhook integrations

Custom prefix commands:
- Managed via `/automation custom-add`
- Triggered with `BOT_PREFIX` (default `!`)

## Running And Operations

### Development Tips

- Set `DISCORD_GUILD_ID` for near-instant slash updates in one server.
- Leave `DISCORD_GUILD_ID` empty for global sync (can take time to propagate).

### Suggested Production Practices

- Run with a process manager (systemd, NSSM, Docker, etc.).
- Add regular SQLite backups of `data/bluemoon.sqlite3`.
- Restrict sensitive commands with staff/admin role policy.
- Rotate tokens immediately if exposed.

## Troubleshooting

### Slash commands do not appear

- Confirm bot invited with `applications.commands` scope.
- Confirm bot process is running and logged in.
- For faster testing, set `DISCORD_GUILD_ID` to your server ID and restart.

### Bot is online but moderation/music actions fail

- Check role hierarchy: bot role must be above target roles.
- Ensure required permissions are granted in server/channel.
- For voice/music, confirm FFmpeg is installed and in PATH.

### Reminders/scheduled tasks not firing

- Verify bot process is continuously running.
- Confirm channel still exists and bot can send messages there.

### Translation/weather/integrations intermittently fail

- External APIs and feeds can rate-limit or timeout.
- Retry later or swap to self-hosted/paid API providers for reliability.

## Security Notes

- Never commit `.env`.
- `DISCORD_BOT_TOKEN` and client secrets must be kept private.
- If any credential was ever posted publicly, rotate it immediately in Developer Portal.

## Project Structure

```text
blue_moon/
  bot.py
  .env.example
  requirements.txt
  README.md
  data/
  bluemoon/
    __init__.py
    bot.py
    config.py
    db.py
    cogs/
      moderation.py
      management.py
      economy.py
      leveling.py
      music.py
      games.py
      utility.py
      tickets.py
      analytics.py
      automation.py
      social.py
      integrations.py
      core.py
    utils/
      helpers.py
      constants.py
```

## License

Add your preferred license file (`LICENSE`) before publishing or sharing publicly.
