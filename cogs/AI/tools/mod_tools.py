"""Moderation tools — gated, and they re-verify the requester's permissions.

Critical: the model asking for a ban is NOT authorization. Every handler here
independently checks that the *invoking Discord user* actually has the relevant
permission and out-ranks the target, regardless of what the model decided.
These tools are registered ``gated=True`` so they also need human approval.
"""
from __future__ import annotations

from .registry import tool
from ._helpers import resolve_member

_USER = {"type": "string", "description": "Target: display name, @mention, or user id."}
_REASON = {"type": "string", "description": "Reason for the action."}


def _precheck(ctx, perm: str, target):
    """Return an error string if the action is not allowed, else None."""
    if ctx.guild is None:
        return "That only works inside a server."
    invoker = ctx.user
    if invoker is None or not hasattr(invoker, "guild_permissions"):
        return "I can't verify who's asking, so I won't do that."
    if not getattr(invoker.guild_permissions, perm, False):
        return f"You don't have permission to do that ({perm})."
    if target is None:
        return "Couldn't find that member."
    # role hierarchy: requester must out-rank the target
    if hasattr(invoker, "top_role") and hasattr(target, "top_role"):
        if invoker.id != ctx.guild.owner_id and invoker.top_role <= target.top_role:
            return f"{target.display_name} is above your pay grade — can't touch 'em."
    me = ctx.guild.me
    if me is not None and hasattr(me, "top_role") and me.top_role <= getattr(target, "top_role", me.top_role):
        return f"{target.display_name} outranks me, so I can't either."
    return None


@tool("timeout_user", "Time a member out (mute) for some minutes.",
      {"type": "object", "properties": {"user": _USER,
       "minutes": {"type": "integer", "description": "How many minutes (default 5)."},
       "reason": _REASON}, "required": ["user"]}, gated=True)
async def timeout_user(ctx, user, minutes=5, reason="No reason given"):
    from datetime import timedelta

    target = resolve_member(ctx.guild, user)
    err = _precheck(ctx, "moderate_members", target)
    if err:
        return err
    try:
        minutes = max(1, min(int(minutes), 40320))  # discord cap: 28 days
    except (TypeError, ValueError):
        minutes = 5
    try:
        await target.timeout(timedelta(minutes=minutes), reason=reason)
    except Exception as e:
        return f"Timeout failed: {e}"
    return f"Timed {target.display_name} out for {minutes} min. ({reason})"


@tool("kick_user", "Kick a member from the server.",
      {"type": "object", "properties": {"user": _USER, "reason": _REASON},
       "required": ["user"]}, gated=True)
async def kick_user(ctx, user, reason="No reason given"):
    target = resolve_member(ctx.guild, user)
    err = _precheck(ctx, "kick_members", target)
    if err:
        return err
    try:
        await ctx.guild.kick(target, reason=reason)
    except Exception as e:
        return f"Kick failed: {e}"
    return f"Kicked {target.display_name}. ({reason})"


@tool("ban_user", "Ban a member from the server.",
      {"type": "object", "properties": {"user": _USER, "reason": _REASON},
       "required": ["user"]}, gated=True)
async def ban_user(ctx, user, reason="No reason given"):
    target = resolve_member(ctx.guild, user)
    err = _precheck(ctx, "ban_members", target)
    if err:
        return err
    try:
        await ctx.guild.ban(target, reason=reason)
    except Exception as e:
        return f"Ban failed: {e}"
    return f"Banned {target.display_name}. ({reason})"
