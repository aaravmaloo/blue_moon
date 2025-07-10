import discord 
from discord import app_commands
from discord.ext import commands, tasks
import json
from datetime import datetime, timezone, timedelta
import asyncio
import os 
from discord import Forbidden
import dotenv

dotenv.load_dotenv(r"C:\Users\Aarav Maloo\Desktop\blue_moon\src\secret.env")
DISCORD_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True

HARDKICKS_FILE = "hardkicks.json"

def load_hardkicks():
    if os.path.exists(HARDKICKS_FILE):
        with open(HARDKICKS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_hardkicks(data):
    with open(HARDKICKS_FILE, "w") as f:
        json.dump(data, f)

# Store appeals in persistent storage
appeal_records = load_hardkicks()

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Kick command
    @commands.command()
    @commands.has_permissions(administrator=True, kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        try:
            # Try to DM before kicking
            try:
                await member.send(f"You have been kicked from {ctx.guild.name}. Reason: {reason if reason else 'No reason provided.'}")
            except Exception:
                pass
            await member.kick(reason=reason)
            await ctx.send(f"{member.mention} has been kicked and removed from the server. Reason: {reason}")
        except Forbidden:
            await ctx.send("I do not have permission to kick this member. Please check my role and permissions.")

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.describe(member="Member to kick", reason="Reason for kick")
    @app_commands.checks.has_permissions(administrator=True, kick_members=True)
    async def kick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            try:
                await member.send(f"You have been kicked from {interaction.guild.name}. Reason: {reason if reason else 'No reason provided.'}")
            except Exception:
                pass
            await member.kick(reason=reason)
            await interaction.response.send_message(f"{member.mention} has been kicked and removed from the server. Reason: {reason}")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to kick this member. Please check my role and permissions.", ephemeral=True)

    # Hardkick command
    @commands.command()
    @commands.has_permissions(administrator=True, kick_members=True, ban_members=True)
    async def hardkick(self, ctx, member: discord.Member, *, reason=None):
        try:
            # Store who hardkicked for appeal
            appeal_records[str(member.id)] = ctx.author.id
            save_hardkicks(appeal_records)
            try:
                await member.send(f"You have been hardkicked (banned) from {ctx.guild.name}. Reason: {reason if reason else 'No reason provided.'}\nYou may appeal by sending /appeal here.")
            except Exception:
                pass
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been hardkicked (banned) and removed from the server. Reason: {reason}\nThey can appeal by DMing the bot with /appeal.")
        except Forbidden:
            await ctx.send("I do not have permission to hardkick (ban) this member. Please check my role and permissions.")

    @app_commands.command(name="hardkick", description="Hardkick a member (with appeal option).")
    @app_commands.describe(member="Member to hardkick", reason="Reason for hardkick")
    @app_commands.checks.has_permissions(administrator=True, kick_members=True, ban_members=True)
    async def hardkick_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            appeal_records[str(member.id)] = interaction.user.id
            save_hardkicks(appeal_records)
            try:
                await member.send(f"You have been hardkicked (banned) from {interaction.guild.name}. Reason: {reason if reason else 'No reason provided.'}\nYou may appeal by sending /appeal here.")
            except Exception:
                pass
            await member.ban(reason=reason)
            await interaction.response.send_message(f"{member.mention} has been hardkicked (banned) and removed from the server. Reason: {reason}\nThey can appeal by DMing the bot with /appeal.")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to hardkick (ban) this member. Please check my role and permissions.", ephemeral=True)

    # Ban command
    @commands.command()
    @commands.has_permissions(administrator=True, ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason=None):
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned. Reason: {reason}")
        except Forbidden:
            await ctx.send("I do not have permission to ban this member. Please check my role and permissions.")

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.describe(member="Member to ban", reason="Reason for ban")
    @app_commands.checks.has_permissions(administrator=True, ban_members=True)
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        try:
            await member.ban(reason=reason)
            await interaction.response.send_message(f"{member.mention} has been banned. Reason: {reason}")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to ban this member. Please check my role and permissions.", ephemeral=True)

    # Mute command
    @commands.command()
    @commands.has_permissions(administrator=True, manage_roles=True)
    async def mute(self, ctx, member: discord.Member = None, duration: int = None, unit: str = None):
        if not member or not duration or not unit:
            await ctx.send("Usage: !mute @member duration unit (e.g. !mute @user 5 min)")
            return
        role = discord.utils.get(ctx.guild.roles, name="Muted")
        if not role:
            role = await ctx.guild.create_role(name="Muted")
            for channel in ctx.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False)
        try:
            await member.add_roles(role)
            await ctx.send(f"{member.mention} has been muted for {duration} {unit}.")
            seconds = duration
            if unit.startswith('min'):
                seconds *= 60
            elif unit.startswith('h'):
                seconds *= 3600
            elif unit.startswith('d'):
                seconds *= 86400
            await asyncio.sleep(seconds)
            await member.remove_roles(role)
            await ctx.send(f"{member.mention} is now unmuted.")
        except Forbidden:
            await ctx.send("I do not have permission to mute this member. Please check my role and permissions.")

    @app_commands.command(name="mute", description="Mute a member for a duration.")
    @app_commands.describe(member="Member to mute", duration="Duration", unit="Unit (sec/min/hr/day)")
    @app_commands.checks.has_permissions(administrator=True, manage_roles=True)
    async def mute_slash(self, interaction: discord.Interaction, member: discord.Member, duration: int, unit: str):
        role = discord.utils.get(interaction.guild.roles, name="Muted")
        if not role:
            role = await interaction.guild.create_role(name="Muted")
            for channel in interaction.guild.channels:
                await channel.set_permissions(role, send_messages=False, speak=False)
        try:
            await member.add_roles(role)
            await interaction.response.send_message(f"{member.mention} has been muted for {duration} {unit}.")
            seconds = duration
            if unit.startswith('min'):
                seconds *= 60
            elif unit.startswith('h'):
                seconds *= 3600
            elif unit.startswith('d'):
                seconds *= 86400
            await asyncio.sleep(seconds)
            await member.remove_roles(role)
            await interaction.followup.send(f"{member.mention} is now unmuted.")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to mute this member. Please check my role and permissions.", ephemeral=True)

    # Timeout command
    @commands.command()
    @commands.has_permissions(administrator=True, moderate_members=True)
    async def timeout(self, ctx, member: discord.Member = None, duration: int = None, unit: str = None):
        if not member or not duration or not unit:
            await ctx.send("Usage: !timeout @member duration unit (e.g. !timeout @user 5 min)")
            return
        seconds = duration
        if unit.startswith('min'):
            seconds *= 60
        elif unit.startswith('h'):
            seconds *= 3600
        elif unit.startswith('d'):
            seconds *= 86400
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason="Timeout by mod")
            await ctx.send(f"{member.mention} is timed out for {duration} {unit}.")
        except Forbidden:
            await ctx.send("I do not have permission to timeout this member. Please check my role and permissions.")

    @app_commands.command(name="timeout", description="Timeout a member for a duration.")
    @app_commands.describe(member="Member to timeout", duration="Duration", unit="Unit (sec/min/hr/day)")
    @app_commands.checks.has_permissions(administrator=True, moderate_members=True)
    async def timeout_slash(self, interaction: discord.Interaction, member: discord.Member, duration: int, unit: str):
        seconds = duration
        if unit.startswith('min'):
            seconds *= 60
        elif unit.startswith('h'):
            seconds *= 3600
        elif unit.startswith('d'):
            seconds *= 86400
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason="Timeout by mod")
            await interaction.response.send_message(f"{member.mention} is timed out for {duration} {unit}.")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to timeout this member. Please check my role and permissions.", ephemeral=True)

    # Mutevoice command
    @commands.command()
    @commands.has_permissions(administrator=True, mute_members=True)
    async def mutevoice(self, ctx, member: discord.Member = None):
        if not member:
            await ctx.send("Usage: !mutevoice @member")
            return
        try:
            await member.edit(mute=True)
            await ctx.send(f"{member.mention} has been voice muted.")
        except Forbidden:
            await ctx.send("I do not have permission to voice mute this member. Please check my role and permissions.")

    @app_commands.command(name="mutevoice", description="Voice mute a member.")
    @app_commands.describe(member="Member to voice mute")
    @app_commands.checks.has_permissions(administrator=True, mute_members=True)
    async def mutevoice_slash(self, interaction: discord.Interaction, member: discord.Member):
        try:
            await member.edit(mute=True)
            await interaction.response.send_message(f"{member.mention} has been voice muted.")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to voice mute this member. Please check my role and permissions.", ephemeral=True)
