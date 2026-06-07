"""Voice tools — join/leave a voice channel and speak with the Butcher voice.

These shim into the VoiceAI cog's agent helpers (added in the voice rework).
They degrade gracefully if those helpers aren't present yet.
"""
from __future__ import annotations

from .registry import tool


def _voice(ctx):
    return ctx.client.get_cog("VoiceAI") if ctx.client else None


def _member(ctx):
    user = ctx.user
    if user is None or ctx.guild is None:
        return None
    if hasattr(user, "voice"):
        return user
    return ctx.guild.get_member(getattr(user, "id", 0))


@tool("join_voice", "Join the user's voice channel.",
      {"type": "object", "properties": {}})
async def join_voice(ctx):
    cog = _voice(ctx)
    if cog is None or not hasattr(cog, "agent_join"):
        return "Voice isn't available right now."
    if ctx.guild is None:
        return "Voice only works inside a server."
    return await cog.agent_join(ctx.guild, _member(ctx))


@tool("leave_voice", "Leave the current voice channel.",
      {"type": "object", "properties": {}})
async def leave_voice(ctx):
    cog = _voice(ctx)
    if cog is None or not hasattr(cog, "agent_leave"):
        return "Voice isn't available right now."
    return await cog.agent_leave(ctx.guild)


@tool("speak", "Say something out loud in the voice channel.",
      {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]})
async def speak(ctx, text):
    cog = _voice(ctx)
    if cog is None or not hasattr(cog, "agent_speak"):
        return "I'm not able to speak in voice right now."
    return await cog.agent_speak(ctx.guild, text)
