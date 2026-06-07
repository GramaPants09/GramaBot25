"""Tests for resolve_member (the moderation target resolver)."""
from cogs.AI.tools._helpers import resolve_member


class FakeMember:
    def __init__(self, id, name, display=None):
        self.id = id
        self.name = name
        self.display_name = display or name


class FakeGuild:
    def __init__(self, members):
        self._by_id = {m.id: m for m in members}
        self.members = members

    def get_member(self, i):
        return self._by_id.get(i)


def test_digit_in_name_does_not_misresolve_to_id():
    # A member whose snowflake collides with digits stripped from another's name.
    collide = FakeMember(2, "Two")
    intended = FakeMember(123456789012345678, "Player2")
    g = FakeGuild([collide, intended])
    # "Player2" must match by NAME, not get_member(2).
    assert resolve_member(g, "Player2") is intended


def test_bare_snowflake_and_mention_resolve():
    bob = FakeMember(123456789012345678, "Bob")
    g = FakeGuild([bob])
    assert resolve_member(g, "123456789012345678") is bob
    assert resolve_member(g, "<@123456789012345678>") is bob
    assert resolve_member(g, "<@!123456789012345678>") is bob


def test_name_and_unknown():
    bob = FakeMember(123456789012345678, "Bob", display="Bobby")
    g = FakeGuild([bob])
    assert resolve_member(g, "bobby") is bob
    assert resolve_member(g, "nobody") is None
    assert resolve_member(None, "bob") is None
