from __future__ import annotations

import asyncio
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp


YDL_OPTS = {
    "format": "bestaudio/best",
    "quiet": True,
    "default_search": "ytsearch",
    "noplaylist": True,
}


@dataclass
class Track:
    title: str
    stream_url: str
    page_url: str
    requested_by: int


@dataclass
class GuildMusicState:
    queue: deque[Track] = field(default_factory=deque)
    now_playing: Track | None = None
    loop: bool = False
    volume: float = 0.5
    stay_247: bool = False


class MusicCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.states: dict[int, GuildMusicState] = {}

    def _state(self, guild_id: int) -> GuildMusicState:
        if guild_id not in self.states:
            self.states[guild_id] = GuildMusicState()
        return self.states[guild_id]

    async def _has_dj_access(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            return False
        if interaction.user.guild_permissions.manage_guild:
            return True
        role_id = await self.bot.db.get_setting(interaction.guild_id, "dj_role_id")
        if not role_id:
            return True
        return any(r.id == int(role_id) for r in interaction.user.roles)

    async def _extract_track(self, query: str, requester_id: int) -> Track | None:
        if "open.spotify.com" in query:
            raise ValueError("Spotify direct playback is not supported yet. Use a song name or YouTube URL.")
        data = await asyncio.to_thread(lambda: yt_dlp.YoutubeDL(YDL_OPTS).extract_info(query, download=False))
        if not data:
            return None
        if "entries" in data and data["entries"]:
            data = data["entries"][0]
        return Track(
            title=data.get("title", "Unknown title"),
            stream_url=data["url"],
            page_url=data.get("webpage_url", query),
            requested_by=requester_id,
        )

    async def _ensure_voice(self, interaction: discord.Interaction) -> discord.VoiceClient | None:
        if not isinstance(interaction.user, discord.Member) or not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.response.send_message("Join a voice channel first.", ephemeral=True)
            return None
        voice = interaction.guild.voice_client
        if voice and voice.channel != interaction.user.voice.channel:
            await voice.move_to(interaction.user.voice.channel)
            return voice
        if not voice:
            voice = await interaction.user.voice.channel.connect()
        return voice

    async def _play_next(self, guild: discord.Guild) -> None:
        voice = guild.voice_client
        if not voice or voice.is_playing():
            return
        state = self._state(guild.id)

        if state.loop and state.now_playing:
            track = state.now_playing
        elif state.queue:
            track = state.queue.popleft()
            state.now_playing = track
        else:
            state.now_playing = None
            if not state.stay_247:
                try:
                    await voice.disconnect()
                except discord.HTTPException:
                    pass
            return

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(
                track.stream_url,
                before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                options="-vn",
            ),
            volume=state.volume,
        )

        def after_play(err: Exception | None) -> None:
            if err:
                print(f"Playback error: {err}")
            self.bot.loop.create_task(self._play_next(guild))

        voice.play(source, after=after_play)

        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(f"Now playing: **{track.title}**")
                break

    music = app_commands.Group(name="music", description="Music playback")

    @music.command(name="play", description="Play from YouTube or query")
    async def play(self, interaction: discord.Interaction, query: str) -> None:
        voice = await self._ensure_voice(interaction)
        if not voice:
            return

        await interaction.response.defer(thinking=True)
        try:
            track = await self._extract_track(query, interaction.user.id)
        except Exception as exc:
            await interaction.followup.send(f"Playback lookup failed: {exc}")
            return

        if not track:
            await interaction.followup.send("Could not find a playable track.")
            return

        state = self._state(interaction.guild_id)
        state.queue.append(track)
        await interaction.followup.send(f"Queued: **{track.title}**")
        if not voice.is_playing():
            await self._play_next(interaction.guild)

    @music.command(name="pause", description="Pause playback")
    async def pause(self, interaction: discord.Interaction) -> None:
        if not await self._has_dj_access(interaction):
            await interaction.response.send_message("DJ role required.", ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if not voice or not voice.is_playing():
            await interaction.response.send_message("Nothing is playing.", ephemeral=True)
            return
        voice.pause()
        await interaction.response.send_message("Paused.")

    @music.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction) -> None:
        if not await self._has_dj_access(interaction):
            await interaction.response.send_message("DJ role required.", ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if not voice or not voice.is_paused():
            await interaction.response.send_message("Nothing paused.", ephemeral=True)
            return
        voice.resume()
        await interaction.response.send_message("Resumed.")

    @music.command(name="skip", description="Skip current track")
    async def skip(self, interaction: discord.Interaction) -> None:
        if not await self._has_dj_access(interaction):
            await interaction.response.send_message("DJ role required.", ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if not voice or not voice.is_playing():
            await interaction.response.send_message("Nothing to skip.", ephemeral=True)
            return
        voice.stop()
        await interaction.response.send_message("Skipped.")

    @music.command(name="queue", description="Show current queue")
    async def queue(self, interaction: discord.Interaction) -> None:
        state = self._state(interaction.guild_id)
        if not state.now_playing and not state.queue:
            await interaction.response.send_message("Queue is empty.")
            return
        lines = []
        if state.now_playing:
            lines.append(f"Now: {state.now_playing.title}")
        for i, t in enumerate(list(state.queue)[:10], start=1):
            lines.append(f"{i}. {t.title}")
        await interaction.response.send_message("\n".join(lines))

    @music.command(name="loop", description="Toggle loop for current song")
    async def loop(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not await self._has_dj_access(interaction):
            await interaction.response.send_message("DJ role required.", ephemeral=True)
            return
        state = self._state(interaction.guild_id)
        state.loop = enabled
        await interaction.response.send_message(f"Loop set to {enabled}.")

    @music.command(name="volume", description="Set volume 0-150")
    async def volume(self, interaction: discord.Interaction, percent: int) -> None:
        if not await self._has_dj_access(interaction):
            await interaction.response.send_message("DJ role required.", ephemeral=True)
            return
        state = self._state(interaction.guild_id)
        percent = max(0, min(150, percent))
        state.volume = percent / 100
        voice = interaction.guild.voice_client
        if voice and voice.source and isinstance(voice.source, discord.PCMVolumeTransformer):
            voice.source.volume = state.volume
        await interaction.response.send_message(f"Volume set to {percent}%")

    @music.command(name="disconnect", description="Disconnect from voice")
    async def disconnect(self, interaction: discord.Interaction) -> None:
        if not await self._has_dj_access(interaction):
            await interaction.response.send_message("DJ role required.", ephemeral=True)
            return
        voice = interaction.guild.voice_client
        if not voice:
            await interaction.response.send_message("Not connected.", ephemeral=True)
            return
        await voice.disconnect()
        self._state(interaction.guild_id).queue.clear()
        await interaction.response.send_message("Disconnected.")

    @music.command(name="247", description="Toggle 24/7 mode")
    async def mode_247(self, interaction: discord.Interaction, enabled: bool) -> None:
        if not await self._has_dj_access(interaction):
            await interaction.response.send_message("DJ role required.", ephemeral=True)
            return
        self._state(interaction.guild_id).stay_247 = enabled
        await interaction.response.send_message(f"24/7 mode set to {enabled}")

    @music.command(name="set-dj-role", description="Set DJ role")
    async def set_dj_role(self, interaction: discord.Interaction, role: discord.Role) -> None:
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message("Manage Guild required.", ephemeral=True)
            return
        await self.bot.db.set_setting(interaction.guild_id, "dj_role_id", role.id)
        await interaction.response.send_message(f"DJ role set to {role.mention}")

    @music.command(name="lyrics", description="Fetch lyrics for current track (best effort)")
    async def lyrics(self, interaction: discord.Interaction) -> None:
        state = self._state(interaction.guild_id)
        if not state.now_playing:
            await interaction.response.send_message("Nothing playing.", ephemeral=True)
            return

        title = state.now_playing.title
        parts = re.split(r"[-|]", title, maxsplit=1)
        if len(parts) < 2:
            await interaction.response.send_message("Could not parse artist/title from current track.")
            return
        artist = parts[0].strip()
        song = parts[1].strip()

        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.lyrics.ovh/v1/{artist}/{song}") as resp:
                if resp.status != 200:
                    await interaction.response.send_message("Lyrics not found.")
                    return
                data = await resp.json()

        lyrics_text = data.get("lyrics", "No lyrics returned.")
        await interaction.response.send_message(f"Lyrics for **{title}**:\n{lyrics_text[:1800]}")


async def setup(bot: commands.Bot) -> None:
    cog = MusicCog(bot)
    await bot.add_cog(cog)
