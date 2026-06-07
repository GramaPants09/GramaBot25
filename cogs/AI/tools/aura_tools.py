"""Aura (economy) tools — read and adjust users' aura scores."""
from __future__ import annotations

from .registry import tool
from ._helpers import resolve_member

_USER = {"type": "string", "description": "Who: a display name, @mention, or user id."}


def _aura_cog(ctx):
    if ctx.client is None:
        return None
    return ctx.client.get_cog("Aura_Manager")


@tool("get_aura", "Get a user's current aura score.",
      {"type": "object", "properties": {"user": _USER}, "required": ["user"]})
async def get_aura(ctx, user):
    if ctx.guild is None:
        return "Aura only works inside a server."
    cog = _aura_cog(ctx)
    if cog is None:
        return "Aura system isn't loaded."
    member = resolve_member(ctx.guild, user)
    if member is None:
        return f"Couldn't find anyone called '{user}'."
    score = await cog.get_aura(ctx.guild.id, member.id)
    return f"{member.display_name} has {score} aura."


@tool("add_aura", "Add (or remove, with a negative amount) aura from a user.",
      {"type": "object", "properties": {"user": _USER,
       "amount": {"type": "integer", "description": "Amount to add; negative to subtract."}},
       "required": ["user", "amount"]})
async def add_aura(ctx, user, amount):
    if ctx.guild is None:
        return "Aura only works inside a server."
    cog = _aura_cog(ctx)
    if cog is None:
        return "Aura system isn't loaded."
    member = resolve_member(ctx.guild, user)
    if member is None:
        return f"Couldn't find anyone called '{user}'."
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return "Amount has to be a whole number."
    await cog.add_aura(ctx.guild.id, member.id, amount)
    new = await cog.get_aura(ctx.guild.id, member.id)
    verb = "gave" if amount >= 0 else "docked"
    return f"{verb} {member.display_name} {abs(amount)} aura — now on {new}."


@tool("set_aura", "Set a user's aura to an exact value.",
      {"type": "object", "properties": {"user": _USER,
       "amount": {"type": "integer", "description": "The exact score to set."}},
       "required": ["user", "amount"]})
async def set_aura(ctx, user, amount):
    if ctx.guild is None:
        return "Aura only works inside a server."
    cog = _aura_cog(ctx)
    if cog is None:
        return "Aura system isn't loaded."
    member = resolve_member(ctx.guild, user)
    if member is None:
        return f"Couldn't find anyone called '{user}'."
    try:
        amount = int(amount)
    except (TypeError, ValueError):
        return "Amount has to be a whole number."
    await cog.set_aura(ctx.guild.id, member.id, amount)
    return f"Set {member.display_name}'s aura to {amount}."
