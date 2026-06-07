"""Tests for the agent tool registry."""
import importlib


def _fresh_registry():
    # Import (or reimport) the registry module in isolation.
    from cogs.AI.tools import registry
    importlib.reload(registry)
    return registry


def test_register_and_lookup():
    registry = _fresh_registry()

    schema = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}

    @registry.tool("ping", "Reply pong", schema)
    async def _ping(ctx, x):
        return f"pong:{x}"

    t = registry.get_tool("ping")
    assert t is not None
    assert t.name == "ping"
    assert t.description == "Reply pong"
    assert t.schema == schema
    assert t.gated is False
    assert t.handler is _ping
    assert any(tt.name == "ping" for tt in registry.all_tools())


def test_gated_flag():
    registry = _fresh_registry()

    @registry.tool("nuke", "danger", {"type": "object", "properties": {}}, gated=True)
    async def _nuke(ctx):
        return "boom"

    assert registry.get_tool("nuke").gated is True


def test_anthropic_schemas_shape():
    registry = _fresh_registry()

    schema = {"type": "object", "properties": {}}

    @registry.tool("ping", "desc", schema)
    async def _ping(ctx):
        return "pong"

    specs = registry.anthropic_schemas()
    spec = next(s for s in specs if s["name"] == "ping")
    assert set(spec.keys()) == {"name", "description", "input_schema"}
    assert spec["description"] == "desc"
    assert spec["input_schema"] == schema


def test_get_tool_missing_returns_none():
    registry = _fresh_registry()
    assert registry.get_tool("does-not-exist") is None
