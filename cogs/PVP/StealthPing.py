import discord
from discord.ext import commands
import OutputText

class StealthPing(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("StealthPing.py is ready")
        
    @commands.command()
    async def stealthping(self, ctx, member: discord.Member):
        await ctx.send(OutputText.output(ctx.guild.id,f"Hey {member.mention}"))
        await ctx.channel.purge(limit=2)
        
async def setup(client):
    await client.add_cog(StealthPing(client))

        