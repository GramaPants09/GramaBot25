import discord
from discord.ext import commands
import aiohttp
import os 
from dotenv import load_dotenv

load_dotenv()

class GifFetcher(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tenor_api_key = os.getenv("TENOR_KEY")

    @commands.command()
    async def gif(self, ctx, *, search: str):
        """Fetches the first GIF from Tenor based on a search term."""
        if not self.tenor_api_key:
            await ctx.send("I seem to be missing an API key. Who took it? Was it you?")
            return
        
        url = f"https://tenor.googleapis.com/v2/search?q={search}&key={self.tenor_api_key}&limit=1"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    await ctx.send(f"Something went wrong! Tenor returned status {response.status}.")
                    return
                
                data = await response.json()
                if "results" not in data or not data["results"]:
                    await ctx.send("No GIFs found. It's a GIF-less wasteland out there.")
                    return

                # Properly extracting the first GIF URL
                try:
                    gif_url = data["results"][0]["media_formats"]["gif"]["url"]
                except KeyError:
                    await ctx.send("Unexpected response format from Tenor. Maybe they changed their API?")
                    return

                await ctx.send(gif_url)

async def setup(bot):
    await bot.add_cog(GifFetcher(bot))
