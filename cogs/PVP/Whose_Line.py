import discord
from discord.ext import commands
import random
import OutputText

class WhoseLine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='whoseline')
    async def whoseline(self, ctx):
        channel = ctx.channel
        members = [m for m in channel.members if not m.bot]

        if not members:
            await ctx.send(OutputText.output(ctx.guild.id,"No human members found in this channel!"))
            return

        # Pick a random member
        chosen_member = random.choice(members)

        # Fetch messages from history
        messages = []
        async for msg in channel.history(limit=None):  # Adjust limit if needed
            if msg.author == chosen_member and msg.content.strip():
                messages.append(msg)

        if not messages:
            await ctx.send(OutputText.output(ctx.guild.id,f"Couldn't find any messages from {chosen_member.display_name}."))
            return

        random_message = random.choice(messages)
        await ctx.send(OutputText.output(ctx.guild.id,
            f"**Whose line is it anyway?**\n" +
            f"> {random_message.content}"
        ))

# Setup function to add the cog
async def setup(bot):
    await bot.add_cog(WhoseLine(bot))
