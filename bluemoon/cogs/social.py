from __future__ import annotations

import random
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks


class SocialCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.birthday_loop.start()

    def cog_unload(self) -> None:
        self.birthday_loop.cancel()

    social = app_commands.Group(name="social", description="Social and community tools")

    @social.command(name="profile", description="View user profile")
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        row = await self.bot.db.get_user_row(interaction.guild_id, target.id)
        embed = discord.Embed(title=f"Profile: {target.display_name}", color=0x4DA6FF)
        embed.add_field(name="Reputation", value=str(row["reputation"]))
        embed.add_field(name="Thanks", value=str(row["thanks_count"]))
        embed.add_field(name="Level", value=str(row["level"]))
        embed.add_field(name="Birthday", value=row["birthday"] or "Not set", inline=False)
        await interaction.response.send_message(embed=embed)

    @social.command(name="rep", description="Give reputation point")
    async def rep(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if member.bot or member.id == interaction.user.id:
            await interaction.response.send_message("Invalid target.", ephemeral=True)
            return
        row = await self.bot.db.get_user_row(interaction.guild_id, member.id)
        await self.bot.db.set_user_field(interaction.guild_id, member.id, "reputation", row["reputation"] + 1)
        await interaction.response.send_message(f"+1 reputation to {member.mention}")

    @social.command(name="thanks", description="Thank someone")
    async def thanks(self, interaction: discord.Interaction, member: discord.Member) -> None:
        if member.bot or member.id == interaction.user.id:
            await interaction.response.send_message("Invalid target.", ephemeral=True)
            return
        row = await self.bot.db.get_user_row(interaction.guild_id, member.id)
        await self.bot.db.set_user_field(interaction.guild_id, member.id, "thanks_count", row["thanks_count"] + 1)
        await interaction.response.send_message(f"{interaction.user.mention} thanked {member.mention}")

    @social.command(name="birthday-set", description="Set birthday as YYYY-MM-DD")
    async def birthday_set(self, interaction: discord.Interaction, date_iso: str) -> None:
        try:
            year, month, day = [int(v) for v in date_iso.split("-")]
            assert 1 <= month <= 12
            assert 1 <= day <= 31
            assert 1900 <= year <= 2100
        except Exception:
            await interaction.response.send_message("Invalid date format. Use YYYY-MM-DD", ephemeral=True)
            return
        await self.bot.db.set_user_field(interaction.guild_id, interaction.user.id, "birthday", date_iso)
        await interaction.response.send_message("Birthday saved.")

    @social.command(name="birthdays", description="List upcoming birthdays")
    async def birthdays(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT user_id, birthday FROM user_state WHERE guild_id = ? AND birthday IS NOT NULL ORDER BY birthday ASC",
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("No birthdays saved.")
            return
        lines = []
        for row in rows[:20]:
            member = interaction.guild.get_member(row["user_id"])
            name = member.display_name if member else str(row["user_id"])
            lines.append(f"{name}: {row['birthday']}")
        await interaction.response.send_message("\n".join(lines))

    @social.command(name="set-confession-channel", description="Set anonymous confession channel")
    async def set_confession_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "confession_channel_id", channel.id)
        await interaction.response.send_message(f"Confession channel set to {channel.mention}")

    @social.command(name="confess", description="Post anonymous confession")
    async def confess(self, interaction: discord.Interaction, text: str) -> None:
        channel_id = await self.bot.db.get_setting(interaction.guild_id, "confession_channel_id")
        if not channel_id:
            await interaction.response.send_message("Confession channel is not configured.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Confession channel missing.", ephemeral=True)
            return
        embed = discord.Embed(title="Anonymous Confession", description=text[:1800], color=0x223344)
        await channel.send(embed=embed)
        await interaction.response.send_message("Confession posted anonymously.", ephemeral=True)

    @social.command(name="set-anon-channel", description="Set anonymous post channel")
    async def set_anon_channel(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "anonymous_channel_id", channel.id)
        await interaction.response.send_message(f"Anonymous post channel set to {channel.mention}")

    @social.command(name="anon-post", description="Post anonymous message")
    async def anon_post(self, interaction: discord.Interaction, text: str) -> None:
        channel_id = await self.bot.db.get_setting(interaction.guild_id, "anonymous_channel_id")
        if not channel_id:
            await interaction.response.send_message("Anonymous channel is not configured.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(channel_id))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Anonymous channel missing.", ephemeral=True)
            return
        await channel.send(f"Anonymous: {text[:1800]}")
        await interaction.response.send_message("Anonymous post sent.", ephemeral=True)

    @social.command(name="matchmake", description="Random matchmaker")
    async def matchmake(self, interaction: discord.Interaction) -> None:
        members = [m for m in interaction.guild.members if not m.bot]
        if len(members) < 2:
            await interaction.response.send_message("Need at least two human members.")
            return
        a, b = random.sample(members, 2)
        await interaction.response.send_message(f"Matchmaker picked: {a.mention} + {b.mention}")

    @social.command(name="quote-add", description="Save a quote")
    async def quote_add(self, interaction: discord.Interaction, quote_text: str) -> None:
        await self.bot.db.execute(
            "INSERT INTO quotes (guild_id, author_id, quote_text, created_at) VALUES (?, ?, ?, ?)",
            (interaction.guild_id, interaction.user.id, quote_text[:500], int(time.time())),
        )
        await interaction.response.send_message("Quote saved.")

    @social.command(name="quote-random", description="Get random quote")
    async def quote_random(self, interaction: discord.Interaction) -> None:
        row = await self.bot.db.fetchone(
            "SELECT quote_text, author_id FROM quotes WHERE guild_id = ? ORDER BY RANDOM() LIMIT 1",
            (interaction.guild_id,),
        )
        if not row:
            await interaction.response.send_message("No quotes saved.")
            return
        member = interaction.guild.get_member(row["author_id"])
        name = member.display_name if member else str(row["author_id"])
        await interaction.response.send_message(f"\"{row['quote_text']}\" - {name}")

    @tasks.loop(hours=12)
    async def birthday_loop(self) -> None:
        await self.bot.wait_until_ready()
        today = discord.utils.utcnow().strftime("%m-%d")
        for guild in self.bot.guilds:
            rows = await self.bot.db.fetchall(
                "SELECT user_id, birthday FROM user_state WHERE guild_id = ? AND birthday IS NOT NULL",
                (guild.id,),
            )
            if not rows:
                continue
            welcome_id = await self.bot.db.get_setting(guild.id, "welcome_channel_id")
            channel = guild.get_channel(int(welcome_id)) if welcome_id else None
            if not isinstance(channel, discord.TextChannel):
                continue
            for row in rows:
                if row["birthday"][5:] == today:
                    await channel.send(f"Happy birthday <@{row['user_id']}>.")


async def setup(bot: commands.Bot) -> None:
    cog = SocialCog(bot)
    await bot.add_cog(cog)
