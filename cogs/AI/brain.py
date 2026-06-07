"""AgentBrain — a bounded agentic tool-use loop over Claude or OpenRouter.

The brain takes a piece of user text, builds the conversation from memory +
persona, and runs the model in a loop: it may request tools, which we dispatch
to registered handlers and feed back, repeating until it returns a plain text
answer (or we hit the iteration cap).

Two providers are supported behind one seam (the two wire formats differ, so
each has its own loop):
- **anthropic** — the Anthropic SDK, ``tool_use``/``tool_result`` content blocks.
- **openrouter** — the OpenAI-compatible API, ``tool_calls`` + ``role:"tool"``
  results (arguments arrive as a JSON *string*).

Provider is chosen by ``BRAIN_PROVIDER`` (``anthropic``|``openrouter``); if unset
it auto-detects from which key is present. Both SDKs are imported lazily so the
module loads (and unit-tests) without any key, by injecting a fake client.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from cogs.AI import persona
from cogs.AI.memory import Memory
from cogs.AI.tools import registry

DEFAULT_MODEL = "claude-sonnet-4-6"
FAST_MODEL = "claude-haiku-4-5"
OPENROUTER_MODEL = "nvidia/nemotron-3-super-120b-a12b:free"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


@dataclass
class ToolContext:
    client: Any = None                 # the discord bot client
    guild: Any = None
    channel: Any = None
    user: Any = None
    voice: bool = False
    request_approval: Callable[["registry.Tool", dict], Awaitable[bool]] | None = None


class AgentBrain:
    def __init__(
        self,
        client=None,
        *,
        memory: Memory | None = None,
        model: str | None = None,
        fast_model: str | None = None,
        max_iterations: int = 8,
        anthropic_client=None,
        openrouter_client=None,
        api_key: str | None = None,
    ):
        self.client = client
        self.memory = memory or Memory()
        # Model is env-configurable so cost/quality can be tuned without code
        # changes — e.g. ANTHROPIC_MODEL=claude-haiku-4-5 for a near-free brain.
        self.model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL
        self.fast_model = fast_model or os.getenv("ANTHROPIC_FAST_MODEL") or FAST_MODEL
        self.max_iterations = max_iterations
        self._anthropic = anthropic_client
        self._openrouter = openrouter_client
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    # ------------------------------------------------------------------ clients
    def _provider(self) -> str:
        p = (os.getenv("BRAIN_PROVIDER") or "").strip().lower()
        if p in ("openrouter", "anthropic"):
            return p
        if self._api_key:
            return "anthropic"
        if self._openrouter_key():
            return "openrouter"
        return "none"

    @staticmethod
    def _openrouter_key() -> str:
        return (
            os.getenv("OPEN_ROUTER_API_KEY")
            or os.getenv("OPENROUTER_API_KEY")
            or os.getenv("GramaBot_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or ""
        ).strip().strip('"').strip("'")

    def _get_anthropic(self):
        if self._anthropic is not None:
            return self._anthropic
        if not self._api_key:
            return None
        from anthropic import AsyncAnthropic

        self._anthropic = AsyncAnthropic(api_key=self._api_key)
        return self._anthropic

    def _get_openrouter(self):
        if self._openrouter is not None:
            return self._openrouter
        key = self._openrouter_key()
        if not key:
            return None
        from openai import OpenAI

        self._openrouter = OpenAI(base_url=OPENROUTER_BASE_URL, api_key=key)
        return self._openrouter

    # ------------------------------------------------------------------- public
    async def respond(
        self,
        *,
        user=None,
        channel=None,
        guild=None,
        text: str,
        voice: bool = False,
        chat: bool = False,
        mem_key: str | None = None,
        request_approval=None,
    ) -> str:
        speaker_id = str(getattr(user, "id", user) or "local_user")
        channel_id = str(getattr(channel, "id", channel) or "dm")
        mem_user = mem_key or ("chat" if chat else speaker_id)

        system = persona.system_prompt_for(speaker_id, in_chat=chat or voice)
        messages = list(self.memory.history(mem_user, channel_id, limit=20))
        messages.append({"role": "user", "content": text})
        self.memory.add_turn(mem_user, channel_id, "user", text)

        ctx = ToolContext(
            client=self.client, guild=guild, channel=channel, user=user,
            voice=voice, request_approval=request_approval,
        )

        provider = self._provider()
        if provider == "openrouter":
            answer = await self._run_loop_openrouter(system, messages, ctx)
        elif provider == "anthropic":
            client = self._get_anthropic()
            answer = await self._run_loop(client, system, messages, ctx)
        elif self._openrouter_key():
            answer = await self._run_loop_openrouter(system, messages, ctx)
        else:
            answer = ("My brain's offline, guv — set ANTHROPIC_API_KEY or "
                      "OPEN_ROUTER_API_KEY in the .env.")

        self.memory.add_turn(mem_user, channel_id, "assistant", answer)
        return answer

    # --------------------------------------------------------------- tool loop
    async def _run_loop(self, client, system, messages, ctx: ToolContext) -> str:
        # Only advertise gated tools when an approval gate is actually wired,
        # so the model never wastes iterations on tools that will be refused.
        tools = registry.anthropic_schemas(include_gated=ctx.request_approval is not None)
        last_text = ""
        for _ in range(self.max_iterations):
            kwargs = dict(model=self.model, system=system, messages=messages, max_tokens=2048)
            if tools:
                kwargs["tools"] = tools
            resp = await client.messages.create(**kwargs)

            blocks = list(getattr(resp, "content", []) or [])
            text_out = "".join(
                getattr(b, "text", "") for b in blocks if getattr(b, "type", None) == "text"
            )
            tool_uses = [b for b in blocks if getattr(b, "type", None) == "tool_use"]
            if text_out:
                last_text = text_out

            # A truncated response may hold an incomplete tool_use block — never
            # dispatch that; just return whatever text we managed to get.
            if getattr(resp, "stop_reason", None) == "max_tokens":
                return self._clean(last_text) or "Ran out of room there — ask again and I'll keep it shorter."

            if not tool_uses:
                return self._clean(last_text)

            # Append the assistant turn (text + tool_use) before the results.
            assistant_content = []
            for b in blocks:
                btype = getattr(b, "type", None)
                if btype == "text":
                    assistant_content.append({"type": "text", "text": b.text})
                elif btype == "tool_use":
                    assistant_content.append(
                        {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
                    )
            messages.append({"role": "assistant", "content": assistant_content})

            results = []
            for tu in tool_uses:
                result = await self._run_tool(tu.name, tu.input or {}, ctx)
                results.append(
                    {"type": "tool_result", "tool_use_id": tu.id, "content": result}
                )
            messages.append({"role": "user", "content": results})

        # Hit the iteration cap — return whatever text we last produced.
        return self._clean(last_text) or "Bloody hell, I lost the thread there. Try again, mate."

    async def _run_tool(self, name: str, args: dict, ctx: ToolContext) -> str:
        t = registry.get_tool(name)
        if t is None:
            return f"Unknown tool '{name}'."
        if t.gated:
            approved = False
            if ctx.request_approval is not None:
                try:
                    approved = await ctx.request_approval(t, args)
                except Exception as e:
                    return f"Approval for '{name}' errored: {e}"
            if not approved:
                return f"Action '{name}' was not approved, so I didn't do it."
        try:
            return await t.handler(ctx, **args)
        except TypeError as e:
            return f"Tool '{name}' got bad arguments: {e}"
        except Exception as e:
            return f"Tool '{name}' failed: {e}"

    # ------------------------------------------------------ OpenRouter tool loop
    async def _run_loop_openrouter(self, system, messages, ctx: ToolContext) -> str:
        """Agentic loop over the OpenAI-compatible OpenRouter API.

        Differs from the Anthropic loop: tool calls come back on
        ``message.tool_calls`` with ``arguments`` as a JSON *string*, and results
        are appended as ``role:"tool"`` messages.
        """
        client = self._get_openrouter()
        if client is None:
            return ("My brain's offline, guv — set OPEN_ROUTER_API_KEY (or "
                    "ANTHROPIC_API_KEY) in the .env.")

        model = os.getenv("OPENROUTER_MODEL", OPENROUTER_MODEL)
        tools = registry.openai_schemas(include_gated=ctx.request_approval is not None)
        # OpenAI dialect: system lives in the message list (content is plain str).
        convo = [{"role": "system", "content": system}] + [
            m for m in messages if isinstance(m.get("content"), str)
        ]
        last_text = ""
        for _ in range(self.max_iterations):
            kwargs = dict(model=model, messages=convo, max_tokens=2048)
            if tools:
                kwargs["tools"] = tools
            try:
                resp = await asyncio.to_thread(client.chat.completions.create, **kwargs)
            except Exception as e:
                return f"Brain error (OpenRouter): {e}"

            msg = resp.choices[0].message
            text = self._clean(msg.content or "")
            if text:
                last_text = text
            tool_calls = getattr(msg, "tool_calls", None)
            if not tool_calls:
                return last_text or "..."

            # Append the assistant turn (with its tool_calls) before the results.
            convo.append({
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.function.name, "arguments": tc.function.arguments}}
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except (json.JSONDecodeError, TypeError):
                    args = {}
                result = await self._run_tool(tc.function.name, args, ctx)
                convo.append({"role": "tool", "tool_call_id": tc.id, "content": result})

        return last_text or "Bloody hell, I lost the thread there. Try again, mate."

    @staticmethod
    def _clean(text: str) -> str:
        # Strip any <think>...</think> reasoning leakage and trim.
        return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()
