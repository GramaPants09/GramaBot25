"""Web search tool — optional, backed by Brave Search if a key is configured."""
from __future__ import annotations

import os

from .registry import tool


@tool("web_search", "Search the web for current information.",
      {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]})
async def web_search(ctx, query):
    key = os.getenv("BRAVE_API_KEY")
    if not key:
        return "Web search isn't set up (no BRAVE_API_KEY), so I can't look that up right now."
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": 3},
                headers={"X-Subscription-Token": key, "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                data = await resp.json()
    except Exception as e:
        return f"Search failed: {e}"

    results = (data.get("web") or {}).get("results", [])[:3]
    if not results:
        return f"No results for '{query}'."
    return " | ".join(
        f"{r.get('title', '')}: {r.get('description', '')}".strip() for r in results
    )
