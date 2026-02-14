from __future__ import annotations

import json
import random
import time

import discord
from discord import app_commands
from discord.ext import commands


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    economy = app_commands.Group(name="economy", description="Economy commands")

    async def _cooldown_ok(self, guild_id: int, user_id: int, field: str, cooldown: int) -> tuple[bool, int]:
        row = await self.bot.db.get_user_row(guild_id, user_id)
        last = row[field] or 0
        now = int(time.time())
        remain = cooldown - (now - int(last))
        if remain > 0:
            return False, remain
        await self.bot.db.set_user_field(guild_id, user_id, field, now)
        return True, 0

    @economy.command(name="balance", description="View wallet and bank balance")
    async def balance(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        row = await self.bot.db.get_user_row(interaction.guild_id, target.id)
        currency = await self.bot.db.get_setting(interaction.guild_id, "economy_currency")
        await interaction.response.send_message(
            f"{target.mention} Wallet: **{row['wallet']} {currency}** | Bank: **{row['bank']} {currency}**"
        )

    @economy.command(name="daily", description="Claim daily reward")
    async def daily(self, interaction: discord.Interaction) -> None:
        ok, remain = await self._cooldown_ok(interaction.guild_id, interaction.user.id, "last_daily", 24 * 3600)
        if not ok:
            await interaction.response.send_message(f"Daily resets in {remain // 3600}h {(remain % 3600) // 60}m", ephemeral=True)
            return
        amount = int(await self.bot.db.get_setting(interaction.guild_id, "economy_daily") or 200)
        bal = await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=amount)
        await interaction.response.send_message(f"Daily claimed: +{amount}. Wallet now {bal.wallet}.")

    @economy.command(name="weekly", description="Claim weekly reward")
    async def weekly(self, interaction: discord.Interaction) -> None:
        ok, remain = await self._cooldown_ok(interaction.guild_id, interaction.user.id, "last_weekly", 7 * 24 * 3600)
        if not ok:
            await interaction.response.send_message(f"Weekly resets in {remain // 3600}h", ephemeral=True)
            return
        amount = int(await self.bot.db.get_setting(interaction.guild_id, "economy_weekly") or 1000)
        bal = await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=amount)
        await interaction.response.send_message(f"Weekly claimed: +{amount}. Wallet now {bal.wallet}.")

    @economy.command(name="work", description="Work for money")
    async def work(self, interaction: discord.Interaction) -> None:
        ok, remain = await self._cooldown_ok(interaction.guild_id, interaction.user.id, "last_work", 3600)
        if not ok:
            await interaction.response.send_message(f"Work cooldown: {remain // 60}m", ephemeral=True)
            return
        min_amt = int(await self.bot.db.get_setting(interaction.guild_id, "economy_work_min") or 50)
        max_amt = int(await self.bot.db.get_setting(interaction.guild_id, "economy_work_max") or 220)
        amount = random.randint(min_amt, max(max_amt, min_amt))
        bal = await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=amount)
        await interaction.response.send_message(f"You worked and earned **{amount}**. Wallet: {bal.wallet}.")

    @economy.command(name="crime", description="Risky crime for money")
    async def crime(self, interaction: discord.Interaction) -> None:
        ok, remain = await self._cooldown_ok(interaction.guild_id, interaction.user.id, "last_crime", 7200)
        if not ok:
            await interaction.response.send_message(f"Crime cooldown: {remain // 60}m", ephemeral=True)
            return
        chance = float(await self.bot.db.get_setting(interaction.guild_id, "economy_crime_win") or 0.45)
        if random.random() < chance:
            gain = random.randint(120, 500)
            bal = await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=gain)
            await interaction.response.send_message(f"Crime succeeded: +{gain}. Wallet: {bal.wallet}.")
        else:
            loss = random.randint(80, 220)
            bal = await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=-loss)
            await interaction.response.send_message(f"Crime failed: -{loss}. Wallet: {bal.wallet}.")

    @economy.command(name="rob", description="Attempt to rob another user")
    async def rob(self, interaction: discord.Interaction, target: discord.Member) -> None:
        if target.bot or target.id == interaction.user.id:
            await interaction.response.send_message("Invalid target.", ephemeral=True)
            return
        target_row = await self.bot.db.get_user_row(interaction.guild_id, target.id)
        if target_row["wallet"] < 50:
            await interaction.response.send_message("Target wallet too low.", ephemeral=True)
            return
        if random.random() < 0.45:
            stolen = min(target_row["wallet"], random.randint(50, 250))
            await self.bot.db.add_balance(interaction.guild_id, target.id, wallet_delta=-stolen)
            thief_bal = await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=stolen)
            await interaction.response.send_message(f"Rob success: +{stolen}. Wallet: {thief_bal.wallet}")
        else:
            fine = random.randint(40, 180)
            bal = await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=-fine)
            await interaction.response.send_message(f"Rob failed. Fine -{fine}. Wallet: {bal.wallet}")

    @economy.command(name="deposit", description="Deposit to bank")
    async def deposit(self, interaction: discord.Interaction, amount: int) -> None:
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return
        row = await self.bot.db.get_user_row(interaction.guild_id, interaction.user.id)
        if row["wallet"] < amount:
            await interaction.response.send_message("Not enough in wallet.", ephemeral=True)
            return
        await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=-amount, bank_delta=amount)
        await interaction.response.send_message(f"Deposited {amount}.")

    @economy.command(name="withdraw", description="Withdraw from bank")
    async def withdraw(self, interaction: discord.Interaction, amount: int) -> None:
        if amount <= 0:
            await interaction.response.send_message("Amount must be positive.", ephemeral=True)
            return
        row = await self.bot.db.get_user_row(interaction.guild_id, interaction.user.id)
        if row["bank"] < amount:
            await interaction.response.send_message("Not enough in bank.", ephemeral=True)
            return
        await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=amount, bank_delta=-amount)
        await interaction.response.send_message(f"Withdrew {amount}.")

    @economy.command(name="pay", description="Pay another user")
    async def pay(self, interaction: discord.Interaction, target: discord.Member, amount: int) -> None:
        if target.bot or target.id == interaction.user.id or amount <= 0:
            await interaction.response.send_message("Invalid payment target/amount.", ephemeral=True)
            return
        row = await self.bot.db.get_user_row(interaction.guild_id, interaction.user.id)
        if row["wallet"] < amount:
            await interaction.response.send_message("Insufficient wallet.", ephemeral=True)
            return
        await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=-amount)
        await self.bot.db.add_balance(interaction.guild_id, target.id, wallet_delta=amount)
        await interaction.response.send_message(f"Sent {amount} to {target.mention}.")

    @economy.command(name="gamble", description="Gamble amount with coinflip odds")
    async def gamble(self, interaction: discord.Interaction, amount: int) -> None:
        if amount <= 0:
            await interaction.response.send_message("Amount must be > 0.", ephemeral=True)
            return
        row = await self.bot.db.get_user_row(interaction.guild_id, interaction.user.id)
        if row["wallet"] < amount:
            await interaction.response.send_message("Not enough wallet balance.", ephemeral=True)
            return
        if random.random() < 0.48:
            win = int(amount * 1.8)
            await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=win)
            await interaction.response.send_message(f"You won {win}.")
        else:
            await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=-amount)
            await interaction.response.send_message(f"You lost {amount}.")

    @economy.command(name="shop-add", description="Add item to shop")
    async def shop_add(self, interaction: discord.Interaction, name: str, price: int, description: str) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild required.", ephemeral=True)
            return
        await self.bot.db.execute(
            """
            CREATE TABLE IF NOT EXISTS shop_items (
                guild_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                price INTEGER NOT NULL,
                description TEXT NOT NULL,
                stock INTEGER,
                PRIMARY KEY (guild_id, name)
            )
            """
        )
        await self.bot.db.execute(
            "INSERT OR REPLACE INTO shop_items (guild_id, name, price, description, stock) VALUES (?, ?, ?, ?, COALESCE((SELECT stock FROM shop_items WHERE guild_id = ? AND name = ?), NULL))",
            (interaction.guild_id, name.lower(), max(price, 1), description[:200], interaction.guild_id, name.lower()),
        )
        await interaction.response.send_message("Shop item added.")

    @economy.command(name="shop", description="View shop inventory")
    async def shop(self, interaction: discord.Interaction) -> None:
        rows = await self.bot.db.fetchall("SELECT name, price, description FROM shop_items WHERE guild_id = ? ORDER BY price ASC", (interaction.guild_id,))
        if not rows:
            await interaction.response.send_message("Shop is empty.")
            return
        text = "\n".join([f"`{r['name']}` - {r['price']} :: {r['description']}" for r in rows[:20]])
        await interaction.response.send_message(text)

    @economy.command(name="buy", description="Buy item from shop")
    async def buy(self, interaction: discord.Interaction, item: str) -> None:
        row = await self.bot.db.fetchone(
            "SELECT name, price FROM shop_items WHERE guild_id = ? AND name = ?",
            (interaction.guild_id, item.lower()),
        )
        if not row:
            await interaction.response.send_message("Item not found.", ephemeral=True)
            return
        user_row = await self.bot.db.get_user_row(interaction.guild_id, interaction.user.id)
        if user_row["wallet"] < row["price"]:
            await interaction.response.send_message("Not enough wallet balance.", ephemeral=True)
            return
        await self.bot.db.add_balance(interaction.guild_id, interaction.user.id, wallet_delta=-row["price"])
        inventory = await self.bot.db.add_inventory_item(interaction.guild_id, interaction.user.id, row["name"])
        await interaction.response.send_message(f"Bought `{row['name']}`. Inventory size: {len(inventory)}")

    @economy.command(name="inventory", description="View your inventory")
    async def inventory(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        target = member or interaction.user
        inv = await self.bot.db.get_inventory(interaction.guild_id, target.id)
        if not inv:
            await interaction.response.send_message(f"{target.mention} inventory is empty.")
            return
        counts: dict[str, int] = {}
        for item in inv:
            counts[item] = counts.get(item, 0) + 1
        text = "\n".join([f"{name} x{qty}" for name, qty in sorted(counts.items())[:25]])
        await interaction.response.send_message(f"Inventory for {target.mention}:\n{text}")


async def setup(bot: commands.Bot) -> None:
    cog = EconomyCog(bot)
    await bot.add_cog(cog)
