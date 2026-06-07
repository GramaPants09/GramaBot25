"""Importing the tools package registers every built-in tool."""
import sys


def _fresh_tools():
    for name in list(sys.modules):
        if name.startswith("cogs.AI.tools"):
            del sys.modules[name]
    import cogs.AI.tools as tools
    return tools


def test_all_expected_tools_registered():
    tools = _fresh_tools()
    names = {t.name for t in tools.registry.all_tools()}
    expected = {
        "play_music", "skip_music", "pause_music", "resume_music", "stop_music", "queue_status",
        "join_voice", "leave_voice", "speak",
        "get_aura", "add_aura", "set_aura",
        "timeout_user", "kick_user", "ban_user",
        "openclaw_rpc", "web_search",
    }
    missing = expected - names
    assert not missing, f"missing tools: {missing}"


def test_destructive_tools_are_gated():
    tools = _fresh_tools()
    gated = {t.name for t in tools.registry.all_tools() if t.gated}
    assert {"timeout_user", "kick_user", "ban_user", "openclaw_rpc"} <= gated
    # read-only tools must NOT be gated
    assert "get_aura" not in gated
    assert "play_music" not in gated
