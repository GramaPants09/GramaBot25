"""Music tools — shim into the Music cog's agent-facing helpers."""
from __future__ import annotations

from .registry import tool


def _music(ctx):
    return ctx.client.get_cog("Music") if ctx.client else None


def _member(ctx):
    """The speaking user as a guild Member (so we can find their voice channel)."""
    user = ctx.user
    if user is None or ctx.guild is None:
        return None
    if hasattr(user, "voice"):
        return user
    return ctx.guild.get_member(getattr(user, "id", 0))


@tool("play_music", "Play a song in the user's voice channel. Accepts a search query, "
      "a YouTube link, or a Spotify track/album/playlist link.",
      {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]})
async def play_music(ctx, query):
    cog = _music(ctx)
    if cog is None:
        return "Music system isn't loaded."
    if ctx.guild is None:
        return "Music only works inside a server."
    return await cog.agent_play(ctx.guild, _member(ctx), ctx.channel, query)


@tool("skip_music", "Skip the current song.",
      {"type": "object", "properties": {}})
async def skip_music(ctx):
    cog = _music(ctx)
    return await cog.agent_control(ctx.guild, "skip") if cog else "Music isn't loaded."


@tool("pause_music", "Pause playback.", {"type": "object", "properties": {}})
async def pause_music(ctx):
    cog = _music(ctx)
    return await cog.agent_control(ctx.guild, "pause") if cog else "Music isn't loaded."


@tool("resume_music", "Resume playback.", {"type": "object", "properties": {}})
async def resume_music(ctx):
    cog = _music(ctx)
    return await cog.agent_control(ctx.guild, "resume") if cog else "Music isn't loaded."


@tool("stop_music", "Stop playback, clear the queue, and leave the voice channel.",
      {"type": "object", "properties": {}})
async def stop_music(ctx):
    cog = _music(ctx)
    return await cog.agent_control(ctx.guild, "stop") if cog else "Music isn't loaded."


@tool("queue_status", "Show what's queued up.", {"type": "object", "properties": {}})
async def queue_status(ctx):
    cog = _music(ctx)
    return cog.agent_queue_text(ctx.guild) if cog else "Music isn't loaded."
