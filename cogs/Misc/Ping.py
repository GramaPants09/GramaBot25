import discord
from discord.ext import commands
import OutputText


class Ping(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Ping.py is ready")

    @commands.command()
    async def ping(self, ctx):
        """Shows the bot's latency in ms."""
        bot_latency = round(self.client.latency * 1000)

        # Ensure that ctx.guild exists before accessing its ID
        guild_id = ctx.guild.id if ctx.guild else 0  
        await ctx.send(OutputText.output(guild_id, f"PongPooliPooli! {bot_latency} ms."))

    @discord.app_commands.command(name="ping", description="Shows the bot's latency in ms.")
    async def slash_ping(self, interaction: discord.Interaction):
        bot_latency = round(self.client.latency * 1000)

        # Ensure that interaction.guild exists before accessing its ID
        guild_id = interaction.guild.id if interaction.guild else 0  
        await interaction.response.send_message(OutputText.output(guild_id, f"PongPooliPooli! {bot_latency} ms."))

async def setup(client):
    await client.add_cog(Ping(client))
