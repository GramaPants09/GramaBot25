from cogs.Aura.Gambling.Gambling import Gambling
import discord
from discord.ext import commands

class Mines(commands.Cog):
    def __init__(self, client):
        self.client = client
        gambling_cog = self.client.get_cog("Gambling")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Mines.py is ready")


    async def check_eligible_play(self, guildID, userID, min_bet=1):
        able_to_gamble = Gambling.Gambling.able_to_gamble(guildID, userID, min_bet)
        

    # Function to print the board (Allow for different sizes)

    # Function to set up the board (Not visible) with boards

    # Function that checks for user input

    # Function tha checks for mine or not


    
    



async def setup(client):
    await client.add_cog(Mines(client))


if __name__ == "__main__":
    pass