from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from bluemoon.utils.constants import DARES, TRIVIA, TRUTHS, WOULD_YOU_RATHER


class GamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.hangman_sessions: dict[tuple[int, int], dict[str, str | set[str] | int]] = {}
        self.guess_numbers: dict[tuple[int, int], int] = {}

    games = app_commands.Group(name="games", description="Fun and games")

    @games.command(name="trivia", description="Get a trivia question")
    async def trivia(self, interaction: discord.Interaction) -> None:
        q, a = random.choice(TRIVIA)
        await interaction.response.send_message(f"Trivia: {q}\nUse `/games answer {a}` privately to check.")

    @games.command(name="answer", description="Answer latest trivia quickly")
    async def answer(self, interaction: discord.Interaction, response: str) -> None:
        # Lightweight check against random question pool for quick engagement.
        correct = any(response.lower().strip() == ans for _, ans in TRIVIA)
        await interaction.response.send_message("Correct." if correct else "Not quite.")

    @games.command(name="hangman-start", description="Start hangman")
    async def hangman_start(self, interaction: discord.Interaction, word: str) -> None:
        key = (interaction.guild_id, interaction.channel_id)
        self.hangman_sessions[key] = {"word": word.lower(), "guessed": set(), "lives": 7}
        await interaction.response.send_message("Hangman started. Use `/games hangman-guess <letter>`." )

    @games.command(name="hangman-guess", description="Guess a letter")
    async def hangman_guess(self, interaction: discord.Interaction, letter: str) -> None:
        key = (interaction.guild_id, interaction.channel_id)
        game = self.hangman_sessions.get(key)
        if not game:
            await interaction.response.send_message("No hangman running.", ephemeral=True)
            return
        if len(letter) != 1:
            await interaction.response.send_message("Guess one letter.", ephemeral=True)
            return
        guessed: set[str] = game["guessed"]
        guessed.add(letter.lower())
        word = str(game["word"])
        if letter.lower() not in word:
            game["lives"] = int(game["lives"]) - 1
        masked = "".join([c if c in guessed else "_" for c in word])
        if "_" not in masked:
            del self.hangman_sessions[key]
            await interaction.response.send_message(f"You won. Word: `{word}`")
            return
        if int(game["lives"]) <= 0:
            del self.hangman_sessions[key]
            await interaction.response.send_message(f"Game over. Word was `{word}`")
            return
        await interaction.response.send_message(f"`{masked}` lives={game['lives']}")

    @games.command(name="truth-dare", description="Get truth or dare")
    async def truth_dare(self, interaction: discord.Interaction, mode: str) -> None:
        mode = mode.lower().strip()
        if mode == "truth":
            await interaction.response.send_message(random.choice(TRUTHS))
        elif mode == "dare":
            await interaction.response.send_message(random.choice(DARES))
        else:
            await interaction.response.send_message("Mode must be truth/dare.", ephemeral=True)

    @games.command(name="wyr", description="Would You Rather")
    async def wyr(self, interaction: discord.Interaction) -> None:
        a, b = random.choice(WOULD_YOU_RATHER)
        poll = await interaction.channel.send(f"Would you rather:\n1) {a}\n2) {b}")
        await poll.add_reaction("1??")
        await poll.add_reaction("2??")
        await interaction.response.send_message("WYR posted.", ephemeral=True)

    @games.command(name="guess-start", description="Start number guessing game")
    async def guess_start(self, interaction: discord.Interaction, max_number: int = 100) -> None:
        key = (interaction.guild_id, interaction.user.id)
        self.guess_numbers[key] = random.randint(1, max(2, max_number))
        await interaction.response.send_message(f"Guess game started. Number is between 1 and {max_number}.")

    @games.command(name="guess", description="Guess number")
    async def guess(self, interaction: discord.Interaction, value: int) -> None:
        key = (interaction.guild_id, interaction.user.id)
        answer = self.guess_numbers.get(key)
        if answer is None:
            await interaction.response.send_message("Start with `/games guess-start`.", ephemeral=True)
            return
        if value == answer:
            del self.guess_numbers[key]
            await interaction.response.send_message("Correct. You win.")
        elif value < answer:
            await interaction.response.send_message("Too low.")
        else:
            await interaction.response.send_message("Too high.")

    @games.command(name="roast", description="Playful roast")
    async def roast(self, interaction: discord.Interaction, member: discord.Member) -> None:
        lines = [
            f"{member.mention}, your ping has better timing than your jokes.",
            f"{member.mention}, even the loading icon is faster than that move.",
            f"{member.mention}, your strategy is brave. Mostly because it ignores logic.",
        ]
        await interaction.response.send_message(random.choice(lines))

    @games.command(name="compliment", description="Give a compliment")
    async def compliment(self, interaction: discord.Interaction, member: discord.Member) -> None:
        lines = [
            f"{member.mention} has top-tier energy.",
            f"{member.mention} makes this server better every day.",
            f"{member.mention} consistently brings solid vibes.",
        ]
        await interaction.response.send_message(random.choice(lines))

    @games.command(name="poll", description="Create a quick yes/no poll")
    async def poll(self, interaction: discord.Interaction, question: str) -> None:
        msg = await interaction.channel.send(f"Poll: **{question}**")
        await msg.add_reaction("??")
        await msg.add_reaction("??")
        await interaction.response.send_message("Poll created.", ephemeral=True)

    @games.command(name="rpg", description="Simple RPG adventure roll")
    async def rpg(self, interaction: discord.Interaction) -> None:
        reward = random.randint(30, 140)
        await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=reward)
        await interaction.response.send_message(f"Adventure complete. You found {reward} MoonCoin.")

    @games.command(name="pet", description="Pets and farming mini loop")
    async def pet(self, interaction: discord.Interaction, action: str) -> None:
        action = action.lower().strip()
        rewards = {"adopt": 1, "feed": 2, "farm": 5}
        if action not in rewards:
            await interaction.response.send_message("Actions: adopt, feed, farm", ephemeral=True)
            return
        await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=rewards[action] * 20)
        await interaction.response.send_message(f"Pet action `{action}` complete.")

    @games.command(name="chess", description="Chess placeholder command")
    async def chess(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message("Chess module hook is ready; integrate your preferred chess API or bot for full matches.")


async def setup(bot: commands.Bot) -> None:
    cog = GamesCog(bot)
    await bot.add_cog(cog)
