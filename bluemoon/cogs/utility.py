from __future__ import annotations

import ast
import io
import math
import operator
import random
import time
from datetime import datetime

import aiohttp
import discord
import segno
from discord import app_commands
from discord.ext import commands, tasks

from bluemoon.utils.helpers import parse_duration_to_seconds, random_password


SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.Mod: operator.mod,
}


def safe_eval(expr: str) -> float:
    def _eval(node: ast.AST) -> float:
        if isinstance(node, ast.Num):
            return float(node.n)
        if isinstance(node, ast.BinOp):
            if type(node.op) not in SAFE_OPS:
                raise ValueError("Unsupported operator")
            return SAFE_OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp):
            if type(node.op) not in SAFE_OPS:
                raise ValueError("Unsupported unary operator")
            return SAFE_OPS[type(node.op)](_eval(node.operand))
        raise ValueError("Unsupported expression")

    parsed = ast.parse(expr, mode="eval")
    return _eval(parsed.body)


def convert_unit(value: float, from_unit: str, to_unit: str) -> float:
    key = (from_unit.lower(), to_unit.lower())
    table = {
        ("km", "mi"): lambda v: v * 0.621371,
        ("mi", "km"): lambda v: v / 0.621371,
        ("c", "f"): lambda v: (v * 9 / 5) + 32,
        ("f", "c"): lambda v: (v - 32) * 5 / 9,
        ("kg", "lb"): lambda v: v * 2.20462,
        ("lb", "kg"): lambda v: v / 2.20462,
        ("m", "ft"): lambda v: v * 3.28084,
        ("ft", "m"): lambda v: v / 3.28084,
    }
    if key not in table:
        raise ValueError("Unsupported conversion pair")
    return table[key](value)


class UtilityCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.reminder_loop.start()
        self.scheduled_message_loop.start()

    def cog_unload(self) -> None:
        self.reminder_loop.cancel()
        self.scheduled_message_loop.cancel()

    utility = app_commands.Group(name="utility", description="Utility and productivity")

    @utility.command(name="remind", description="Set a reminder")
    async def remind(self, interaction: discord.Interaction, when: str, message: str) -> None:
        try:
            seconds = parse_duration_to_seconds(when)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        remind_at = int(time.time()) + seconds
        await self.bot.db.execute(
            "INSERT INTO reminders (guild_id, user_id, channel_id, message, remind_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (interaction.guild_id, interaction.user.id, interaction.channel_id, message[:350], remind_at, int(time.time())),
        )
        await interaction.response.send_message(f"Reminder set for {when}.")

    @utility.command(name="timer", description="Start a timer and ping when done")
    async def timer(self, interaction: discord.Interaction, duration: str) -> None:
        await self.remind(interaction, duration, f"Timer complete for {duration}.")

    @utility.command(name="note-add", description="Add personal note")
    async def note_add(self, interaction: discord.Interaction, note: str) -> None:
        notes = await self.bot.db.get_notes(interaction.guild_id, interaction.user.id)
        notes.append(note[:240])
        await self.bot.db.set_notes(interaction.guild_id, interaction.user.id, notes)
        await interaction.response.send_message(f"Note saved. Total notes: {len(notes)}")

    @utility.command(name="notes", description="List notes")
    async def notes(self, interaction: discord.Interaction) -> None:
        notes = await self.bot.db.get_notes(interaction.guild_id, interaction.user.id)
        if not notes:
            await interaction.response.send_message("No notes yet.")
            return
        lines = [f"{i}. {n}" for i, n in enumerate(notes[:20], start=1)]
        await interaction.response.send_message("\n".join(lines))

    @utility.command(name="note-remove", description="Remove note by index")
    async def note_remove(self, interaction: discord.Interaction, index: int) -> None:
        notes = await self.bot.db.get_notes(interaction.guild_id, interaction.user.id)
        idx = index - 1
        if idx < 0 or idx >= len(notes):
            await interaction.response.send_message("Invalid index.", ephemeral=True)
            return
        notes.pop(idx)
        await self.bot.db.set_notes(interaction.guild_id, interaction.user.id, notes)
        await interaction.response.send_message("Note removed.")

    @utility.command(name="todo-add", description="Add todo item")
    async def todo_add(self, interaction: discord.Interaction, text: str) -> None:
        todos = await self.bot.db.get_todos(interaction.guild_id, interaction.user.id)
        todo_id = (max([t["id"] for t in todos], default=0) + 1) if todos else 1
        todos.append({"id": todo_id, "text": text[:200], "done": False})
        await self.bot.db.set_todos(interaction.guild_id, interaction.user.id, todos)
        await interaction.response.send_message(f"Todo #{todo_id} added.")

    @utility.command(name="todos", description="List todo items")
    async def todos(self, interaction: discord.Interaction) -> None:
        todos = await self.bot.db.get_todos(interaction.guild_id, interaction.user.id)
        if not todos:
            await interaction.response.send_message("No todos.")
            return
        lines = [f"{t['id']}. [{'x' if t['done'] else ' '}] {t['text']}" for t in todos[:25]]
        await interaction.response.send_message("\n".join(lines))

    @utility.command(name="todo-done", description="Mark todo done")
    async def todo_done(self, interaction: discord.Interaction, todo_id: int) -> None:
        todos = await self.bot.db.get_todos(interaction.guild_id, interaction.user.id)
        found = False
        for todo in todos:
            if todo["id"] == todo_id:
                todo["done"] = True
                found = True
                break
        if not found:
            await interaction.response.send_message("Todo not found.", ephemeral=True)
            return
        await self.bot.db.set_todos(interaction.guild_id, interaction.user.id, todos)
        await interaction.response.send_message(f"Todo #{todo_id} marked done.")

    @utility.command(name="calc", description="Calculator")
    async def calc(self, interaction: discord.Interaction, expression: str) -> None:
        try:
            result = safe_eval(expression)
        except Exception as exc:
            await interaction.response.send_message(f"Calc error: {exc}", ephemeral=True)
            return
        await interaction.response.send_message(f"Result: `{result}`")

    @utility.command(name="convert", description="Convert units")
    async def convert(self, interaction: discord.Interaction, value: float, from_unit: str, to_unit: str) -> None:
        try:
            result = convert_unit(value, from_unit, to_unit)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        await interaction.response.send_message(f"{value} {from_unit} = {result:.4f} {to_unit}")

    @utility.command(name="weather", description="Get weather by lat/lon")
    async def weather(self, interaction: discord.Interaction, latitude: float, longitude: float) -> None:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}&longitude={longitude}&current=temperature_2m,wind_speed_10m,weather_code"
        )
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=20) as resp:
                if resp.status != 200:
                    await interaction.response.send_message("Weather lookup failed.", ephemeral=True)
                    return
                data = await resp.json()
        current = data.get("current", {})
        await interaction.response.send_message(
            f"Temp: {current.get('temperature_2m')} C | Wind: {current.get('wind_speed_10m')} km/h | Code: {current.get('weather_code')}"
        )

    @utility.command(name="timezone", description="Show current time for timezone")
    async def timezone(self, interaction: discord.Interaction, tz_name: str) -> None:
        try:
            from zoneinfo import ZoneInfo

            now = datetime.now(ZoneInfo(tz_name))
        except Exception:
            await interaction.response.send_message("Invalid timezone. Example: Asia/Kolkata", ephemeral=True)
            return
        await interaction.response.send_message(f"Current time in `{tz_name}`: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    @utility.command(name="translate", description="Translate text using LibreTranslate")
    async def translate(self, interaction: discord.Interaction, target_lang: str, text: str) -> None:
        payload = {"q": text, "source": "auto", "target": target_lang, "format": "text"}
        async with aiohttp.ClientSession() as session:
            async with session.post("https://libretranslate.de/translate", json=payload, timeout=20) as resp:
                if resp.status != 200:
                    await interaction.response.send_message("Translate API failed.", ephemeral=True)
                    return
                data = await resp.json()
        await interaction.response.send_message(data.get("translatedText", "No translation returned."))

    @utility.command(name="qr", description="Generate QR code")
    async def qr(self, interaction: discord.Interaction, content: str) -> None:
        qr = segno.make(content[:800] or "blue moon")
        buffer = io.BytesIO()
        qr.save(buffer, kind="png", scale=5)
        buffer.seek(0)
        await interaction.response.send_message(file=discord.File(buffer, filename="qr.png"))

    @utility.command(name="password", description="Generate secure password")
    async def password(self, interaction: discord.Interaction, length: int = 16) -> None:
        length = max(8, min(128, length))
        pwd = random_password(length)
        await interaction.response.send_message(f"`{pwd}`", ephemeral=True)

    @utility.command(name="schedule-message", description="Schedule a message in this channel")
    async def schedule_message(self, interaction: discord.Interaction, when: str, content: str) -> None:
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("Manage Messages required.", ephemeral=True)
            return
        try:
            seconds = parse_duration_to_seconds(when)
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        send_at = int(time.time()) + seconds
        await self.bot.db.execute(
            "INSERT INTO scheduled_messages (guild_id, channel_id, content, send_at, created_by, sent) VALUES (?, ?, ?, ?, ?, 0)",
            (interaction.guild_id, interaction.channel_id, content[:1800], send_at, interaction.user.id),
        )
        await interaction.response.send_message("Scheduled message created.")

    @tasks.loop(seconds=30)
    async def reminder_loop(self) -> None:
        await self.bot.wait_until_ready()
        now = int(time.time())
        rows = await self.bot.db.fetchall("SELECT * FROM reminders WHERE remind_at <= ?", (now,))
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if guild:
                channel = guild.get_channel(row["channel_id"])
                if isinstance(channel, discord.TextChannel):
                    await channel.send(f"<@{row['user_id']}> reminder: {row['message']}")
            await self.bot.db.execute("DELETE FROM reminders WHERE id = ?", (row["id"],))

    @tasks.loop(seconds=30)
    async def scheduled_message_loop(self) -> None:
        await self.bot.wait_until_ready()
        now = int(time.time())
        rows = await self.bot.db.fetchall(
            "SELECT * FROM scheduled_messages WHERE send_at <= ? AND sent = 0",
            (now,),
        )
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if guild:
                channel = guild.get_channel(row["channel_id"])
                if isinstance(channel, discord.TextChannel):
                    await channel.send(row["content"])
            await self.bot.db.execute("UPDATE scheduled_messages SET sent = 1 WHERE id = ?", (row["id"],))


async def setup(bot: commands.Bot) -> None:
    cog = UtilityCog(bot)
    await bot.add_cog(cog)
