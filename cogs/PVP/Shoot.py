import discord
from discord.ext import commands
import datetime
import random
import asyncio
import re
import OutputText

class ShootCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="shoot")
    async def shoot(self, ctx, target: str):
        guild = ctx.guild

        if target.lower() == "random":
            members = [m for m in guild.members if not m.bot and m != ctx.author]
            if not members:
                await ctx.send(OutputText.output(ctx.guild.id, "No one to shoot!"))
                return
            member = random.choice(members)
        else:
            try:
                member = await commands.MemberConverter().convert(ctx, target)
            except commands.BadArgument:
                await ctx.send(OutputText.output(ctx.guild.id, "Couldn't find that user."))
                return

        duration = datetime.timedelta(seconds=5)

        try:
            await member.timeout(duration, reason=f"{ctx.author.display_name} shot them (5 sec timeout)")
            await ctx.send(OutputText.output(ctx.guild.id, f"{member.display_name} got shot and is timed out for 5 seconds!"))
        except discord.Forbidden:
            await ctx.send(OutputText.output(ctx.guild.id, "I don't have permission to timeout that user."))
        except Exception as e:
            await ctx.send(OutputText.output(ctx.guild.id, f"Failed to shoot: {e}"))

async def setup(bot):
    await bot.add_cog(ShootCommand(bot))

# === LOCAL VOICE HANDLER (with nickname support) ===

import discord
import datetime
import asyncio
import re

# Optional: define aliases for members by name
ALIAS_MAP = {
    "ryan": 915043571940343919,
    "abrasive land": 915043571940343919,
    "lord thickums": 525799573445410817,
    "kyle": 525799573445410817,
    "aiden": 691050015078219786,
    "spencer": 1135674124585410662,
    "dennis": 418946699965497355
}

async def handle_command(command: str, client: discord.Client) -> str | None:
    keywords = ["shoot", "bang", "fire", "blast", "gun"]

    if not any(k in command.lower() for k in keywords):
        return None

    GUILD_ID = 1213715650736947241  # Replace with your actual server ID
    DEFAULT_DURATION = datetime.timedelta(seconds=5)

    # Extract target name from command
    match = re.search(r"shoot\s+(.*)", command.lower())
    if not match:
        return "You need to say who to shoot."

    target_name = match.group(1).strip()

    try:
        future = asyncio.run_coroutine_threadsafe(
            run_shoot(GUILD_ID, target_name, DEFAULT_DURATION, client), client.loop
        )
        return await asyncio.wrap_future(future)
    except Exception as e:
        return f"Voice handler crashed: {e}"

async def run_shoot(guild_id: int, target_name: str, duration: datetime.timedelta, client: discord.Client) -> str:
    guild = client.get_guild(guild_id)
    if not guild:
        return "Couldn't find the server."

    target_member = None

    # Check alias map first
    if target_name in ALIAS_MAP:
        target_member = guild.get_member(ALIAS_MAP[target_name])

    # Fallback to searching by nickname or username
    if not target_member:
        for member in guild.members:
            if member.bot:
                continue
            if target_name in member.display_name.lower() or target_name in member.name.lower():
                target_member = member
                break

    if not target_member:
        return f"Couldn't find anyone named '{target_name}'."

    try:
        await target_member.timeout(duration, reason="Shot by local voice user")
        return f"{target_member.display_name} got shot and is timed out for 5 seconds!"
    except discord.Forbidden:
        return "I don't have permission to timeout that user."
    except Exception as e:
        return f"Something went wrong trying to shoot: {e}"
