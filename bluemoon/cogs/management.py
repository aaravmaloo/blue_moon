from __future__ import annotations

import json

import discord
from discord import app_commands
from discord.ext import commands, tasks


class RoleButtonView(discord.ui.View):
    def __init__(self, role_id: int, label: str, style: discord.ButtonStyle = discord.ButtonStyle.primary):
        super().__init__(timeout=None)
        self.add_item(RoleButton(role_id=role_id, label=label, style=style))


class RoleButton(discord.ui.Button):
    def __init__(self, role_id: int, label: str, style: discord.ButtonStyle = discord.ButtonStyle.primary):
        super().__init__(label=label, style=style, custom_id=f"bluemoon:role:{role_id}")
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("Guild only.", ephemeral=True)
            return
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("Role not found.", ephemeral=True)
            return
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role, reason="Button role toggle")
            await interaction.response.send_message(f"Removed {role.mention}", ephemeral=True)
        else:
            await interaction.user.add_roles(role, reason="Button role toggle")
            await interaction.response.send_message(f"Added {role.mention}", ephemeral=True)


class ManagementCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.stats_updater.start()

    def cog_unload(self) -> None:
        self.stats_updater.cancel()

    async def _is_staff(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        if interaction.user.guild_permissions.manage_guild:
            return True
        staff_role_id = await self.bot.db.get_setting(interaction.guild_id, "staff_role_id")
        return bool(staff_role_id and any(r.id == int(staff_role_id) for r in interaction.user.roles))

    async def _require_staff(self, interaction: discord.Interaction) -> bool:
        ok = await self._is_staff(interaction)
        if not ok:
            await interaction.response.send_message("Manage server permission required.", ephemeral=True)
        return ok

    manage = app_commands.Group(name="manage", description="Server management")

    @manage.command(name="welcome", description="Set welcome channel")
    async def welcome(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.set_setting(interaction.guild_id, "welcome_channel_id", channel.id)
        await interaction.response.send_message(f"Welcome channel set: {channel.mention}")

    @manage.command(name="goodbye", description="Set goodbye channel")
    async def goodbye(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.set_setting(interaction.guild_id, "goodbye_channel_id", channel.id)
        await interaction.response.send_message(f"Goodbye channel set: {channel.mention}")

    @manage.command(name="autorole", description="Set auto-role on join")
    async def autorole(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.set_setting(interaction.guild_id, "autorole_id", role.id)
        await interaction.response.send_message(f"Autorole set to {role.mention}")

    @manage.command(name="role-panel", description="Create a button role panel")
    async def role_panel(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        label: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if not await self._require_staff(interaction):
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Must target a text channel.", ephemeral=True)
            return
        view = RoleButtonView(role_id=role.id, label=label)
        msg = await target.send(f"Click to toggle {role.mention}", view=view)
        await self.bot.db.execute(
            "INSERT INTO role_buttons (guild_id, message_id, label, role_id, style) VALUES (?, ?, ?, ?, ?)",
            (interaction.guild_id, msg.id, label, role.id, int(discord.ButtonStyle.primary.value)),
        )
        await interaction.response.send_message("Role panel created.", ephemeral=True)

    @manage.command(name="reaction-role", description="Reaction roles (uses button panel under the hood)")
    async def reaction_role(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        label: str,
        channel: discord.TextChannel | None = None,
    ) -> None:
        await self.role_panel(interaction, role, label, channel)

    @manage.command(name="clone-channel", description="Clone a text channel")
    async def clone_channel(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        if not await self._require_staff(interaction):
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Use a text channel.", ephemeral=True)
            return
        clone = await target.clone(reason=f"Cloned by {interaction.user}")
        await interaction.response.send_message(f"Cloned channel: {clone.mention}")

    @manage.command(name="mass-role", description="Mass add/remove role from members")
    @app_commands.describe(mode="add or remove")
    async def mass_role(self, interaction: discord.Interaction, role: discord.Role, mode: str) -> None:
        if not await self._require_staff(interaction):
            return
        mode = mode.lower().strip()
        if mode not in {"add", "remove"}:
            await interaction.response.send_message("Mode must be add/remove.", ephemeral=True)
            return
        await interaction.response.defer(thinking=True)
        count = 0
        for member in interaction.guild.members:
            if member.bot:
                continue
            try:
                if mode == "add" and role not in member.roles:
                    await member.add_roles(role, reason=f"Mass role by {interaction.user}")
                    count += 1
                elif mode == "remove" and role in member.roles:
                    await member.remove_roles(role, reason=f"Mass role by {interaction.user}")
                    count += 1
            except discord.HTTPException:
                continue
        await interaction.followup.send(f"Mass role `{mode}` complete. Updated {count} members.")

    @manage.command(name="auto-thread", description="Set channel for auto-thread creation")
    async def auto_thread(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        if not await self._require_staff(interaction):
            return
        if channel is None:
            await self.bot.db.set_setting(interaction.guild_id, "auto_thread_channel_id", None)
            await interaction.response.send_message("Auto-thread disabled.")
            return
        await self.bot.db.set_setting(interaction.guild_id, "auto_thread_channel_id", channel.id)
        await interaction.response.send_message(f"Auto-thread channel set to {channel.mention}")

    @manage.command(name="stats-channel", description="Set member stats voice channel")
    async def stats_channel(self, interaction: discord.Interaction, channel: discord.VoiceChannel) -> None:
        if not await self._require_staff(interaction):
            return
        await self.bot.db.set_setting(interaction.guild_id, "stats_channel_id", channel.id)
        await interaction.response.send_message(f"Stats channel set to {channel.mention}")

    @manage.command(name="backup-create", description="Create server backup snapshot")
    async def backup_create(self, interaction: discord.Interaction) -> None:
        if not await self._require_staff(interaction):
            return
        data = {
            "roles": [{"name": r.name, "permissions": r.permissions.value, "color": r.color.value} for r in interaction.guild.roles if not r.is_default()],
            "channels": [{"name": c.name, "type": str(c.type), "category": c.category.name if c.category else None} for c in interaction.guild.channels],
        }
        await self.bot.db.execute(
            "INSERT INTO analytics_events (guild_id, actor_id, event_type, payload, created_at) VALUES (?, ?, ?, ?, strftime('%s','now'))",
            (interaction.guild_id, interaction.user.id, "server_backup", json.dumps(data)),
        )
        await interaction.response.send_message("Server backup snapshot saved.")

    @manage.command(name="backup-restore", description="Restore latest backup channels")
    async def backup_restore(self, interaction: discord.Interaction) -> None:
        if not await self._require_staff(interaction):
            return
        row = await self.bot.db.fetchone(
            "SELECT payload FROM analytics_events WHERE guild_id = ? AND event_type = 'server_backup' ORDER BY id DESC LIMIT 1",
            (interaction.guild_id,),
        )
        if not row:
            await interaction.response.send_message("No backup found.", ephemeral=True)
            return
        data = json.loads(row["payload"])
        await interaction.response.defer(thinking=True)
        categories: dict[str, discord.CategoryChannel] = {}
        for ch in data.get("channels", []):
            if ch.get("type") != "category" or ch["name"] in categories:
                continue
            categories[ch["name"]] = await interaction.guild.create_category(ch["name"], reason="Backup restore")

        for ch in data.get("channels", []):
            if ch.get("type") != "text":
                continue
            category = categories.get(ch.get("category"))
            await interaction.guild.create_text_channel(ch["name"], category=category, reason="Backup restore")

        await interaction.followup.send("Backup restore created channels from latest snapshot.")

    @manage.command(name="template-export", description="Export bot settings template")
    async def template_export(self, interaction: discord.Interaction) -> None:
        if not await self._require_staff(interaction):
            return
        rows = await self.bot.db.fetchall("SELECT key, value FROM guild_settings WHERE guild_id = ?", (interaction.guild_id,))
        payload = {r["key"]: json.loads(r["value"]) for r in rows}
        content = "```json\n" + json.dumps(payload, indent=2)[:3800] + "\n```"
        await interaction.response.send_message(content)

    @manage.command(name="template-import", description="Import bot settings template from JSON")
    async def template_import(self, interaction: discord.Interaction, raw_json: str) -> None:
        if not await self._require_staff(interaction):
            return
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            await interaction.response.send_message("Invalid JSON.", ephemeral=True)
            return
        for key, value in data.items():
            await self.bot.db.set_setting(interaction.guild_id, key, value)
        await interaction.response.send_message(f"Imported {len(data)} settings keys.")

    @tasks.loop(minutes=5)
    async def stats_updater(self) -> None:
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            channel_id = await self.bot.db.get_setting(guild.id, "stats_channel_id")
            if not channel_id:
                continue
            channel = guild.get_channel(int(channel_id))
            if isinstance(channel, discord.VoiceChannel):
                try:
                    await channel.edit(name=f"Members: {guild.member_count}")
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot) -> None:
    cog = ManagementCog(bot)
    await bot.add_cog(cog)
