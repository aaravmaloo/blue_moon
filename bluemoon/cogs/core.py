from __future__ import annotations

import asyncio
import json
import random
import re
import time
from collections import defaultdict, deque
from datetime import timedelta

import discord
from discord import app_commands
from discord.ext import commands

from bluemoon.db import now_ts
from bluemoon.utils.constants import PROFANITY_WORDS
from bluemoon.utils.helpers import clean_caps_ratio, level_from_xp, xp_for_level


class CoreCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.spam_tracker: dict[int, dict[int, deque[int]]] = defaultdict(lambda: defaultdict(deque))
        self.join_tracker: dict[int, deque[int]] = defaultdict(deque)
        self.voice_join_ts: dict[tuple[int, int], int] = {}

    async def cog_load(self) -> None:
        print("CoreCog loaded")

    async def _log(self, guild: discord.Guild, title: str, description: str) -> None:
        channel_id = await self.bot.db.get_setting(guild.id, "log_channel_id")
        if not channel_id:
            return
        channel = guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            return
        embed = discord.Embed(title=title, description=description, color=0x5CA1E1)
        embed.timestamp = discord.utils.utcnow()
        await channel.send(embed=embed)

    async def _handle_custom_prefix_command(self, message: discord.Message) -> bool:
        prefix = self.bot.settings.prefix
        if not message.content.startswith(prefix):
            return False
        raw = message.content[len(prefix) :].strip()
        if not raw:
            return False
        name = raw.split(" ")[0].lower()
        row = await self.bot.db.fetchone(
            "SELECT response FROM custom_commands WHERE guild_id = ? AND name = ?",
            (message.guild.id, name),
        )
        if row:
            await message.channel.send(row["response"])
            return True
        return False

    async def _apply_automod(self, message: discord.Message) -> bool:
        guild_id = message.guild.id
        member = message.author
        if isinstance(member, discord.Member) and member.guild_permissions.manage_messages:
            return False

        anti_spam_msgs = int(await self.bot.db.get_setting(guild_id, "anti_spam_msgs") or 6)
        anti_spam_window = int(await self.bot.db.get_setting(guild_id, "anti_spam_window") or 8)
        tracker = self.spam_tracker[guild_id][message.author.id]
        now = now_ts()
        tracker.append(now)
        while tracker and now - tracker[0] > anti_spam_window:
            tracker.popleft()
        if len(tracker) >= anti_spam_msgs:
            await message.delete()
            await message.channel.send(f"{message.author.mention} message blocked: spam detected.", delete_after=5)
            await self._log(message.guild, "AutoMod", f"Spam blocked from {message.author.mention}")
            return True

        text = message.content.lower()
        profanity_on = bool(await self.bot.db.get_setting(guild_id, "profanity_filter"))
        if profanity_on:
            bad_words = PROFANITY_WORDS | await self.bot.db.get_bad_words(guild_id)
            if any(word in text for word in bad_words):
                await message.delete()
                await self._log(message.guild, "AutoMod", f"Bad word blocked from {message.author.mention}")
                return True

        regex_filters = await self.bot.db.get_regex_filters(guild_id)
        for pattern in regex_filters:
            if re.search(pattern, message.content, flags=re.IGNORECASE):
                await message.delete()
                await self._log(message.guild, "AutoMod", f"Regex `{pattern}` blocked from {message.author.mention}")
                return True

        link_filter = bool(await self.bot.db.get_setting(guild_id, "link_filter"))
        if link_filter and re.search(r"https?://", message.content, flags=re.IGNORECASE):
            await message.delete()
            await message.channel.send(f"{message.author.mention} links are blocked here.", delete_after=5)
            return True

        cap_threshold = float(await self.bot.db.get_setting(guild_id, "caps_threshold") or 0.8)
        if len(message.content) >= 12 and clean_caps_ratio(message.content) > cap_threshold:
            await message.delete()
            await message.channel.send(f"{message.author.mention} too many caps.", delete_after=5)
            return True

        return False

    async def _handle_leveling(self, message: discord.Message) -> None:
        rate = float(await self.bot.db.get_setting(message.guild.id, "xp_rate") or 1.0)
        base = random.randint(15, 25)
        gain = int(base * rate)

        user_row = await self.bot.db.get_user_row(message.guild.id, message.author.id)
        new_xp = user_row["xp"] + gain
        new_level = level_from_xp(new_xp)
        await self.bot.db.set_user_field(message.guild.id, message.author.id, "xp", new_xp)

        if new_level > user_row["level"]:
            await self.bot.db.set_user_field(message.guild.id, message.author.id, "level", new_level)
            await message.channel.send(f"{message.author.mention} leveled up to **{new_level}**.")

            role_row = await self.bot.db.fetchone(
                "SELECT role_id FROM level_roles WHERE guild_id = ? AND level = ?",
                (message.guild.id, new_level),
            )
            if role_row and isinstance(message.author, discord.Member):
                role = message.guild.get_role(role_row["role_id"])
                if role:
                    await message.author.add_roles(role, reason="Level role reward")

    async def _handle_auto_responses(self, message: discord.Message) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT * FROM auto_responses WHERE guild_id = ?",
            (message.guild.id,),
        )
        content = message.content.lower()
        for row in rows:
            if row["trigger_text"].lower() in content:
                await message.channel.send(row["response_text"])
                if int(row["open_ticket"]) == 1:
                    category_id = await self.bot.db.get_setting(message.guild.id, "ticket_category_id")
                    category = message.guild.get_channel(int(category_id)) if category_id else None
                    overwrites = {
                        message.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                        message.author: discord.PermissionOverwrite(view_channel=True, send_messages=True),
                    }
                    name = f"ticket-{message.author.name}"[:90]
                    ticket_channel = await message.guild.create_text_channel(
                        name=name,
                        category=category if isinstance(category, discord.CategoryChannel) else None,
                        overwrites=overwrites,
                        reason="Auto-response workflow ticket",
                    )
                    await ticket_channel.send(f"Opened for {message.author.mention} from workflow trigger.")
                break

    async def _handle_auto_thread(self, message: discord.Message) -> None:
        channel_id = await self.bot.db.get_setting(message.guild.id, "auto_thread_channel_id")
        if not channel_id:
            return
        if message.channel.id != int(channel_id):
            return
        if isinstance(message.channel, discord.TextChannel) and not message.has_thread:
            title = (message.content[:40] or f"Thread-{message.author.display_name}").strip()
            await message.create_thread(name=title)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or message.guild is None:
            return

        await self.bot.db.log_event(
            message.guild.id,
            "message_create",
            {"channel_id": message.channel.id, "message_id": message.id},
            actor_id=message.author.id,
        )

        if await self._handle_custom_prefix_command(message):
            return

        blocked = await self._apply_automod(message)
        if blocked:
            return

        await self._handle_leveling(message)
        await self._handle_auto_responses(message)
        await self._handle_auto_thread(message)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        guild_id = member.guild.id
        created_age_hours = (discord.utils.utcnow() - member.created_at).total_seconds() / 3600
        anti_alt_hours = int(await self.bot.db.get_setting(guild_id, "anti_alt_hours") or 24)

        joins = self.join_tracker[guild_id]
        now = now_ts()
        joins.append(now)
        while joins and now - joins[0] > 60:
            joins.popleft()
        join_cap = int(await self.bot.db.get_setting(guild_id, "anti_join_spam_per_min") or 10)

        if len(joins) > join_cap:
            await self._log(member.guild, "Anti-Raid", f"Join spam detected ({len(joins)} in 60s)")

        if created_age_hours < anti_alt_hours and member.guild.me and member.guild.me.guild_permissions.moderate_members:
            timeout_until = discord.utils.utcnow() + timedelta(hours=2)
            try:
                await member.timeout(timeout_until, reason="Anti-alt protection")
                await self._log(member.guild, "Anti-Alt", f"Timed out {member.mention} (new account)")
            except discord.HTTPException:
                pass

        autorole_id = await self.bot.db.get_setting(guild_id, "autorole_id")
        if autorole_id:
            role = member.guild.get_role(int(autorole_id))
            if role:
                try:
                    await member.add_roles(role, reason="Auto role")
                except discord.HTTPException:
                    pass

        welcome_channel_id = await self.bot.db.get_setting(guild_id, "welcome_channel_id")
        if welcome_channel_id:
            channel = member.guild.get_channel(int(welcome_channel_id))
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"Welcome {member.mention} to **{member.guild.name}**.")

        await self.bot.db.log_event(guild_id, "member_join", {"member_id": member.id}, actor_id=member.id)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        goodbye_channel_id = await self.bot.db.get_setting(member.guild.id, "goodbye_channel_id")
        if goodbye_channel_id:
            channel = member.guild.get_channel(int(goodbye_channel_id))
            if isinstance(channel, discord.TextChannel):
                await channel.send(f"Goodbye **{member.display_name}**.")
        await self.bot.db.log_event(member.guild.id, "member_leave", {"member_id": member.id}, actor_id=member.id)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        if message.guild is None or message.author.bot:
            return
        await self._log(
            message.guild,
            "Message Deleted",
            f"Author: {message.author.mention}\nChannel: {message.channel.mention}\nContent: {message.content[:900] or '[empty]'}",
        )
        await self.bot.db.log_event(
            message.guild.id,
            "message_delete",
            {"channel_id": message.channel.id, "author_id": message.author.id},
            actor_id=message.author.id,
        )

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message) -> None:
        if before.guild is None or before.author.bot:
            return
        if before.content == after.content:
            return
        await self._log(
            before.guild,
            "Message Edited",
            f"Author: {before.author.mention}\nBefore: {before.content[:400] or '[empty]'}\nAfter: {after.content[:400] or '[empty]'}",
        )

    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        if before.permissions != after.permissions or before.name != after.name:
            await self._log(before.guild, "Role Updated", f"`{before.name}` changed")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        key = (member.guild.id, member.id)
        if before.channel is None and after.channel is not None:
            self.voice_join_ts[key] = now_ts()
        elif before.channel is not None and after.channel is None:
            start = self.voice_join_ts.pop(key, None)
            if start:
                seconds = max(0, now_ts() - start)
                row = await self.bot.db.get_user_row(member.guild.id, member.id)
                total = row["voice_seconds"] + seconds
                await self.bot.db.set_user_field(member.guild.id, member.id, "voice_seconds", total)
                rate = float(await self.bot.db.get_setting(member.guild.id, "xp_voice_rate") or 1.0)
                xp_gain = int((seconds / 60.0) * 5 * rate)
                if xp_gain > 0:
                    new_xp = row["xp"] + xp_gain
                    await self.bot.db.set_user_field(member.guild.id, member.id, "xp", new_xp)
                    level = level_from_xp(new_xp)
                    if level > row["level"]:
                        await self.bot.db.set_user_field(member.guild.id, member.id, "level", level)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CoreCog(bot))