# Appeal command in DMs
@app_commands.command(name="appeal", description="Appeal a hardkick.")
async def appeal(interaction: discord.Interaction):
    appeal_records = load_hardkicks()
    user_id = str(interaction.user.id)
    if user_id not in appeal_records:
        await interaction.response.send_message("No record of a hardkick found for you, or appeal already submitted.", ephemeral=True)
        return
    admin_id = appeal_records[user_id]
    admin = await interaction.client.fetch_user(admin_id)
    await interaction.response.send_message("Your appeal has been submitted to the admin who removed you. Please wait for a response.", ephemeral=True)
    try:
        await admin.send(f"User {interaction.user} (ID: {interaction.user.id}) has appealed their hardkick.\nReply with /approveappeal {interaction.user.id} or /rejectappeal {interaction.user.id} <reason>.")
    except Exception:
        pass

@app_commands.command(name="approveappeal", description="Approve a user's appeal (admin only, DM only)")
@app_commands.describe(user_id="ID of the user to approve")
async def approveappeal(interaction: discord.Interaction, user_id: str):
    appeal_records = load_hardkicks()
    admin_id = appeal_records.get(user_id)
    if admin_id is None or interaction.user.id != admin_id:
        await interaction.response.send_message("You are not authorized to approve this appeal.", ephemeral=True)
        return
    user = await interaction.client.fetch_user(int(user_id))
    for guild in interaction.client.guilds:
        try:
            await guild.unban(user, reason="Appeal approved")
        except Exception:
            pass
    await user.send(f"Your appeal has been approved. You may rejoin the server.")
    await interaction.response.send_message(f"Appeal approved for user {user_id}.", ephemeral=True)
    if user_id in appeal_records:
        del appeal_records[user_id]
        save_hardkicks(appeal_records)

