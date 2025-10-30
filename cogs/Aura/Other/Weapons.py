import discord
from discord.ext import commands

class Weapons(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Ranked_Aura.py is ready")

    async def set_weapon(self, ctx):
        pass

    async def get_weapon(self, ctx):
        pass

async def setup(client):
    await client.add_cog(Weapons(client))