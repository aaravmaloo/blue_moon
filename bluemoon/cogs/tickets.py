from __future__ import annotations

import asyncio
import io
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks


class TicketTypeButton(discord.ui.Button):
    def __init__(self, ticket_type: str, label: str, style: discord.ButtonStyle):
        super().__init__(label=label, style=style, custom_id=f"bluemoon:ticket:create:{ticket_type}")
        self.ticket_type = ticket_type

    async def callback(self, interaction: discord.Interaction) -> None:
        cog: TicketsCog = interaction.client.get_cog("TicketsCog")
        if cog:
            await cog.create_ticket_from_button(interaction, self.ticket_type)


class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeButton("support", "Support", discord.ButtonStyle.primary))
        self.add_item(TicketTypeButton("report", "Report", discord.ButtonStyle.danger))
        self.add_item(TicketTypeButton("appeal", "Appeal", discord.ButtonStyle.secondary))


class TicketActionsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketActionButton("assign", "Assign", discord.ButtonStyle.primary))
        self.add_item(TicketActionButton("close", "Close", discord.ButtonStyle.danger))


class TicketActionButton(discord.ui.Button):
    def __init__(self, action: str, label: str, style: discord.ButtonStyle):
        super().__init__(label=label, style=style, custom_id=f"bluemoon:ticket:action:{action}")
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        cog: TicketsCog = interaction.client.get_cog("TicketsCog")
        if cog:
            if self.action == "assign":
                await cog.assign_ticket(interaction, interaction.user)
            elif self.action == "close":
                await cog.close_ticket(interaction, "Closed from button")


class TicketsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.sla_checker.start()
        self.auto_close_checker.start()

    async def cog_load(self) -> None:
        self.bot.add_view(TicketPanelView())
        self.bot.add_view(TicketActionsView())

    def cog_unload(self) -> None:
        self.sla_checker.cancel()
        self.auto_close_checker.cancel()

    async def _is_staff(self, member: discord.Member) -> bool:
        if member.guild_permissions.manage_guild:
            return True
        staff_role_id = await self.bot.db.get_setting(member.guild.id, "staff_role_id")
        return bool(staff_role_id and any(r.id == int(staff_role_id) for r in member.roles))

    async def create_ticket_from_button(self, interaction: discord.Interaction, ticket_type: str) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message("Guild only.", ephemeral=True)
            return

        existing = await self.bot.db.fetchone(
            "SELECT * FROM tickets WHERE guild_id = ? AND opener_id = ? AND status = 'open'",
            (guild.id, interaction.user.id),
        )
        if existing:
            ch = guild.get_channel(existing["channel_id"])
            await interaction.response.send_message(
                f"You already have an open ticket: {ch.mention if ch else '#deleted-channel'}",
                ephemeral=True,
            )
            return

        category_id = await self.bot.db.get_setting(guild.id, "ticket_category_id")
        category = guild.get_channel(int(category_id)) if category_id else None
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }

        staff_role_id = await self.bot.db.get_setting(guild.id, "staff_role_id")
        if staff_role_id:
            staff_role = guild.get_role(int(staff_role_id))
            if staff_role:
                overwrites[staff_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel = await guild.create_text_channel(
            name=f"{ticket_type}-{interaction.user.name}"[:95],
            category=category if isinstance(category, discord.CategoryChannel) else None,
            overwrites=overwrites,
            reason=f"Ticket {ticket_type}",
        )
        await self.bot.db.execute(
            "INSERT INTO tickets (guild_id, channel_id, opener_id, ticket_type, status, created_at) VALUES (?, ?, ?, ?, 'open', ?)",
            (guild.id, channel.id, interaction.user.id, ticket_type, int(time.time())),
        )
        await channel.send(
            f"Ticket opened by {interaction.user.mention} ({ticket_type}).",
            view=TicketActionsView(),
        )
        await interaction.response.send_message(f"Ticket created: {channel.mention}", ephemeral=True)

    async def assign_ticket(self, interaction: discord.Interaction, staff_member: discord.Member) -> None:
        if not await self._is_staff(interaction.user):
            await interaction.response.send_message("Staff only action.", ephemeral=True)
            return
        row = await self.bot.db.fetchone(
            "SELECT * FROM tickets WHERE guild_id = ? AND channel_id = ? AND status = 'open'",
            (interaction.guild.id, interaction.channel.id),
        )
        if not row:
            await interaction.response.send_message("This channel is not an active ticket.", ephemeral=True)
            return
        await self.bot.db.execute(
            "UPDATE tickets SET assigned_staff_id = ? WHERE id = ?",
            (staff_member.id, row["id"]),
        )
        await interaction.response.send_message(f"Assigned to {staff_member.mention}.")

    async def close_ticket(self, interaction: discord.Interaction, reason: str) -> None:
        if not await self._is_staff(interaction.user):
            await interaction.response.send_message("Staff only action.", ephemeral=True)
            return
        row = await self.bot.db.fetchone(
            "SELECT * FROM tickets WHERE guild_id = ? AND channel_id = ? AND status = 'open'",
            (interaction.guild.id, interaction.channel.id),
        )
        if not row:
            await interaction.response.send_message("No open ticket found in this channel.", ephemeral=True)
            return

        await self.bot.db.execute(
            "UPDATE tickets SET status = 'closed', closed_at = ? WHERE id = ?",
            (int(time.time()), row["id"]),
        )

        transcript_channel_id = await self.bot.db.get_setting(interaction.guild.id, "ticket_transcript_channel")
        transcript_ch = interaction.guild.get_channel(int(transcript_channel_id)) if transcript_channel_id else None

        transcript_lines: list[str] = []
        async for msg in interaction.channel.history(limit=200, oldest_first=True):
            transcript_lines.append(f"[{msg.created_at.isoformat()}] {msg.author}: {msg.content}")
        transcript_data = "\n".join(transcript_lines).encode("utf-8")

        if isinstance(transcript_ch, discord.TextChannel):
            file_obj = discord.File(io.BytesIO(transcript_data), filename=f"ticket-{interaction.channel.id}.txt")
            await transcript_ch.send(
                f"Transcript for {interaction.channel.mention} closed by {interaction.user.mention}. Reason: {reason}",
                file=file_obj,
            )

        await interaction.response.send_message("Ticket closed. Channel will delete in 5 seconds.")
        await interaction.channel.send("Please rate support with `/ticket feedback 1-5` before close if needed.")
        await asyncio.sleep(5)
        await interaction.channel.delete(reason="Ticket closed")

    ticket = app_commands.Group(name="ticket", description="Tickets and support")

    @ticket.command(name="panel", description="Create a ticket panel")
    async def panel(self, interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Manage Channels required.", ephemeral=True)
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.response.send_message("Target must be text channel.", ephemeral=True)
            return
        await target.send("Create a ticket:", view=TicketPanelView())
        await interaction.response.send_message("Ticket panel created.", ephemeral=True)

    @ticket.command(name="set-category", description="Set ticket category")
    async def set_category(self, interaction: discord.Interaction, category: discord.CategoryChannel) -> None:
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Manage Channels required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "ticket_category_id", category.id)
        await interaction.response.send_message(f"Ticket category set to {category.name}")

    @ticket.command(name="set-transcripts", description="Set transcript export channel")
    async def set_transcripts(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Manage Channels required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "ticket_transcript_channel", channel.id)
        await interaction.response.send_message(f"Transcript channel set: {channel.mention}")

    @ticket.command(name="set-feedback", description="Set ticket feedback channel")
    async def set_feedback(self, interaction: discord.Interaction, channel: discord.TextChannel) -> None:
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("Manage Channels required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "ticket_feedback_channel", channel.id)
        await interaction.response.send_message(f"Feedback channel set: {channel.mention}")

    @ticket.command(name="assign", description="Assign current ticket")
    async def assign(self, interaction: discord.Interaction, staff: discord.Member | None = None) -> None:
        await self.assign_ticket(interaction, staff or interaction.user)

    @ticket.command(name="close", description="Close current ticket")
    async def close(self, interaction: discord.Interaction, reason: str = "No reason") -> None:
        await self.close_ticket(interaction, reason)

    @ticket.command(name="transcript", description="Export transcript without closing")
    async def transcript(self, interaction: discord.Interaction) -> None:
        if not await self._is_staff(interaction.user):
            await interaction.response.send_message("Staff only.", ephemeral=True)
            return
        transcript_lines: list[str] = []
        async for msg in interaction.channel.history(limit=200, oldest_first=True):
            transcript_lines.append(f"[{msg.created_at.isoformat()}] {msg.author}: {msg.content}")
        data = "\n".join(transcript_lines).encode("utf-8")
        file_obj = discord.File(io.BytesIO(data), filename=f"transcript-{interaction.channel.id}.txt")
        await interaction.response.send_message("Transcript export:", file=file_obj)

    @ticket.command(name="feedback", description="Rate support 1-5")
    async def feedback(self, interaction: discord.Interaction, stars: app_commands.Range[int, 1, 5], comments: str = "") -> None:
        feedback_channel_id = await self.bot.db.get_setting(interaction.guild_id, "ticket_feedback_channel")
        if not feedback_channel_id:
            await interaction.response.send_message("Feedback channel not configured.", ephemeral=True)
            return
        channel = interaction.guild.get_channel(int(feedback_channel_id))
        if not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("Feedback channel missing.", ephemeral=True)
            return
        await channel.send(f"Feedback from {interaction.user.mention}: {stars}/5\n{comments}")
        await interaction.response.send_message("Feedback submitted.", ephemeral=True)

    @ticket.command(name="sla", description="Set SLA threshold in minutes")
    async def sla(self, interaction: discord.Interaction, minutes: int) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "ticket_sla_minutes", max(1, minutes))
        await interaction.response.send_message(f"SLA set to {minutes} minutes.")

    @tasks.loop(minutes=2)
    async def sla_checker(self) -> None:
        await self.bot.wait_until_ready()
        now = int(time.time())
        rows = await self.bot.db.fetchall("SELECT * FROM tickets WHERE status = 'open' AND assigned_staff_id IS NULL")
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if not guild:
                continue
            sla_minutes = int(await self.bot.db.get_setting(guild.id, "ticket_sla_minutes") or 60)
            if now - int(row["created_at"]) < sla_minutes * 60:
                continue
            channel = guild.get_channel(row["channel_id"])
            if not isinstance(channel, discord.TextChannel):
                continue
            staff_role_id = await self.bot.db.get_setting(guild.id, "staff_role_id")
            ping = f"<@&{staff_role_id}>" if staff_role_id else "Staff"
            await channel.send(f"{ping} SLA warning: this ticket is waiting for assignment.")

    @tasks.loop(minutes=5)
    async def auto_close_checker(self) -> None:
        await self.bot.wait_until_ready()
        rows = await self.bot.db.fetchall("SELECT * FROM tickets WHERE status = 'open'")
        now = time.time()
        for row in rows:
            guild = self.bot.get_guild(row["guild_id"])
            if not guild:
                continue
            ch = guild.get_channel(row["channel_id"])
            if not isinstance(ch, discord.TextChannel):
                continue
            last = None
            async for msg in ch.history(limit=1):
                last = msg
            if not last:
                continue
            idle_hours = (now - last.created_at.timestamp()) / 3600
            if idle_hours >= 72:
                try:
                    await ch.send("Auto-closing due to 72h inactivity.")
                    await self.bot.db.execute(
                        "UPDATE tickets SET status='closed', closed_at=? WHERE id = ?",
                        (int(time.time()), row["id"]),
                    )
                    await ch.delete(reason="Auto-close inactive ticket")
                except discord.HTTPException:
                    pass


async def setup(bot: commands.Bot) -> None:
    cog = TicketsCog(bot)
    await bot.add_cog(cog)
