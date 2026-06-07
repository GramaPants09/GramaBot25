"""AgentBrain — a bounded Claude tool-use loop.

The brain takes a piece of user text, builds the conversation from memory +
persona, and runs Claude in a loop: the model may emit ``tool_use`` blocks,
which we dispatch to registered handlers and feed back as ``tool_result``
blocks, repeating until the model returns a plain text answer (or we hit the
iteration cap).

Design notes
------------
- The Anthropic SDK is imported lazily so this module loads without a key and
  is unit-testable by injecting a fake client.
- Destructive/"gated" tools must clear ``ToolContext.request_approval`` before
  they run; without an approval callback a gated tool is refused.
- If no ``ANTHROPIC_API_KEY`` is configured, ``respond`` falls back to a simple
  keyless OpenRouter chat (no tools) so the bot still talks.
"""
from __future__ import annotations

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
        model: str = DEFAULT_MODEL,
        fast_model: str = FAST_MODEL,
        max_iterations: int = 8,
        anthropic_client=None,
        api_key: str | None = None,
    ):
        self.client = client
        self.memory = memory or Memory()
        self.model = model
        self.fast_model = fast_model
        self.max_iterations = max_iterations
        self._anthropic = anthropic_client
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY")

    # ------------------------------------------------------------------ clients
    def _get_anthropic(self):
        if self._anthropic is not None:
            return self._anthropic
        if not self._api_key:
            return None
        from anthropic import AsyncAnthropic

        self._anthropic = AsyncAnthropic(api_key=self._api_key)
        return self._anthropic

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

        client = self._get_anthropic()
        if client is None:
            answer = await self._openrouter_fallback(system, messages)
            self.memory.add_turn(mem_user, channel_id, "assistant", answer)
            return answer

        answer = await self._run_loop(client, system, messages, ctx)
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

    # ---------------------------------------------------------------- fallback
    async def _openrouter_fallback(self, system, messages) -> str:
        """Keyless-Claude fallback: a plain OpenRouter chat with no tools."""
        import asyncio

        key = (
            os.getenv("OPEN_ROUTER_API_KEY")
            or os.getenv("GramaBot_API_KEY")
            or os.getenv("GROQ_API_KEY")
            or ""
        ).strip().strip('"').strip("'")
        if not key:
            return ("My brain's offline, guv — no ANTHROPIC_API_KEY and no OpenRouter "
                    "key set. Sort the .env out.")
        try:
            from openai import OpenAI

            oa = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
            convo = [{"role": "system", "content": system}] + [
                m for m in messages if isinstance(m.get("content"), str)
            ]
            resp = await asyncio.to_thread(
                oa.chat.completions.create,
                model=OPENROUTER_MODEL, messages=convo, max_tokens=500,
            )
            return self._clean(resp.choices[0].message.content or "")
        except Exception as e:
            return f"Brain error (fallback): {e}"

    @staticmethod
    def _clean(text: str) -> str:
        # Strip any <think>...</think> reasoning leakage and trim.
        return re.sub(r"<think>.*?</think>", "", text or "", flags=re.DOTALL).strip()
