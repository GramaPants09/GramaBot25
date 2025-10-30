import discord
from discord.ext import commands
import OutputText
import os
import random

class What_Ghost(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("What_Ghost.py is ready")

    @commands.command(aliases=["ghosts", "ghost", "ghots", "phasmo", "phasmophobia"])
    async def what_ghost(self, ctx):
        """Provides a random Phasmophobia ghost for when you have no clue what you are doing."""
        file_path = os.path.join(os.path.dirname(__file__), "cogs/text_files/ghosts.txt")

        with open(file_path, "r") as f:
            random_responses = f.readlines()
            response = random.choice(random_responses)
        guild_id = ctx.guild.id if ctx.guild else 0
        await ctx.send(OutputText.output(guild_id ,response))

    @discord.app_commands.command(name="whatghost", description="Provides a random Phasmophobia ghost for when you have no clue what you are doing.")
    async def what_ghost_slash(self, interaction: discord.Interaction):
        file_path = os.path.join(os.path.dirname(__file__), "cogs/text_files/ghosts.txt")

        with open(file_path, "r") as f:
            random_responses = f.readlines()
            response = random.choice(random_responses)
        
        
        guild_id = interaction.guild.id if interaction.guild else 0
        await interaction.response.send_message(OutputText.output(guild_id, response))

async def setup(client):
    await client.add_cog(What_Ghost(client))

# === LOCAL VOICE HANDLER ===

async def handle_command(command: str, client) -> str | None:
    """Allows the What_Ghost command to be used by Local_Voice.py."""
    keywords = ["ghost", "phasmo", "phasmophobia"]
    if any(k in command for k in keywords):
        file_path = os.path.join(os.path.dirname(__file__), "cogs/text_files/ghosts.txt")
        with open(file_path, "r") as f:
            random_responses = f.readlines()
            response = random.choice(random_responses)
        return response.strip()
    return None  # Not handled by this cog