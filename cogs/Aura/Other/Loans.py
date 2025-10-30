import discord
from discord.ext import commands
import asyncio
import json


class Loans(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.filepath = "cogs/jsonfiles/loans.json"
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Loans.py is ready")
        
    def load_data(self):
        try:
            with open(self.filepath, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            print("ranked_aura.json not found.")
            return {}

    def save_data(self, data):
        with open(self.filepath, "w") as f:
            json.dump(data, f, indent=4)
    
    
    async def loan_available(self, ctx, guild_id: int, user_id: int):
        data = self.load_data()
        guild_id = str(guild_id)
        user_id = str(user_id)
        aura_manager = self.client.get_cog("Aura_Manager")
        
        user_data = data[guild_id]["users"][user_id]
        
#         if data[]
            
        
        
    
    @commands.command(name="loan")    
    async def request_loan(self, ctx, *, loan_amount: str):
        
        try:
            loan = str(loan_amount)
        except Exception:
            await ctx.send("You can only request a loan if you put the number down.")
            
        if loan <= 0:
            await ctx.send("You can only request a positive loan. (Do you know how loans work?)")
            

            
async def setup(client):
    await client.add_cog(Loans(client))        