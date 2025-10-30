import discord
from discord.ext import commands
import OutputText

class Ging(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Ging.py is ready")
        
    @commands.command()
    async def ging(self, ctx):
        """Ging gang goolee?"""
        guild_id = ctx.guild.id if ctx.guild else 0  
        await ctx.send(OutputText.output(guild_id, """Ging Gang Goolee, Goolee,
Goolee, Goolee Watcha
Ging Gang Goo Ging Gang Goo
Ging Gang Goolee, Goolee,
Goolee, Goolee Watcha
Ging Gang Goo Ging Gang Goo

Hayla, Hayla Shayla, Hayla Shayla Hayla Ho-o-o!
Hayla, Hayla Shayla Hayla Shayla Hayla Ho-o-o!
Shalawally hallway shalawally shalawally!
Oompah, Oompah, Oompah, Oompah!"""))
        
     
    @discord.app_commands.command(name="ging", description="Ging gang goolee?")
    async def slash_ping(self, interaction: discord.Interaction):
        
        guild_id = interaction.guild.id if interaction.guild else 0  
        await interaction.response.send_message(OutputText.output(guild_id, """Ging Gang Goolee, Goolee,
Goolee, Goolee Watcha
Ging Gang Goo Ging Gang Goo
Ging Gang Goolee, Goolee,
Goolee, Goolee Watcha
Ging Gang Goo Ging Gang Goo

Hayla, Hayla Shayla, Hayla Shayla Hayla Ho-o-o!
Hayla, Hayla Shayla Hayla Shayla Hayla Ho-o-o!
Shalawally hallway shalawally shalawally!
Oompah, Oompah, Oompah, Oompah!"""))
        
async def setup(client):
    await client.add_cog(Ging(client))
