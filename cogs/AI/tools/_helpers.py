"""Shared helpers for tool handlers."""
from __future__ import annotations

import re

# A bare snowflake (15-20 digits) or a <@id> / <@!id> mention — NOT stray digits
# embedded in a display name like "Player2".
_ID_RE = re.compile(r"<@!?(\d+)>|(\d{15,20})")


def resolve_member(guild, who):
    """Best-effort resolve ``who`` (id / <@mention> / display name) to a Member.

    Returns the Member or ``None``. ``guild`` may be ``None``.
    """
    if guild is None or who is None:
        return None
    text = str(who).strip()
    if not text:
        return None

    m_id = _ID_RE.fullmatch(text)
    if m_id:
        member = guild.get_member(int(m_id.group(1) or m_id.group(2)))
        if member:
            return member

    lowered = text.lstrip("@").lower()
    for m in getattr(guild, "members", []):
        if m.name.lower() == lowered or (m.display_name or "").lower() == lowered:
            return m
    return None
