import discord
from discord.ext import commands
import datetime
import OutputText

class ThirteenMonth(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="13month")
    async def thirteenmonth(self, ctx):
        user_id = 915043571940343919
        member = ctx.guild.get_member(user_id)

        if not member:
            await ctx.send(OutputText.output(ctx.guild.id, "Couldn't find that member in this server."))
            return

        duration = datetime.timedelta(seconds=13)

        try:
            await member.timeout(duration, reason="13 seconds of silence (from $13month)")
            await ctx.send(OutputText.output(ctx.guild.id, f"{member.display_name} has been timed out for 13 seconds. Next time use a different calendar."))
        except discord.Forbidden:
            await ctx.send(OutputText.output(ctx.guild.id, "I don't have permission to timeout that user."))
        except Exception as e:
            await ctx.send(OutputText.output(ctx.guild.id, f"Failed to timeout: {e}"))

async def setup(bot):
    await bot.add_cog(ThirteenMonth(bot))

# === LOCAL VOICE HANDLER ===

import discord
import datetime
import asyncio

async def handle_command(command: str, client: discord.Client) -> str | None:
    """
    Allows Local_Voice to trigger the $13month logic.
    Requires access to the bot client to locate the guild and member.
    """
    keywords = ["13 month", "13month", "thirteen month", "13 seconds"]

    if not any(k in command.lower() for k in keywords):
        return None

    GUILD_ID = 1213715650736947241  # <-- Replace with your actual guild ID
    USER_ID = 915043571940343919
    DURATION = datetime.timedelta(seconds=13)

    try:
        future = asyncio.run_coroutine_threadsafe(run_timeout(GUILD_ID, USER_ID, DURATION, client), client.loop)
        return await asyncio.wrap_future(future)
    except Exception as e:
        return f"Voice handler crashed: {e}"

async def run_timeout(guild_id: int, user_id: int, duration: datetime.timedelta, client: discord.Client) -> str:
    guild = client.get_guild(guild_id)
    if not guild:
        return "Couldn't access the server."

    member = guild.get_member(user_id)
    if not member:
        return "Ryan isn't here right now. Probably hiding."

    try:
        await member.timeout(duration, reason="13 seconds of silence (triggered by voice)")
        return f"{member.display_name} has been timed out for 13 seconds. Next time use a different calendar."
    except discord.Forbidden:
        return "I don't have permission to timeout Ryan."
    except Exception as e:
        return f"Error trying to timeout Ryan: {e}"
