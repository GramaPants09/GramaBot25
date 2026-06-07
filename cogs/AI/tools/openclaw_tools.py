"""OpenClaw gateway tool — gated. Lets GramaBot reach Darwin & friends."""
from __future__ import annotations

import json

from .registry import tool


@tool(
    "openclaw_rpc",
    "Call a JSON-RPC method on the OpenClaw agent gateway (e.g. 'status', "
    "'agents.list', 'chat.send' to talk to Darwin). Use sparingly.",
    {"type": "object", "properties": {
        "method": {"type": "string", "description": "RPC method name, e.g. 'status'."},
        "params": {"type": "object", "description": "Method parameters (optional)."},
    }, "required": ["method"]},
    gated=True,
)
async def openclaw_rpc(ctx, method, params=None):
    from .openclaw import openclaw_call

    try:
        result = await openclaw_call(method, params or {})
    except Exception as e:
        return str(e)
    blob = json.dumps(result, default=str)
    if len(blob) > 1500:
        blob = blob[:1500] + "…"
    return f"OpenClaw {method} → {blob}"
