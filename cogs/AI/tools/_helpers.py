"""Shared helpers for tool handlers."""
from __future__ import annotations


def resolve_member(guild, who):
    """Best-effort resolve ``who`` (id / <@mention> / display name) to a Member.

    Returns the Member or ``None``. ``guild`` may be ``None``.
    """
    if guild is None or who is None:
        return None
    text = str(who).strip()
    if not text:
        return None

    # raw id or <@id> / <@!id>
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        m = guild.get_member(int(digits))
        if m:
            return m

    lowered = text.lstrip("@").lower()
    for m in getattr(guild, "members", []):
        if m.name.lower() == lowered or (m.display_name or "").lower() == lowered:
            return m
    return None
