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

class BlueMoonBot(commands.Bot):
    async def setup_hook(self):
        await self.add_cog(Mod(self))
        # Register appeal commands globally (so they work in DMs)
        self.tree.add_command(appeal)
        self.tree.add_command(approveappeal)
        self.tree.add_command(rejectappeal)
        self.tree.add_command(assignrole_slash)
        self.tree.add_command(addrolefromtemplate)
        self.tree.add_command(addrole)
        # Sync global commands
        await self.tree.sync()
        print(f"Synced slash commands globally (including DMs, assignrole, addrolefromtemplate, and addrole).")

bot = BlueMoonBot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

bot.run(DISCORD_TOKEN)