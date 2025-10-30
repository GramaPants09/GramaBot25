import discord
from discord.ext import commands
import json

class Reverse(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Reverse.py is ready!")

    def update_modifier(self, guild_id):
        """Toggles 'reversed_\text' and ensures 'australia_text' is disabled."""
        with open("cogs/jsonfiles/modify_text.json", "r") as j:
            text_modifiers = json.load(j)

        # Ensure the guild has an entry
        if str(guild_id) not in text_modifiers:
            text_modifiers[str(guild_id)] = {"reversed_text": False, "australia_text": False}

        # Toggle 'reversed_text' and disable 'australia_text'
        text_modifiers[str(guild_id)]["reversed_text"] = not text_modifiers[str(guild_id)]["reversed_text"]
        text_modifiers[str(guild_id)]["australia_text"] = False  # Disable Australia mode
        text_modifiers[str(guild_id)]["balls_text"] = False  # Disable Balls mode

        # Save the updated file
        with open("cogs/jsonfiles/modify_text.json", "w") as j:
            json.dump(text_modifiers, j, indent=4)

        return text_modifiers[str(guild_id)]["reversed_text"]

    @commands.command(aliases=["reverse", "reversed", "rev"])
    async def toggle_reverse(self, ctx):
        new_status = self.update_modifier(ctx.guild.id)
        status = "enabled" if new_status else "disabled"
        await ctx.send(f"Reverse speech mode is now {status}.")

    @discord.app_commands.command(name="reverse", description="Toggle reverse speech mode.")
    async def toggle_reverse_slash(self, interaction: discord.Interaction):
        new_status = self.update_modifier(interaction.guild.id)
        status = "enabled" if new_status else "disabled"
        await interaction.response.send_message(f"Reverse speech mode is now {status}.")

async def setup(client):
    await client.add_cog(Reverse(client))
