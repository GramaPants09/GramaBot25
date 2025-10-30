import discord
from discord.ext import commands
import json

class Balls(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Balls.py is ready!")

    def update_modifier(self, guild_id):
        """Toggles 'balls_text' and ensures 'reversed_text' is disabled."""
        with open("cogs/jsonfiles/modify_text.json", "r") as j:
            text_modifiers = json.load(j)

        # Ensure the guild has an entry
        if str(guild_id) not in text_modifiers:
            text_modifiers[str(guild_id)] = {"reversed_text": False, "balls_text": False}

        # Toggle 'balls_text' and disable 'reversed_text'
        text_modifiers[str(guild_id)]["balls_text"] = not text_modifiers[str(guild_id)]["balls_text"]
        text_modifiers[str(guild_id)]["reversed_text"] = False  # Disable Reverse mode
        text_modifiers[str(guild_id)]["australia_text"] = False  # Disable Australia mode

        # Save the updated file
        with open("cogs/jsonfiles/modify_text.json", "w") as j:
            json.dump(text_modifiers, j, indent=4)

        return text_modifiers[str(guild_id)]["balls_text"]

    @commands.command(aliases=["balls", "ball", "bigballs"])
    async def toggle_balls(self, ctx):
        new_status = self.update_modifier(ctx.guild.id)
        status = "enabled" if new_status else "disabled"
        await ctx.send(f"Balls mode is now {status}.")

    @discord.app_commands.command(name="balls", description="Toggle Balls mode.")
    async def toggle_balls_slash(self, interaction: discord.Interaction):
        new_status = self.update_modifier(interaction.guild.id)
        status = "enabled" if new_status else "disabled"
        await interaction.response.send_message(f"Balls mode is now {status}.")

async def setup(client):
    await client.add_cog(Balls(client))
