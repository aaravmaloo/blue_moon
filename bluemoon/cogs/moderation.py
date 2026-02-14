from __future__ import annotations

import asyncio
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bluemoon.utils.helpers import parse_duration_to_seconds


class ModerationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _is_staff(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        if interaction.user.guild_permissions.manage_guild:
            return True
        staff_role_id = await self.bot.db.get_setting(interaction.guild_id, "staff_role_id")
        if not staff_role_id:
            return False
        return any(role.id == int(staff_role_id) for role in interaction.user.roles)

    async def _require_staff(self, interaction: discord.Interaction) -> bool:
        if await self._is_staff(interaction):
            return True
        await interaction.response.send_message("Staff permissions required.", ephemeral=True)
        return False

    mod = app_commands.Group(name="mod", description="Moderation and security")

    @mod.command(name="set-log-channel", description="Set moderation log channel")
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.set_setting(interaction.guild_id, "log_channel_id", channel.id)
        await interaction.response.send_message(f"Log channel set to {channel.mention}.")

    @mod.command(name="set-staff-role", description="Set role considered as staff")
    async def set_staff_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Administrator permission required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "staff_role_id", role.id)
        await interaction.response.send_message(f"Staff role set to {role.mention}.")

    @mod.command(name="automod", description="Configure automod")
    @app_commands.describe(
        profanity="Enable profanity filter",
        links="Enable link filter",
        caps_threshold="Caps ratio threshold (0.1-1.0)",
        spam_msgs="Messages allowed in spam window",
        spam_window="Spam window seconds",
    )
    async def automod(
        self,
        interaction: discord.Interaction,
        profanity: bool | None = None,
        links: bool | None = None,
        caps_threshold: float | None = None,
        spam_msgs: int | None = None,
        spam_window: int | None = None,
    ) -> None:
        if not await self._require_staff(interaction):
            return
        updates: list[str] = []
        if profanity is not None:
            await self.bot.db.set_setting(interaction.guild_id, "profanity_filter", profanity)
            updates.append(f"profanity={profanity}")
        if links is not None:
            await self.bot.db.set_setting(interaction.guild_id, "link_filter", links)
            updates.append(f"links={links}")
        if caps_threshold is not None:
            await self.bot.db.set_setting(interaction.guild_id, "caps_threshold", max(0.1, min(1.0, caps_threshold)))
            updates.append(f"caps_threshold={caps_threshold:.2f}")
        if spam_msgs is not None:
            await self.bot.db.set_setting(interaction.guild_id, "anti_spam_msgs", max(2, spam_msgs))
            updates.append(f"spam_msgs={spam_msgs}")
        if spam_window is not None:
            await self.bot.db.set_setting(interaction.guild_id, "anti_spam_window", max(2, spam_window))
            updates.append(f"spam_window={spam_window}")

        if updates:
            await interaction.response.send_message("Updated: " + ", ".join(updates))
        else:
            await interaction.response.send_message("No values provided.", ephemeral=True)

    @mod.command(name="security", description="Configure anti-alt and anti-join spam")
    async def security(self, interaction: discord.Interaction, anti_alt_hours: int, join_spam_per_min: int) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.set_setting(interaction.guild_id, "anti_alt_hours", max(0, anti_alt_hours))
        await self.bot.db.set_setting(interaction.guild_id, "anti_join_spam_per_min", max(2, join_spam_per_min))
        await interaction.response.send_message("Security settings updated.")

    @mod.command(name="add-badword", description="Add custom blocked word")
    async def add_badword(self, interaction: discord.Interaction, word: str) -> None:
        if not await self._require_staff(interaction):
            return
        word = word.lower().strip()
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO bad_words (guild_id, word) VALUES (?, ?)",
            (interaction.guild_id, word),
        )
        await interaction.response.send_message(f"Added bad word: `{word}`")

    @mod.command(name="remove-badword", description="Remove blocked word")
    async def remove_badword(self, interaction: discord.Interaction, word: str) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.execute(
            "DELETE FROM bad_words WHERE guild_id = ? AND word = ?",
            (interaction.guild_id, word.lower().strip()),
        )
        await interaction.response.send_message("Removed bad word filter.")

    @mod.command(name="add-regex", description="Add regex content filter")
    async def add_regex(self, interaction: discord.Interaction, pattern: str) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO regex_filters (guild_id, pattern) VALUES (?, ?)",
            (interaction.guild_id, pattern),
        )
        await interaction.response.send_message(f"Added regex filter: `{pattern}`")

    @mod.command(name="warn", description="Warn a user")
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
        await interaction.response.send_message(f"Warned {member.mention}: {reason}")

    @mod.command(name="warnings", description="List user warnings")
    async def warnings(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if not await self._require_staff(interaction):
            return
        rows = await self.bot.db.get_warnings(interaction.guild_id, member.id)
        if not rows:
            await interaction.response.send_message("No warnings found.")
            return
        lines = [f"#{r['id']} <t:{r['created_at']}:R> - {r['reason']}" for r in rows[:10]]
        await interaction.response.send_message("\n".join(lines))

    @mod.command(name="timeout", description="Timeout member for duration like 10m")
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason") -> None:
        if not await self._require_staff(interaction):
            return
        try:
            seconds = parse_duration_to_seconds(duration)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        await member.timeout(until, reason=reason)
        await interaction.response.send_message(f"Timed out {member.mention} for {duration}.")

    @mod.command(name="kick", description="Kick member")
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason") -> None:
        if not await self._require_staff(interaction):
            return
        await member.kick(reason=reason)
        await interaction.response.send_message(f"Kicked {member.mention}.")

    @mod.command(name="ban", description="Ban member")
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason") -> None:
        if not await self._require_staff(interaction):
            return
        await interaction.guild.ban(member, reason=reason, delete_message_days=1)
        await interaction.response.send_message(f"Banned {member.mention}.")

    @mod.command(name="tempban", description="Tempban member")
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason") -> None:
        if not await self._require_staff(interaction):
            return
        try:
            seconds = parse_duration_to_seconds(duration)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        await interaction.guild.ban(member, reason=f"Tempban: {reason}", delete_message_days=1)
        await interaction.response.send_message(f"Tempbanned {member.mention} for {duration}.")

        async def unban_later() -> None:
            await asyncio.sleep(seconds)
            user = await self.bot.fetch_user(member.id)
            try:
                await interaction.guild.unban(user, reason="Tempban expired")
            except discord.HTTPException:
                pass

        self.bot.loop.create_task(unban_later())

    @mod.command(name="softban", description="Softban member (ban then unban)")
    async def softban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason") -> None:
        if not await self._require_staff(interaction):
            return
        await interaction.guild.ban(member, reason=reason, delete_message_days=1)
        user = await self.bot.fetch_user(member.id)
        await interaction.guild.unban(user, reason="Softban release")
        await interaction.response.send_message(f"Softbanned {member.mention}.")

    @mod.command(name="lock", description="Lock a channel")
    async def lock(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        if not await self._require_staff(interaction):
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Target must be a text channel.", ephemeral=True)
            return
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"Locked {target.mention}.")

    @mod.command(name="unlock", description="Unlock a channel")
    async def unlock(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        if not await self._require_staff(interaction):
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Target must be a text channel.", ephemeral=True)
            return
        overwrite = target.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await target.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        await interaction.response.send_message(f"Unlocked {target.mention}.")

    @mod.command(name="appeal-channel", description="Set channel for ban appeal messages")
    async def appeal_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.set_setting(interaction.guild_id, "appeal_channel_id", channel.id)
        await interaction.response.send_message(f"Appeal channel set to {channel.mention}.")

    @mod.command(name="appeal", description="Submit an appeal")
    async def appeal(self, interaction: discord.Interaction, message: str) -> None:
        channel_id = await self.bot.db.get_setting(interaction.guild_id, "appeal_channel_id")
        if not channel_id:
            await interaction.response.send_message("Appeal channel is not configured.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Appeal channel unavailable.", ephemeral=True)
            return
        embed = discord.Embed(title="New Appeal", description=message, color=0x6B8E23)
        embed.add_field(name="User", value=f"{interaction.user} ({interaction.user.id})")
        await channel.send(embed=embed)
        await interaction.response.send_message("Appeal submitted.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    cog = ModerationCog(bot)
    await bot.add_cog(cog)
