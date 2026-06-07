"""Human-in-the-loop approval for gated (destructive) tools.

When the brain wants to run a gated tool, it posts an Approve/Reject prompt in
the channel and waits for an admin (or the requesting user, if privileged) to
click. No click, no channel, or a timeout all mean *deny* — fail closed.
"""
from __future__ import annotations

import asyncio
import json

import discord


class ApprovalView(discord.ui.View):
    def __init__(self, allowed_user_id: int, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.allowed_user_id = allowed_user_id
        self.result: bool = False
        self._event = asyncio.Event()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        perms = getattr(interaction.user, "guild_permissions", None)
        is_admin = bool(perms and perms.administrator)
        if interaction.user.id == self.allowed_user_id or is_admin:
            return True
        await interaction.response.send_message("Not your call to make.", ephemeral=True)
        return False

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = True
        await interaction.response.edit_message(content="✅ Approved.", embed=None, view=None)
        self._event.set()
        self.stop()

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = False
        await interaction.response.edit_message(content="❌ Rejected.", embed=None, view=None)
        self._event.set()
        self.stop()

    async def wait_result(self) -> bool:
        try:
            await asyncio.wait_for(self._event.wait(), timeout=(self.timeout or 60) + 5)
        except asyncio.TimeoutError:
            pass
        return bool(self.result)


async def request_approval(channel, user, tool, args, *, timeout: float = 60) -> bool:
    """Post an approval prompt and return True only if explicitly approved."""
    if channel is None:
        return False
    view = ApprovalView(allowed_user_id=getattr(user, "id", 0), timeout=timeout)
    embed = discord.Embed(
        title="Approve this action?",
        description=f"GramaBot wants to run **`{tool.name}`**.",
        color=discord.Color.orange(),
    )
    arg_text = json.dumps(args, default=str)[:1000] if args else "(no arguments)"
    embed.add_field(name="Arguments", value=f"```{arg_text}```", inline=False)
    embed.set_footer(text=f"Requested by {getattr(user, 'display_name', 'someone')}")
    try:
        await channel.send(embed=embed, view=view)
    except Exception:
        return False
    return await view.wait_result()


def make_gate(channel, user, *, timeout: float = 60):
    """Return an ``async (tool, args) -> bool`` callback for ``AgentBrain``."""

    async def _gate(tool, args):
        return await request_approval(channel, user, tool, args, timeout=timeout)

    return _gate
