from __future__ import annotations

import asyncio
import importlib
import pkgutil

import discord
from discord.ext import commands

from .config import Settings
from .db import Database
from . import cogs as cogs_pkg


class BlueMoonBot(commands.Bot):
    def __init__(self, settings: Settings) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        intents.voice_states = True
        intents.guilds = True
        intents.messages = True

        super().__init__(
            command_prefix=settings.prefix,
            intents=intents,
            help_command=None,
            activity=discord.Activity(type=discord.ActivityType.watching, name="the blue moon"),
        )
        self.settings = settings
        self.db = Database(settings.database_path)

    async def setup_hook(self) -> None:
        await self.db.connect()

        for module in pkgutil.iter_modules(cogs_pkg.__path__):
            if module.name.startswith("_"):
                continue
            await self.load_extension(f"bluemoon.cogs.{module.name}")

        if self.settings.guild_id:
            guild_obj = discord.Object(id=self.settings.guild_id)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        print(f"Logged in as {self.user} ({self.user.id if self.user else 'n/a'})")


def run_bot(settings: Settings) -> None:
    bot = BlueMoonBot(settings)
    bot.run(settings.token)
