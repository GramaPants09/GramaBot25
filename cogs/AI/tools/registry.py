"""Agent tool registry.

A tool is a callable ability the AgentBrain can invoke. Tools register
themselves with the ``@tool`` decorator at import time; the brain reads their
JSON schemas to tell Claude what it can do, then dispatches ``tool_use`` blocks
to the matching handler.

This module is intentionally dependency-free (no discord/anthropic imports) so
it can be imported and unit-tested anywhere. Handlers receive a ``ToolContext``
(defined in ``cogs.AI.brain``) as their first argument plus the model-supplied
keyword arguments, and return a short human-readable result string.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


@dataclass
class Tool:
    name: str
    description: str
    schema: dict
    handler: Callable[..., Awaitable[str]]
    gated: bool = False


_REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, schema: dict, *, gated: bool = False):
    """Decorator: register ``func`` as the handler for ``name``.

    The function is returned unchanged so it remains directly callable/testable.
    """

    def decorator(func: Callable[..., Awaitable[str]]) -> Callable[..., Awaitable[str]]:
        _REGISTRY[name] = Tool(
            name=name,
            description=description,
            schema=schema,
            handler=func,
            gated=gated,
        )
        return func

    return decorator


def get_tool(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    return list(_REGISTRY.values())


def anthropic_schemas(include_gated: bool = True) -> list[dict]:
    """Return tool definitions in Anthropic's ``tools=[...]`` format.

    When ``include_gated`` is False, gated (approval-required) tools are omitted
    so the model isn't offered tools that will always be refused on a surface
    with no approval gate wired (e.g. voice).
    """
    return [
        {"name": t.name, "description": t.description, "input_schema": t.schema}
        for t in _REGISTRY.values()
        if include_gated or not t.gated
    ]
