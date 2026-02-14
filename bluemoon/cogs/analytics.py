from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

import discord
from discord import app_commands
from discord.ext import commands


class AnalyticsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    analytics = app_commands.Group(name="analytics", description="Logging and analytics")

    @analytics.command(name="growth", description="Server join/leave trend for last 14 days")
    async def growth(self, interaction: discord.Interaction) -> None:
        since = int((discord.utils.utcnow() - timedelta(days=14)).timestamp())
        rows = await self.bot.db.fetchall(
            "SELECT event_type, created_at FROM analytics_events WHERE guild_id = ? AND created_at >= ? AND event_type IN ('member_join','member_leave')",
            (interaction.guild_id, since),
        )
        joined = Counter()
        left = Counter()
        for row in rows:
            day = datetime.fromtimestamp(row["created_at"], tz=timezone.utc).strftime("%Y-%m-%d")
            if row["event_type"] == "member_join":
                joined[day] += 1
            else:
                left[day] += 1
        days = [(discord.utils.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(13, -1, -1)]
        lines = ["Date | Joins | Leaves"]
        for d in days:
            lines.append(f"{d} | {joined[d]} | {left[d]}")
        await interaction.response.send_message("```\n" + "\n".join(lines)[:1900] + "\n```")

    @analytics.command(name="heatmap", description="Message activity heatmap by hour (last 7 days)")
    async def heatmap(self, interaction: discord.Interaction) -> None:
        since = int((discord.utils.utcnow() - timedelta(days=7)).timestamp())
        rows = await self.bot.db.fetchall(
            "SELECT created_at FROM analytics_events WHERE guild_id = ? AND created_at >= ? AND event_type = 'message_create'",
            (interaction.guild_id, since),
        )
        bins = Counter()
        for row in rows:
            hour = datetime.fromtimestamp(row["created_at"], tz=timezone.utc).hour
            bins[hour] += 1
        max_val = max(bins.values(), default=1)
        lines = ["Hour | Activity"]
        for hour in range(24):
            count = bins[hour]
            blocks = int((count / max_val) * 20) if max_val else 0
            lines.append(f"{hour:02d}:00 | {'#' * blocks} ({count})")
        await interaction.response.send_message("```\n" + "\n".join(lines)[:1900] + "\n```")

    @analytics.command(name="staff", description="Staff performance stats")
    async def staff(self, interaction: discord.Interaction) -> None:
        warn_rows = await self.bot.db.fetchall(
            "SELECT moderator_id, COUNT(*) AS c FROM warnings WHERE guild_id = ? GROUP BY moderator_id ORDER BY c DESC LIMIT 20",
            (interaction.guild_id,),
        )
        ticket_rows = await self.bot.db.fetchall(
            "SELECT assigned_staff_id, COUNT(*) AS c FROM tickets WHERE guild_id = ? AND assigned_staff_id IS NOT NULL GROUP BY assigned_staff_id ORDER BY c DESC LIMIT 20",
            (interaction.guild_id,),
        )
        ticket_map = {r["assigned_staff_id"]: r["c"] for r in ticket_rows}
        lines = ["Staff | Warnings | Tickets"]
        for row in warn_rows:
            member = interaction.guild.get_member(row["moderator_id"])
            name = member.display_name if member else str(row["moderator_id"])
            lines.append(f"{name} | {row['c']} | {ticket_map.get(row['moderator_id'], 0)}")
        if len(lines) == 1:
            lines.append("No staff activity yet.")
        await interaction.response.send_message("```\n" + "\n".join(lines)[:1900] + "\n```")

    @analytics.command(name="logs", description="Recent moderation/log events")
    async def logs(self, interaction: discord.Interaction, event_type: str = "message_delete") -> None:
        rows = await self.bot.db.fetchall(
            "SELECT actor_id, payload, created_at FROM analytics_events WHERE guild_id = ? AND event_type = ? ORDER BY id DESC LIMIT 15",
            (interaction.guild_id, event_type),
        )
        if not rows:
            await interaction.response.send_message("No records found.")
            return
        lines = []
        for row in rows:
            actor = f"<@{row['actor_id']}>" if row["actor_id"] else "n/a"
            ts = f"<t:{row['created_at']}:R>"
            payload = json.loads(row["payload"])
            lines.append(f"{ts} by {actor}: {payload}")
        await interaction.response.send_message("\n".join(lines)[:1900])


async def setup(bot: commands.Bot) -> None:
    cog = AnalyticsCog(bot)
    await bot.add_cog(cog)
