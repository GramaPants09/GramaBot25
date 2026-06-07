"""Minimal async WebSocket JSON-RPC client for the OpenClaw gateway.

Lets GramaBot reach the OpenClaw agent gateway (Darwin et al.) as a gated tool.
Connection details come from the environment so nothing is hardcoded:

    OPENCLAW_WS_URL   (default ws://127.0.0.1:18789)
    OPENCLAW_TOKEN    (auth token; required by the gateway)

``websockets`` is imported lazily so importing this module never fails.
"""
from __future__ import annotations

import json
import os

DEFAULT_URL = "ws://127.0.0.1:18789"


async def openclaw_call(
    method: str,
    params: dict | None = None,
    *,
    url: str | None = None,
    token: str | None = None,
    timeout: float = 10.0,
) -> dict:
    """Call a single JSON-RPC method on the gateway and return its result dict.

    Raises ``RuntimeError`` with a readable message on connection/auth/timeout
    failure so callers can surface it to the model as a tool result.
    """
    import asyncio

    url = url or os.getenv("OPENCLAW_WS_URL") or DEFAULT_URL
    token = token or os.getenv("OPENCLAW_TOKEN")

    try:
        import websockets
    except Exception as e:  # pragma: no cover
        raise RuntimeError(f"websockets library not installed: {e}")

    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    if token:
        payload["token"] = token

    try:
        async with websockets.connect(url, open_timeout=timeout) as ws:
            await ws.send(json.dumps(payload))
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    except asyncio.TimeoutError:
        raise RuntimeError(f"OpenClaw gateway timed out after {timeout}s at {url}")
    except Exception as e:
        raise RuntimeError(f"OpenClaw gateway unreachable at {url}: {e}")

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        raise RuntimeError(f"OpenClaw returned non-JSON: {e}")

    if isinstance(data, dict) and data.get("error"):
        raise RuntimeError(f"OpenClaw error: {data['error']}")
    return data.get("result", data) if isinstance(data, dict) else {"result": data}
