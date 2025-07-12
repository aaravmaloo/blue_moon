
import discord 
from discord import app_commands
from discord.ext import commands, tasks
import json
from datetime import datetime, timezone, timedelta
import asyncio
import os 
from discord import Forbidden
import dotenv
import random

###########################
# --- GLOBAL SLASH COMMANDS ---
###########################

@app_commands.command(name="lvlprogress", description="Show your XP, XP needed for next level, and estimated messages needed.")
async def lvlprogress(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    guild_id = str(interaction.guild.id)
    key = f"{guild_id}:{user_id}"
    user_data = levels.get(key, {"xp": 0, "level": 1})
    level = user_data["level"]
    xp = user_data["xp"]
    if level >= 10:
        await interaction.response.send_message(f"You are at the max level (10)! Total XP: {xp}", ephemeral=True)
        return
    next_level = level + 1
    required_xp = next_level * 100
    xp_needed = required_xp - xp
    avg_xp_per_msg = 10  # Based on random.randint(5, 15)
    est_msgs = max(1, xp_needed // avg_xp_per_msg)
    embed = discord.Embed(title="Level Progress", color=discord.Color.blurple())
    embed.add_field(name="Current Level", value=str(level), inline=True)
    embed.add_field(name="Current XP", value=str(xp), inline=True)
    embed.add_field(name="Next Level", value=str(next_level), inline=True)
    embed.add_field(name="XP Needed", value=str(xp_needed), inline=True)
    embed.add_field(name="Estimated Messages Needed", value=str(est_msgs), inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@app_commands.command(name="roleinfo", description="Show info and permissions for a role.")
@app_commands.describe(role="The role to show info for")
async def roleinfo(interaction: discord.Interaction, role: discord.Role):
    embed = discord.Embed(title=f"Role Info: {role.name}", color=role.color)
    embed.add_field(name="Role ID", value=role.id, inline=True)
    embed.add_field(name="Hoisted?", value="Yes" if role.hoist else "No", inline=True)
    embed.add_field(name="Mentionable?", value="Yes" if role.mentionable else "No", inline=True)
    embed.add_field(name="Color", value=str(role.color), inline=True)
    perms = [perm.replace('_', ' ').title() for perm, val in role.permissions if val]
    if perms:
        perms_str = ", ".join(perms)
    else:
        perms_str = "None"
    embed.add_field(name="Permissions", value=perms_str, inline=False)
    embed.set_footer(text=f"Position: {role.position}")
    await interaction.response.send_message(embed=embed, ephemeral=True)


dotenv.load_dotenv(r"C:\Users\Aarav Maloo\Desktop\blue_moon\src\secret.env")
DISCORD_TOKEN = os.getenv("BOT_TOKEN")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True
intents.voice_states = True

HARDKICKS_FILE = "hardkicks.json"
LEVELS_FILE = "levels.json"

LEVEL_ROLE_CONFIG = [
    # (level, role_name, permissions, color, hoist)
    (1, "Level 1", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True
    ), discord.Color.light_grey(), True),
    (2, "Level 2", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True
    ), discord.Color.teal(), True),
    (3, "Level 3", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True, use_external_stickers=True
    ), discord.Color.green(), True),
    (4, "Level 4", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True, use_external_stickers=True, connect=True, speak=True
    ), discord.Color.blue(), True),
    (5, "Level 5", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True, use_external_stickers=True, connect=True, speak=True, mention_everyone=True
    ), discord.Color.purple(), True),
    (6, "Level 6", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True, use_external_stickers=True, connect=True, speak=True, mention_everyone=True, manage_messages=True
    ), discord.Color.orange(), True),
    (7, "Level 7", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True, use_external_stickers=True, connect=True, speak=True, mention_everyone=True, manage_messages=True, manage_threads=True
    ), discord.Color.gold(), True),
    (8, "Level 8", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True, use_external_stickers=True, connect=True, speak=True, mention_everyone=True, manage_messages=True, manage_threads=True, manage_webhooks=True
    ), discord.Color.dark_gold(), True),
    (9, "Level 9", discord.Permissions(
        read_messages=True, send_messages=True, add_reactions=True, embed_links=True, attach_files=True,
        create_public_threads=True, create_private_threads=True, read_message_history=True, use_external_emojis=True, use_external_stickers=True, connect=True, speak=True, mention_everyone=True, manage_messages=True, manage_threads=True, manage_webhooks=True, manage_nicknames=True
    ), discord.Color.dark_teal(), True),
    (10, "Level 10", discord.Permissions.all(), discord.Color.red(), True),  # Owner, all perms
]

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

