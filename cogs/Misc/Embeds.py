import discord
from discord.ext import commands
from datetime import datetime

class Embeds(commands.Cog):
    def __init__(self, client):
        self.client = client
    @commands.Cog.listener()
    async def on_ready(self):
        print("Embeds.py is ready!")
        
    @commands.command()
    async def embed(self, ctx):
        embed_message = discord.Embed(title="Title of embed", description="Description of embed", color=discord.Color.green())
        
        embed_message.set_author(name=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar)
        embed_message.set_thumbnail(url=ctx.guild.icon)
#         embed_message.set_image(url=ctx.guild.icon)
        embed_message.add_field(name="Field name", value="Field value", inline=False)
        now = datetime.now()
        string_date = now.strftime("%m-%d-%Y at %I:%M:%S %p")
        embed_message.set_footer(text="Action performed on " + string_date)        
        
        await ctx.send(embed = embed_message)
        
async def setup(client):
    await client.add_cog(Embeds(client))