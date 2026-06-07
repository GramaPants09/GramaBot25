"""Tests for the AgentBrain tool-use loop using a fake Anthropic client."""
import pytest

from cogs.AI.brain import AgentBrain
from cogs.AI.memory import Memory
from cogs.AI.tools import registry


class Block:
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeResp:
    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


class FakeMessages:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []

    async def create(self, **kw):
        self.calls.append(kw)
        return self.script.pop(0)


class FakeAnthropic:
    def __init__(self, script):
        self.messages = FakeMessages(script)


@pytest.mark.asyncio
async def test_tool_use_loop_runs_handler_and_feeds_result(tmp_path):
    ran = {}

    @registry.tool("echo_test", "echo", {"type": "object", "properties": {"text": {"type": "string"}}})
    async def _echo(ctx, text):
        ran["text"] = text
        return f"echoed:{text}"

    script = [
        FakeResp([Block(type="tool_use", id="t1", name="echo_test", input={"text": "oi"})], "tool_use"),
        FakeResp([Block(type="text", text="all done")], "end_turn"),
    ]
    fake = FakeAnthropic(script)
    brain = AgentBrain(
        client=None, memory=Memory(db_path=str(tmp_path / "b.db")),
        anthropic_client=fake, api_key="x",
    )

    out = await brain.respond(user="u1", channel="c1", guild=None, text="say oi")
    assert out == "all done"
    assert ran["text"] == "oi"

    # second model call must include the tool_result for t1
    second_call_messages = fake.messages.calls[1]["messages"]
    tool_results = [
        blk for m in second_call_messages if isinstance(m["content"], list)
        for blk in m["content"] if blk.get("type") == "tool_result"
    ]
    assert any(tr["tool_use_id"] == "t1" and "echoed:oi" in tr["content"] for tr in tool_results)
    # the assistant tool_use turn must be appended before the results
    roles = [m["role"] for m in second_call_messages]
    assert roles[-2:] == ["assistant", "user"]


@pytest.mark.asyncio
async def test_gated_tool_denied_without_approval(tmp_path):
    ran = {"called": False}

    @registry.tool("nuke_test", "danger", {"type": "object", "properties": {}}, gated=True)
    async def _nuke(ctx):
        ran["called"] = True
        return "boom"

    script = [
        FakeResp([Block(type="tool_use", id="t1", name="nuke_test", input={})], "tool_use"),
        FakeResp([Block(type="text", text="fine, didn't do it")], "end_turn"),
    ]
    fake = FakeAnthropic(script)
    brain = AgentBrain(memory=Memory(db_path=str(tmp_path / "b.db")), anthropic_client=fake, api_key="x")

    async def deny(tool, args):
        return False

    out = await brain.respond(user="u", channel="c", guild=None, text="nuke it", request_approval=deny)
    assert out == "fine, didn't do it"
    assert ran["called"] is False


@pytest.mark.asyncio
async def test_no_key_uses_fallback_message(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_ROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GramaBot_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    brain = AgentBrain(memory=Memory(db_path=str(tmp_path / "b.db")), api_key=None)
    out = await brain.respond(user="u", channel="c", guild=None, text="hi")
    assert "brain" in out.lower()
