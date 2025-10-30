import discord
from discord.ext import commands
import random
import os
import OutputText

class Eight_Ball(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Eight_Ball.py is ready")

    @commands.command(aliases=["8ball", "eightball", "eight ball", "8 ball"])
    async def eight_ball(self, ctx):
        file_path = os.path.join(os.path.dirname(__file__), "cogs/text_files/8_ball_responses.txt")

        with open(file_path, "r") as f:
            random_responses = f.readlines()
            response = random.choice(random_responses)
        guild_id = ctx.guild.id if ctx.guild else 0
        await ctx.send(OutputText.output(guild_id ,response))

    @discord.app_commands.command(name="8ball", description="Ask the magic 8-ball a question.")
    async def slash_eight_ball(self, interaction: discord.Interaction):
        file_path = os.path.join(os.path.dirname(__file__), "cogs/text_files/8_ball_responses.txt")

        with open(file_path, "r") as f:
            random_responses = f.readlines()
            response = random.choice(random_responses)
        
        
        guild_id = interaction.guild.id if interaction.guild else 0
        await interaction.response.send_message(OutputText.output(guild_id, response))

async def setup(client):
    await client.add_cog(Eight_Ball(client))