def load_levels():
    if os.path.exists(LEVELS_FILE):
        with open(LEVELS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_levels(data):
    with open(LEVELS_FILE, "w") as f:
        json.dump(data, f)

levels = load_levels()

class Mod(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def bot_role_higher(self, guild, member):
        bot_member = guild.me
        return bot_member.top_role > member.top_role

    # Kick command
    @commands.command()
    @commands.has_permissions(administrator=True, kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason=None):
        if not self.bot_role_higher(ctx.guild, member):
            await ctx.send("I cannot kick this member because their top role is higher or equal to mine in the server role list.")
            return
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
        if not self.bot_role_higher(interaction.guild, member):
            await interaction.response.send_message("I cannot kick this member because their top role is higher or equal to mine in the server role list.", ephemeral=True)
            return
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
        if not self.bot_role_higher(ctx.guild, member):
            await ctx.send("I cannot hardkick (ban) this member because their top role is higher or equal to mine in the server role list.")
            return
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
        if not self.bot_role_higher(interaction.guild, member):
            await interaction.response.send_message("I cannot hardkick (ban) this member because their top role is higher or equal to mine in the server role list.", ephemeral=True)
            return
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
        if not self.bot_role_higher(ctx.guild, member):
            await ctx.send("I cannot ban this member because their top role is higher or equal to mine in the server role list.")
            return
        try:
            await member.ban(reason=reason)
            await ctx.send(f"{member.mention} has been banned. Reason: {reason}")
        except Forbidden:
            await ctx.send("I do not have permission to ban this member. Please check my role and permissions.")

    @app_commands.command(name="ban", description="Ban a member.")
    @app_commands.describe(member="Member to ban", reason="Reason for ban")
    @app_commands.checks.has_permissions(administrator=True, ban_members=True)
    async def ban_slash(self, interaction: discord.Interaction, member: discord.Member, reason: str = None):
        if not self.bot_role_higher(interaction.guild, member):
            await interaction.response.send_message("I cannot ban this member because their top role is higher or equal to mine in the server role list.", ephemeral=True)
            return
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
        if not self.bot_role_higher(ctx.guild, member):
            await ctx.send("I cannot mute this member because their top role is higher or equal to mine in the server role list.")
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
        if not self.bot_role_higher(interaction.guild, member):
            await interaction.response.send_message("I cannot mute this member because their top role is higher or equal to mine in the server role list.", ephemeral=True)
            return
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
        if not member or not duration or not unit or unit not in ["sec", "min", "hr", "day"]:
            await ctx.send("Usage: !timeout @member <duration> <unit> (unit: sec, min, hr, day)")
            return
        if not self.bot_role_higher(ctx.guild, member):
            await ctx.send("I cannot timeout this member because their top role is higher or equal to mine in the server role list.")
            return
        seconds = duration
        if unit == "min":
            seconds *= 60
        elif unit == "hr":
            seconds *= 3600
        elif unit == "day":
            seconds *= 86400
        until = discord.utils.utcnow() + timedelta(seconds=seconds)
        try:
            await member.timeout(until, reason="Timeout by mod")
            await ctx.send(f"{member.mention} is timed out for {duration} {unit}.")
        except Forbidden:
            await ctx.send("I do not have permission to timeout this member. Please check my role and permissions.")

    @app_commands.command(name="timeout", description="Timeout a member for a duration.")
    @app_commands.describe(member="Member to timeout", duration="Duration", unit="Unit (sec, min, hr, day)")
    @app_commands.checks.has_permissions(administrator=True, moderate_members=True)
    async def timeout_slash(self, interaction: discord.Interaction, member: discord.Member, duration: int, unit: str):
        if unit not in ["sec", "min", "hr", "day"]:
            await interaction.response.send_message("Unit must be one of: sec, min, hr, day.", ephemeral=True)
            return
        if not self.bot_role_higher(interaction.guild, member):
            await interaction.response.send_message("I cannot timeout this member because their top role is higher or equal to mine in the server role list.", ephemeral=True)
            return
        seconds = duration
        if unit == "min":
            seconds *= 60
        elif unit == "hr":
            seconds *= 3600
        elif unit == "day":
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
        if not self.bot_role_higher(ctx.guild, member):
            await ctx.send("I cannot voice mute this member because their top role is higher or equal to mine in the server role list.")
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
        if not self.bot_role_higher(interaction.guild, member):
            await interaction.response.send_message("I cannot voice mute this member because their top role is higher or equal to mine in the server role list.", ephemeral=True)
            return
        try:
            await member.edit(mute=True)
            await interaction.response.send_message(f"{member.mention} has been voice muted.")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to voice mute this member. Please check my role and permissions.", ephemeral=True)

@app_commands.command(name="assignrole", description="Assign a role to a user.")
@app_commands.describe(user="User to assign the role to", role="Role to assign")
@app_commands.checks.has_permissions(administrator=True, manage_roles=True)
async def assignrole_slash(interaction: discord.Interaction, user: discord.Member, role: discord.Role):
    bot_member = interaction.guild.me
    mod_cog = None
    for cog in interaction.client.cogs.values():
        if isinstance(cog, Mod):
            mod_cog = cog
            break
    if role >= bot_member.top_role:
        await interaction.response.send_message("I cannot assign a role higher or equal to my highest role.", ephemeral=True)
        return
    if mod_cog and not mod_cog.bot_role_higher(interaction.guild, user):
        await interaction.response.send_message("I cannot assign roles to this user because their top role is higher or equal to mine.", ephemeral=True)
        return
    try:
        await user.add_roles(role)
        await interaction.response.send_message(f"Assigned role {role.mention} to {user.mention}.")
    except Forbidden:
        await interaction.response.send_message("I do not have permission to assign this role. Please check my permissions and role order.", ephemeral=True)

# Appeal command in DMs
@app_commands.command(name="appeal", description="Appeal a hardkick.")
@app_commands.describe(explanation="Explain what went wrong and why you won't do it again (required)")
async def appeal(interaction: discord.Interaction, explanation: str):
    appeal_records = load_hardkicks()
    user_id = str(interaction.user.id)
    if user_id not in appeal_records:
        await interaction.response.send_message("No record of a hardkick found for you, or appeal already submitted.", ephemeral=True)
        return
    admin_id = appeal_records[user_id]
    admin = await interaction.client.fetch_user(admin_id)
    await interaction.response.send_message("Your appeal has been submitted to the admin who removed you. Please wait for a response.", ephemeral=True)
    try:
        await admin.send(f"User {interaction.user} (ID: {interaction.user.id}) has appealed their hardkick.\nExplanation: {explanation}\nReply with /approveappeal {interaction.user.id} or /rejectappeal {interaction.user.id} <reason>.")
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

ROLE_TEMPLATES = {
    "owner": {
        "name": "👑 Owner",
        "permissions": discord.Permissions(administrator=True),
        "color": discord.Color.gold()
    },
    "pro_mod": {
        "name": "🔥 Pro Mod",
        "permissions": discord.Permissions(
            manage_messages=True, kick_members=True, ban_members=True, manage_roles=True, manage_channels=True,
            create_instant_invite=True, send_messages=True, send_messages_in_threads=True, manage_threads=True,
            create_public_threads=True, create_private_threads=True, add_reactions=True, attach_files=True,
            embed_links=True, read_message_history=True, mention_everyone=True, connect=True, speak=True,
            use_application_commands=True
        ),
        "color": discord.Color.orange()
    },
    "active": {
        "name": "💬 Active",
        "permissions": discord.Permissions(
            send_messages=True, read_messages=True, connect=True, speak=True, read_message_history=True,
            add_reactions=True, embed_links=True, attach_files=True, use_external_emojis=True, use_external_stickers=True
        ),
        "color": discord.Color.green()
    },
    "member": {
        "name": "👤 Member",
        "permissions": discord.Permissions(
            read_messages=True, send_messages=True, connect=True, speak=True, read_message_history=True,
            add_reactions=True, embed_links=True, attach_files=True, use_external_emojis=True, use_external_stickers=True
        ),
        "color": discord.Color.blue()
    },
    "mod": {
        "name": "🛡️ Mod",
        "permissions": discord.Permissions(
            kick_members=True, ban_members=True, manage_messages=True, manage_roles=True, view_channel=True,
            manage_channels=True, create_instant_invite=True, send_messages=True, send_messages_in_threads=True,
            manage_threads=True, create_public_threads=True, create_private_threads=True, add_reactions=True,
            attach_files=True, embed_links=True, read_message_history=True, mention_everyone=True,
            manage_emojis_and_stickers=True, use_external_emojis=True, use_external_stickers=True, connect=True,
            speak=True, use_application_commands=True
        ),
        "color": discord.Color.purple()
    },
    "head_mod": {
        "name": "⭐ Head Mod",
        "permissions": discord.Permissions(
            kick_members=True, ban_members=True, manage_messages=True, manage_roles=True, manage_channels=True
        ),
        "color": discord.Color.teal()
    }
}

@app_commands.command(name="addrolefromtemplate", description="Add a preconfigured role from a template.")
@app_commands.describe(template="Role template to add (owner, pro_active, active, member, mod, head_mod)")
@app_commands.checks.has_permissions(administrator=True, manage_roles=True)
async def addrolefromtemplate(interaction: discord.Interaction, template: str):
    template = template.lower()
    if template not in ROLE_TEMPLATES:
        await interaction.response.send_message(
            "Invalid template. Choose from: owner, pro_active, active, member, mod, head_mod.", ephemeral=True)
        return
    guild = interaction.guild
    config = ROLE_TEMPLATES[template]
    # Check if role already exists
    if discord.utils.get(guild.roles, name=config["name"]):
        await interaction.response.send_message(f"Role {config['name']} already exists.", ephemeral=True)
        return
    try:
        role = await guild.create_role(
            name=config["name"],
            permissions=config["permissions"],
            color=config["color"],
            mentionable=True,
            reason=f"Created by {interaction.user} using /addrolefromtemplate"
        )
        await interaction.response.send_message(f"Role {role.mention} created successfully!", ephemeral=True)
    except Forbidden:
        await interaction.response.send_message("I do not have permission to create roles. Please check my permissions and role order.", ephemeral=True)

    @commands.command(name="addrolefromtemplate")
    @commands.has_permissions(administrator=True, manage_roles=True)
    async def addrolefromtemplate_prefix(self, ctx, template: str):
        template = template.lower()
        if template not in ROLE_TEMPLATES:
            await ctx.send("Invalid template. Choose from: owner, pro_active, active, member, mod, head_mod.")
            return
        guild = ctx.guild
        config = ROLE_TEMPLATES[template]
        if discord.utils.get(guild.roles, name=config["name"]):
            await ctx.send(f"Role {config['name']} already exists.")
            return
        try:
            role = await guild.create_role(
                name=config["name"],
                permissions=config["permissions"],
                color=config["color"],
                mentionable=True,
                reason=f"Created by {ctx.author} using !addrolefromtemplate"
            )
            await ctx.send(f"Role {role.mention} created successfully!")
        except Forbidden:
            await ctx.send("I do not have permission to create roles. Please check my permissions and role order.")

@app_commands.command(name="addrole", description="Create a custom role with options for hoist, mentionable, and all permissions.")
@app_commands.describe(
    name="Name of the role",
    color="Color in hex (e.g. #ff0000)",
    hoist="Display role separately?",
    mentionable="Allow role to be mentionable?",
    all_perms="Give all permissions? (all Discord permissions except admin)"
)
@app_commands.checks.has_permissions(administrator=True, manage_roles=True)
async def addrole(interaction: discord.Interaction, name: str, color: str = None, hoist: bool = False, mentionable: bool = True, all_perms: bool = False):
    guild = interaction.guild
    # Parse color
    try:
        role_color = discord.Color(int(color[1:], 16)) if color else discord.Color.default()
    except Exception:
        await interaction.response.send_message("Invalid color format. Use hex like #ff0000.", ephemeral=True)
        return
    # Permissions
    if all_perms:
        perms = discord.Permissions.all()
        perms.administrator = False
    else:
        perms = discord.Permissions()
    # Check if role already exists
    if discord.utils.get(guild.roles, name=name):
        await interaction.response.send_message(f"Role {name} already exists.", ephemeral=True)
        return
    try:
        role = await guild.create_role(
            name=name,
            color=role_color,
            hoist=hoist,
            mentionable=mentionable,
            permissions=perms,
            reason=f"Created by {interaction.user} using /addrole"
        )
        await interaction.response.send_message(f"Role {role.mention} created successfully!", ephemeral=True)
    except Forbidden:
        await interaction.response.send_message("I do not have permission to create roles. Please check my permissions and role order.", ephemeral=True)

    # Prefix version
    class Mod(commands.Cog):
        # ...existing code...
        @commands.command(name="addrole")
        @commands.has_permissions(administrator=True, manage_roles=True)
        async def addrole_prefix(self, ctx, name: str, color: str = None, hoist: bool = False, mentionable: bool = True, all_perms: bool = False):
            guild = ctx.guild
            try:
                role_color = discord.Color(int(color[1:], 16)) if color else discord.Color.default()
            except Exception:
                await ctx.send("Invalid color format. Use hex like #ff0000.")
                return
            if all_perms:
                perms = discord.Permissions.all()
                perms.administrator = False
            else:
                perms = discord.Permissions()
            if discord.utils.get(guild.roles, name=name):
                await ctx.send(f"Role {name} already exists.")
                return
            try:
                role = await guild.create_role(
                    name=name,
                    color=role_color,
                    hoist=hoist,
                    mentionable=mentionable,
                    permissions=perms,
                    reason=f"Created by {ctx.author} using !addrole"
                )
                await ctx.send(f"Role {role.mention} created successfully!")
            except Forbidden:
                await ctx.send("I do not have permission to create roles. Please check my permissions and role order.")

@app_commands.command(name="addchannel", description="Create a text channel in a specified category.")
@app_commands.describe(
    channel_name="Name of the channel to create",
    category_name="Name of the category to create the channel in"
)
@app_commands.checks.has_permissions(administrator=True, manage_channels=True)
async def addchannel(interaction: discord.Interaction, channel_name: str, category_name: str):
    guild = interaction.guild
    # Find or create the category
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        try:
            category = await guild.create_category(name=category_name, reason=f"Created by {interaction.user} using /addchannel")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to create categories. Please check my permissions.", ephemeral=True)
            return
    # Check if channel already exists in category
    if discord.utils.get(category.channels, name=channel_name):
        await interaction.response.send_message(f"Channel #{channel_name} already exists in {category.name}.", ephemeral=True)
        return
    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            reason=f"Created by {interaction.user} using /addchannel"
        )
        await interaction.response.send_message(f"Channel {channel.mention} created in category {category.name}.", ephemeral=True)
    except Forbidden:
        await interaction.response.send_message("I do not have permission to create channels. Please check my permissions.", ephemeral=True)

@app_commands.command(name="addcategory", description="Create a new category.")
@app_commands.describe(category_name="Name of the category to create")
@app_commands.checks.has_permissions(administrator=True, manage_channels=True)
async def addcategory(interaction: discord.Interaction, category_name: str):
    guild = interaction.guild
    if discord.utils.get(guild.categories, name=category_name):
        await interaction.response.send_message(f"Category '{category_name}' already exists.", ephemeral=True)
        return
    try:
        category = await guild.create_category(name=category_name, reason=f"Created by {interaction.user} using /addcategory")
        await interaction.response.send_message(f"Category '{category.name}' created successfully!", ephemeral=True)
    except Forbidden:
        await interaction.response.send_message("I do not have permission to create categories. Please check my permissions.", ephemeral=True)

    @commands.command(name="addcategory")
    @commands.has_permissions(administrator=True, manage_channels=True)
    async def addcategory_prefix(self, ctx, category_name: str):
        guild = ctx.guild
        if discord.utils.get(guild.categories, name=category_name):
            await ctx.send(f"Category '{category_name}' already exists.")
            return
        try:
            category = await guild.create_category(name=category_name, reason=f"Created by {ctx.author} using !addcategory")
            await ctx.send(f"Category '{category.name}' created successfully!")
        except Forbidden:
            await ctx.send("I do not have permission to create categories. Please check my permissions.")

@app_commands.command(name="addvc", description="Create a voice channel in a specified category.")
@app_commands.describe(
    channel_name="Name of the voice channel to create",
    category_name="Name of the category to create the channel in"
)
@app_commands.checks.has_permissions(administrator=True, manage_channels=True)
async def addvc(interaction: discord.Interaction, channel_name: str, category_name: str):
    guild = interaction.guild
    # Find or create the category
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        try:
            category = await guild.create_category(name=category_name, reason=f"Created by {interaction.user} using /addvc")
        except Forbidden:
            await interaction.response.send_message("I do not have permission to create categories. Please check my permissions.", ephemeral=True)
            return
    # Check if channel already exists in category
    if discord.utils.get(category.channels, name=channel_name):
        await interaction.response.send_message(f"Voice channel '{channel_name}' already exists in {category.name}.", ephemeral=True)
        return
    try:
        channel = await guild.create_voice_channel(
            name=channel_name,
            category=category,
            reason=f"Created by {interaction.user} using /addvc"
        )
        await interaction.response.send_message(f"Voice channel {channel.mention} created in category {category.name}.", ephemeral=True)
    except Forbidden:
        await interaction.response.send_message("I do not have permission to create voice channels. Please check my permissions.", ephemeral=True)

    @commands.command(name="addvc")
    @commands.has_permissions(administrator=True, manage_channels=True)
    async def addvc_prefix(self, ctx, channel_name: str, category_name: str):
        guild = ctx.guild
        category = discord.utils.get(guild.categories, name=category_name)
        if not category:
            try:
                category = await guild.create_category(name=category_name, reason=f"Created by {ctx.author} using !addvc")
            except Forbidden:
                await ctx.send("I do not have permission to create categories. Please check my permissions.")
                return
        if discord.utils.get(category.channels, name=channel_name):
            await ctx.send(f"Voice channel '{channel_name}' already exists in {category.name}.")
            return
        try:
            channel = await guild.create_voice_channel(
                name=channel_name,
                category=category,
                reason=f"Created by {ctx.author} using !addvc"
            )
            await ctx.send(f"Voice channel {channel.mention} created in category {category.name}.")
        except Forbidden:
            await ctx.send("I do not have permission to create voice channels. Please check my permissions.")

@app_commands.command(name="purge_messages", description="Delete all messages in a channel, regardless of age.")
@app_commands.checks.has_permissions(administrator=True, manage_messages=True)
async def purge_messages(interaction: discord.Interaction):
    channel = interaction.channel
    await interaction.response.send_message("Purging all messages in this channel...", ephemeral=True)
    try:
        deleted = 0
        async for message in channel.history(limit=None, oldest_first=True):
            try:
                await message.delete()
                deleted += 1
            except Exception:
                pass  # Ignore errors for messages that can't be deleted
        await interaction.followup.send(f"Purged {deleted} messages from {channel.mention}.", ephemeral=True)
    except Forbidden:
        await interaction.followup.send("I do not have permission to delete messages in this channel.", ephemeral=True)

@app_commands.command(name="slowmode", description="Enable or disable slowmode in this channel.")
@app_commands.describe(
    action="'enable' to set slowmode, 'disable' to turn it off",
    duration="Duration for slowmode",
    unit="Unit for duration (sec, min, hr)"
)
@app_commands.checks.has_permissions(administrator=True, manage_channels=True)
async def slowmode(interaction: discord.Interaction, action: str, duration: int = 0, unit: str = "sec"):
    channel = interaction.channel
    if action.lower() == "enable":
        # Convert duration to seconds
        unit = unit.lower()
        seconds = duration
        if unit.startswith("min"):
            seconds *= 60
        elif unit.startswith("h"):
            seconds *= 3600
        elif unit.startswith("s"):
            pass
        else:
            await interaction.response.send_message("Unit must be one of: sec, min, hr.", ephemeral=True)
            return
        if seconds < 1 or seconds > 21600:
            await interaction.response.send_message("Duration must be between 1 second and 21,600 seconds (6 hours) due to Discord's limit.", ephemeral=True)
            return
        try:
            await channel.edit(slowmode_delay=seconds)
            await interaction.response.send_message(f"Slowmode enabled: {seconds} seconds per message in {channel.mention}.", ephemeral=True)
        except Forbidden:
            await interaction.response.send_message("I do not have permission to set slowmode in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to set slowmode: {e}", ephemeral=True)
    elif action.lower() == "disable":
        try:
            await channel.edit(slowmode_delay=0)
            await interaction.response.send_message(f"Slowmode disabled in {channel.mention}.", ephemeral=True)
        except Forbidden:
            await interaction.response.send_message("I do not have permission to disable slowmode in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to disable slowmode: {e}", ephemeral=True)
    else:
        await interaction.response.send_message("Invalid action. Use 'enable' or 'disable'.", ephemeral=True)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.levels = levels

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)
        key = f"{guild_id}:{user_id}"
        user_data = self.levels.get(key, {"xp": 0, "level": 1})
        # Give random XP per message
        xp_gain = random.randint(5, 15)
        user_data["xp"] += xp_gain
        # Level up logic
        next_level = user_data["level"] + 1
        if next_level <= 10:
            required_xp = next_level * 100
            if user_data["xp"] >= required_xp:
                user_data["level"] = next_level
                # Assign new role, remove old
                guild = message.guild
                member = message.author
                # Remove all level roles
                for lvl, role_name, _, _, _ in LEVEL_ROLE_CONFIG:
                    role = discord.utils.get(guild.roles, name=role_name)
                    if role and role in member.roles:
                        await member.remove_roles(role, reason="Level up")
                # Add new level role
                _, role_name, _, _, _ = LEVEL_ROLE_CONFIG[next_level-1]
                role = discord.utils.get(guild.roles, name=role_name)
                if role:
                    await member.add_roles(role, reason="Level up reward")
                try:
                    await member.send(f"Congrats! You reached level {next_level} and received the role: {role_name}!")
                except Exception:
                    pass
        self.levels[key] = user_data
        save_levels(self.levels)

    @app_commands.command(name="level", description="Check your level and XP.")
    async def level_slash(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = str(interaction.guild.id)
        key = f"{guild_id}:{user_id}"
        user_data = self.levels.get(key, {"xp": 0, "level": 1})
        await interaction.response.send_message(f"Level: {user_data['level']} | XP: {user_data['xp']}", ephemeral=True)

@app_commands.command(name="setuplevel", description="Setup the level system and roles.")
@app_commands.checks.has_permissions(administrator=True, manage_roles=True)
async def setuplevel(interaction: discord.Interaction):
    guild = interaction.guild
    await interaction.response.defer(ephemeral=True)
    # Remove/modify existing level roles to avoid clashes
    for lvl, role_name, _, _, _ in LEVEL_ROLE_CONFIG:
        role = discord.utils.get(guild.roles, name=role_name)
        if role:
            await role.delete(reason="Recreating level roles for setup.")
    # Create level roles
    created_roles = []
    for lvl, role_name, perms, color, hoist in LEVEL_ROLE_CONFIG:
        role = await guild.create_role(
            name=role_name,
            permissions=perms,
            color=color,
            mentionable=True,
            hoist=hoist,
            reason="Level system setup"
        )
        created_roles.append(role)

    # Reorder level roles: Level 10 (top) to Level 1 (bottom), just above @everyone
    # Get the @everyone role position
    everyone_role = guild.default_role
    # Sort created_roles by level descending (Level 10 first)
    sorted_roles = sorted(created_roles, key=lambda r: int(r.name.split()[-1]), reverse=True)
    # Build new positions: place each level role just above @everyone, in order
    # Get current role positions
    role_positions = {role: role.position for role in guild.roles}
    # Start from @everyone's position + 1
    new_position = everyone_role.position + 1
    for role in reversed(sorted_roles):  # Level 1 at bottom, Level 10 at top
        await role.edit(position=new_position)
        new_position += 1

    await interaction.followup.send("Level system and roles set up! Users will now gain XP and level up by being active.\nLevel roles are now arranged sensibly above @everyone.", ephemeral=True)

@app_commands.command(name="setusrlvl", description="Set a user's level (admin only)")
@app_commands.describe(user="User to set level for", level="Level to set (1-10)")
@app_commands.checks.has_permissions(administrator=True, manage_roles=True)
async def setusrlvl(interaction: discord.Interaction, user: discord.Member, level: int):
    if level < 1 or level > 10:
        await interaction.response.send_message("Level must be between 1 and 10.", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)
    user_id = str(user.id)
    key = f"{guild_id}:{user_id}"
    user_data = levels.get(key, {"xp": 0, "level": 1})
    user_data["level"] = level
    # Remove all level roles
    for lvl, role_name, _, _, _ in LEVEL_ROLE_CONFIG:
        role = discord.utils.get(interaction.guild.roles, name=role_name)
        if role and role in user.roles:
            await user.remove_roles(role, reason="Level set by admin")
    # Add new level role
    _, role_name, _, _, _ = LEVEL_ROLE_CONFIG[level-1]
    role = discord.utils.get(interaction.guild.roles, name=role_name)
    if role:
        await user.add_roles(role, reason="Level set by admin")
    levels[key] = user_data
    save_levels(levels)
    await interaction.response.send_message(f"Set {user.mention}'s level to {level} and updated roles.", ephemeral=True)

async def setup_economy(bot):
    await bot.add_cog(Economy(bot))

class BlueMoonBot(commands.Bot):
    async def setup_hook(self):
        await self.add_cog(Mod(self))
        await setup_economy(self)
        self.tree.add_command(appeal)
        self.tree.add_command(approveappeal)
        self.tree.add_command(rejectappeal)
        self.tree.add_command(assignrole_slash)
        self.tree.add_command(addrolefromtemplate)
        self.tree.add_command(addrole)
        self.tree.add_command(addchannel)
        self.tree.add_command(addcategory)
        self.tree.add_command(addvc)
        self.tree.add_command(purge_messages)
        self.tree.add_command(slowmode)
        self.tree.add_command(setuplevel)
        self.tree.add_command(setusrlvl)
        self.tree.add_command(roleinfo)
        self.tree.add_command(lvlprogress)
        # Do NOT add Economy.level_slash again, already registered by decorator
        await self.tree.sync()
        print(f"Synced slash commands globally (including DMs, assignrole, addrolefromtemplate, addrole, addchannel, addcategory, addvc, purge_messages, slowmode, setuplevel, setusrlvl, roleinfo, lvlprogress, and level).")

bot = BlueMoonBot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(DISCORD_TOKEN)