from __future__ import annotations

import hashlib
import json
from typing import Optional

import aiohttp
import discord
import feedparser
from discord import app_commands
from discord.ext import commands, tasks


def normalize_source(feed_type: str, source: str) -> str:
    source = source.strip()
    if feed_type == "github":
        if source.startswith("http"):
            return source
        return f"https://github.com/{source}/releases.atom"
    if feed_type == "youtube":
        if source.startswith("http"):
            return source
        return f"https://www.youtube.com/feeds/videos.xml?channel_id={source}"
    if feed_type == "reddit":
        if source.startswith("http"):
            return source
        return f"https://www.reddit.com/r/{source}/new/.rss"
    return source


class IntegrationsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.feed_poller.start()

    def cog_unload(self) -> None:
        self.feed_poller.cancel()

    integrations = app_commands.Group(name="integrations", description="External integrations")

    @integrations.command(name="add-feed", description="Add feed integration")
    async def add_feed(
        self,
        interaction: discord.Interaction,
        feed_type: str,
        source: str,
        channel: discord.TextChannel,
    ) -> None:
        if not interaction.user.guild_permissions.manage_webhooks:
            await interaction.response.send_message("Manage Webhooks required.", ephemeral=True)
            return

        feed_type = feed_type.lower().strip()
        allowed = {"rss", "github", "youtube", "reddit", "twitter", "twitch", "calendar", "trello", "notion"}
        if feed_type not in allowed:
            await interaction.response.send_message(f"feed_type must be one of: {', '.join(sorted(allowed))}", ephemeral=True)
            return

        normalized = normalize_source(feed_type, source)
        await self.bot.db.execute(
            "INSERT INTO integration_feeds (guild_id, feed_type, source, channel_id, last_item_id) VALUES (?, ?, ?, ?, NULL)",
            (interaction.guild_id, feed_type, normalized, channel.id),
        )
        await interaction.response.send_message(f"Added {feed_type} integration -> {channel.mention}")

    @integrations.command(name="remove-feed", description="Remove feed by id")
    async def remove_feed(self, interaction: discord.Interaction, feed_id: int) -> None:
        if not interaction.user.guild_permissions.manage_webhooks:
            await interaction.response.send_message("Manage Webhooks required.", ephemeral=True)
            return
        await self.bot.db.execute("DELETE FROM integration_feeds WHERE id = ? AND guild_id = ?", (feed_id, interaction.guild_id))
        await interaction.response.send_message("Feed removed.")

    @integrations.command(name="list-feeds", description="List configured integrations")
    async def list_feeds(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT id, feed_type, source, channel_id FROM integration_feeds WHERE guild_id = ? ORDER BY id DESC",
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("No integrations configured.")
            return
        lines = [f"{r['id']}. [{r['feed_type']}] {r['source']} -> <#{r['channel_id']}>" for r in rows[:30]]
        await interaction.response.send_message("\n".join(lines))

    @integrations.command(name="webhook-test", description="Test external webhook URL")
    async def webhook_test(self, interaction: discord.Interaction, webhook_url: str, message: str) -> None:
        if not interaction.user.guild_permissions.manage_webhooks:
            await interaction.response.send_message("Manage Webhooks required.", ephemeral=True)
            return
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json={"content": message[:1800]}, timeout=20) as resp:
                code = resp.status
        await interaction.response.send_message(f"Webhook called: status={code}")

    async def _fetch_feed_entry(self, source: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        async with aiohttp.ClientSession() as session:
            async with session.get(source, timeout=20, headers={"User-Agent": "BlueMoonBot/1.0"}) as resp:
                if resp.status != 200:
                    return None, None, None
                text = await resp.text()

        parsed = feedparser.parse(text)
        if parsed.entries:
            entry = parsed.entries[0]
            item_id = entry.get("id") or entry.get("link") or hashlib.sha256(str(entry).encode()).hexdigest()
            title = entry.get("title", "New update")
            link = entry.get("link", source)
            return item_id, title, link

        digest = hashlib.sha256(text.encode()).hexdigest()
        return digest, "Source changed", source

    @tasks.loop(minutes=5)
    async def feed_poller(self) -> None:
        await self.bot.wait_until_ready()
        rows = await self.bot.db.fetchall("SELECT * FROM integration_feeds")
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if not guild:
                continue
            channel = guild.get_channel(row["channel_id"])
            if not isinstance(channel, discord.TextChannel):
                continue
            item_id, title, link = await self._fetch_feed_entry(row["source"])
            if not item_id:
                continue
            if row["last_item_id"] == item_id:
                continue
            await self.bot.db.execute(
                "UPDATE integration_feeds SET last_item_id = ? WHERE id = ?",
                (item_id, row["id"]),
            )
            embed = discord.Embed(title=f"{row['feed_type'].upper()} update", description=title[:400], color=0x0084FF)
            embed.url = link
            await channel.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    cog = IntegrationsCog(bot)
    await bot.add_cog(cog)
