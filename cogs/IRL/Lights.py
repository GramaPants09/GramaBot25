import discord
from discord.ext import commands
from gpiozero import Servo
from time import sleep

class Lights(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.on = True

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Lights.py is ready")

    @commands.command(name="lights")
    async def lights(self, ctx):
        if ctx.author.id != 448854769306435584:
            await ctx.send("You are not authorized to use this command.")
            return
        
        servo = Servo(13)
        try:
            if not self.on:
              pass  
            else:
                pass
            
        except Exception as e:
            print("[Light.py] Error Occured:", e)

async def setup(client):
    await client.add_cog(Lights(client))