@app_commands.command(name="rejectappeal", description="Reject a user's appeal (admin only, DM only)")
@app_commands.describe(user_id="ID of the user to reject", reason="Reason for rejection")
async def rejectappeal(interaction: discord.Interaction, user_id: str, reason: str):
    appeal_records = load_hardkicks()
    admin_id = appeal_records.get(user_id)
    if admin_id is None or interaction.user.id != admin_id:
        await interaction.response.send_message("You are not authorized to reject this appeal.", ephemeral=True)
        return
    user = await interaction.client.fetch_user(int(user_id))
    await user.send(f"Your appeal has been rejected. Reason: {reason}")
    await interaction.response.send_message(f"Appeal rejected for user {user_id}.", ephemeral=True)
    if user_id in appeal_records:
        del appeal_records[user_id]
        save_hardkicks(appeal_records)

class BlueMoonBot(commands.Bot):
    async def setup_hook(self):
        await self.add_cog(Mod(self))
        # Register appeal commands globally (so they work in DMs)
        self.tree.add_command(appeal)
        self.tree.add_command(approveappeal)
        self.tree.add_command(rejectappeal)
        # Sync global commands
        await self.tree.sync()
        print(f"Synced slash commands globally (including DMs).")

bot = BlueMoonBot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(DISCORD_TOKEN)