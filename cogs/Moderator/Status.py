import discord
from discord.ext import commands, tasks
import random
from itertools import cycle
import os
import asyncio

class Status(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Status cog is ready!")
        self.client.loop.create_task(self.change_status())

    async def change_status(self):
        statuses = [
            "Type in '$help' for help",
            "Ging Gang?",
            "Goolee Goolee!",
            "What did the car say to the cow? Beef Beef? Get get it?",
            "Do $gb, $jarvis, $gramabot, $GramaBot :)"
        ]
        while True:
            await self.client.change_presence(
                activity=discord.Game(random.choice(statuses))
            )
            await asyncio.sleep(30)  # Changes every 30 seconds

async def setup(client):
    await client.add_cog(Status(client))
