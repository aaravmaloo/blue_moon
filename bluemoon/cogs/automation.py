from __future__ import annotations

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands


class AutomationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    automation = app_commands.Group(name="automation", description="Custom commands and automation")

    @automation.command(name="custom-add", description="Add custom prefix command")
    async def custom_add(self, interaction: discord.Interaction, name: str, response: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild required.", ephemeral=True)
            return
        clean = name.lower().strip().replace(" ", "-")
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO custom_commands (guild_id, name, response) VALUES (?, ?, ?)",
            (interaction.guild_id, clean, response[:1900]),
        )
        await interaction.response.send_message(f"Custom command saved: `{self.bot.settings.prefix}{clean}`")

    @automation.command(name="custom-remove", description="Remove custom prefix command")
    async def custom_remove(self, interaction: discord.Interaction, name: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild required.", ephemeral=True)
            return
        await self.bot.db.execute(
            "DELETE FROM custom_commands WHERE guild_id = ? AND name = ?",
            (interaction.guild_id, name.lower().strip()),
        )
        await interaction.response.send_message("Custom command removed.")

    @automation.command(name="custom-list", description="List custom commands")
    async def custom_list(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT name FROM custom_commands WHERE guild_id = ? ORDER BY name ASC",
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("No custom commands configured.")
            return
        names = ", ".join([f"`{self.bot.settings.prefix}{r['name']}`" for r in rows[:50]])
        await interaction.response.send_message(names)

    @automation.command(name="trigger-add", description="Add trigger auto-response rule")
    async def trigger_add(
        self,
        interaction: discord.Interaction,
        trigger_text: str,
        response_text: str,
        open_ticket: bool = False,
    ) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Manage Messages required.", ephemeral=True)
            return
        await self.bot.db.execute(
            "INSERT INTO auto_responses (guild_id, trigger_text, response_text, open_ticket) VALUES (?, ?, ?, ?)",
            (interaction.guild_id, trigger_text[:100], response_text[:1800], 1 if open_ticket else 0),
        )
        await interaction.response.send_message("Trigger rule added.")

    @automation.command(name="trigger-remove", description="Remove trigger by id")
    async def trigger_remove(self, interaction: discord.Interaction, rule_id: int) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Manage Messages required.", ephemeral=True)
            return
        await self.bot.db.execute(
            "DELETE FROM auto_responses WHERE id = ? AND guild_id = ?",
            (rule_id, interaction.guild_id),
        )
        await interaction.response.send_message("Trigger rule removed.")

    @automation.command(name="trigger-list", description="List trigger rules")
    async def trigger_list(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetchall(
            "SELECT id, trigger_text, open_ticket FROM auto_responses WHERE guild_id = ? ORDER BY id DESC LIMIT 30",
            (interaction.guild_id,),
        )
        if not rows:
            await interaction.response.send_message("No trigger rules.")
            return
        lines = [f"{r['id']}. trigger=`{r['trigger_text']}` ticket={bool(r['open_ticket'])}" for r in rows]
        await interaction.response.send_message("\n".join(lines))

    @automation.command(name="workflow-example", description="Create sample workflow: help -> guide + ticket")
    async def workflow_example(self, interaction: discord.Interaction) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Manage Messages required.", ephemeral=True)
            return
        await self.bot.db.execute(
            "INSERT INTO auto_responses (guild_id, trigger_text, response_text, open_ticket) VALUES (?, ?, ?, 1)",
            (interaction.guild_id, "help", "Need help? A support ticket is being opened for you.",),
        )
        await interaction.response.send_message("Workflow rule created.")

    @automation.command(name="webhook-send", description="Send payload to external webhook URL")
    async def webhook_send(self, interaction: discord.Interaction, webhook_url: str, content: str) -> None:
        if not interaction.user.guild_permissions.manage_webhooks:
            await interaction.response.send_message("Manage Webhooks required.", ephemeral=True)
            return
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json={"content": content[:1500]}, timeout=20) as resp:
                status = resp.status
        await interaction.response.send_message(f"Webhook dispatched (status={status}).")


async def setup(bot: commands.Bot) -> None:
    cog = AutomationCog(bot)
    await bot.add_cog(cog)
