from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bluemoon.utils.helpers import level_from_xp, xp_for_level


class LevelingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    level = app_commands.Group(name="level", description="Leveling and XP")

    @level.command(name="rank", description="Show rank card")
    async def rank(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        row = await self.bot.db.get_user_row(interaction.guild_id, target.id)
        next_xp = xp_for_level(row["level"] + 1)
        current_level_floor = xp_for_level(row["level"])
        progress = row["xp"] - current_level_floor
        need = max(1, next_xp - current_level_floor)
        bars = int((progress / need) * 20)
        bar = "#" * bars + "-" * (20 - bars)
        await interaction.response.send_message(
            f"Rank for {target.mention}\n"
            f"Level: **{row['level']}**\n"
            f"XP: **{row['xp']}** ({progress}/{need})\n"
            f"Voice Time: **{row['voice_seconds']//60} min**\n"
            f"`[{bar}]`"
        )

    @level.command(name="leaderboard", description="XP leaderboard")
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT user_id, xp, level FROM user_state WHERE guild_id = ? ORDER BY xp DESC LIMIT 10",
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("No leaderboard data yet.")
            return
        lines = []
        for i, row in enumerate(rows, start=1):
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else f"User {row['user_id']}"
            lines.append(f"{i}. {name} - L{row['level']} ({row['xp']} XP)")
        await interaction.response.send_message("\n".join(lines))

    @level.command(name="set-xp-rate", description="Set custom XP rates")
    async def set_xp_rate(self, interaction: discord.Interaction, message_rate: float, voice_rate: float) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild permission required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "xp_rate", max(0.1, min(5.0, message_rate)))
        await self.bot.db.set_setting(interaction.guild_id, "xp_voice_rate", max(0.1, min(5.0, voice_rate)))
        await interaction.response.send_message("XP rates updated.")

    @level.command(name="set-role-reward", description="Set role reward at a level")
    async def set_role_reward(self, interaction: discord.Interaction, level: int, role: discord.Role) -> None:
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("Manage Roles required.", ephemeral=True)
            return
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO level_roles (guild_id, level, role_id) VALUES (?, ?, ?)",
            (interaction.guild_id, max(1, level), role.id),
        )
        await interaction.response.send_message(f"Role reward set: level {level} -> {role.mention}")


async def setup(bot: commands.Bot) -> None:
    cog = LevelingCog(bot)
    await bot.add_cog(cog)
