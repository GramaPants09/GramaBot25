import discord
from discord.ext import commands
import json

class Normal_Pills(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Normal_Pills.py is ready!")

    def reset_modifiers(self, guild_id):
        """Sets both 'reversed_text' and 'australia_text' to False in the JSON file."""
        with open("cogs/jsonfiles/modify_text.json", "r") as j:
            text_modifiers = json.load(j)

        # Ensure the guild has an entry
        if str(guild_id) not in text_modifiers:
            text_modifiers[str(guild_id)] = {"reversed_text": False, "australia_text": False}

        # Set both modifiers to False
        text_modifiers[str(guild_id)]["reversed_text"] = False
        text_modifiers[str(guild_id)]["australia_text"] = False
        text_modifiers[str(guild_id)]["balls_text"] = False
        text_modifiers[str(guild_id)]["language"]= "en"

        # Save the updated file
        with open("cogs/jsonfiles/modify_text.json", "w") as j:
            json.dump(text_modifiers, j, indent=4)

    @commands.command(aliases=["normal", "reset"])
    async def normal_pills(self, ctx):
        """Turn off all speech modifications."""
        self.reset_modifiers(ctx.guild.id)
        await ctx.send("You have taken your normal pills. Everything is back to normal.")

    @discord.app_commands.command(name="normalpills", description="Turn off all speech modifications.")
    async def normal_pills_slash(self, interaction: discord.Interaction):
        self.reset_modifiers(interaction.guild.id)
        await interaction.response.send_message("You have taken your normal pills. Everything is back to normal.")

async def setup(client):
    await client.add_cog(Normal_Pills(client))
