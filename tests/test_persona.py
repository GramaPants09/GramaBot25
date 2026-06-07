"""Tests for persona system-prompt assembly."""
from cogs.AI import persona


def test_base_present_for_unknown_user():
    p = persona.system_prompt_for("local_user")
    assert persona.BUTCHER_BASE in p
    # no overlay text leaked in for an unknown id
    assert p.strip() == persona.BUTCHER_BASE.strip()


def test_known_user_gets_base_plus_overlay():
    uid = "915043571940343919"  # has a custom overlay
    p = persona.system_prompt_for(uid)
    assert persona.BUTCHER_BASE in p
    assert persona.OVERLAYS[uid] in p


def test_chat_mode_uses_chat_overlay():
    p = persona.system_prompt_for("anyone", in_chat=True)
    assert persona.BUTCHER_BASE in p
    assert persona.CHAT_OVERLAY in p
