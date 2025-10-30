import discord
from discord.ext import commands
import os
import asyncio

class Fish_Test_Cog(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Fish_Test_Cog is ready")

    @commands.command(name="tail")
    async def test_tail(self, ctx):
        await ctx.send("Flipping the tail...")
        process = await asyncio.create_subprocess_exec(
            "/usr/bin/python3", "Fish_Scripts/Fish_Flap_Tail.py"
        )
        await process.wait()

    @commands.command(name="mouth")
    async def test_mouth(self, ctx):
        await ctx.send("Moving the mouth...")
        process = await asyncio.create_subprocess_exec(
            "/usr/bin/python3", "Fish_Scripts/Fish_Move_Mouth.py"
        )
        await process.wait()

    @commands.command(name="head")
    async def test_head(self, ctx):
        await ctx.send("Raising the head...")
        process = await asyncio.create_subprocess_exec(
            "/usr/bin/python3", "Fish_Scripts/Fish_Head_Out.py"
        )
        await process.wait()

async def setup(client):
    await client.add_cog(Fish_Test_Cog(client))
