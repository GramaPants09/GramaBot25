import discord
from discord.ext import commands
import random
import OutputText

class WhoseGuy(commands.Cog):
    def __init__(self, client):
        self.client = client
        
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("WhoseGuy.py is ready")
        
    @commands.command(name="whoisthisguy")
    #@commands.has_permissions(manage_nicknames=True)
    async def who_guy(self, ctx, member: discord.Member):
        try:
            with open("cogs/text_files/adj.txt", "r") as a:
                adjective_list = a.read().splitlines()
            
            with open("cogs/text_files/noun.txt", "r") as n:
                noun_list = n.read().split(", ")

            random_num = random.randint(0, 99)
            adj = random.choice(adjective_list)
            noun = random.choice(noun_list)
            username = OutputText.output(ctx.guild.id,f"{adj}{noun}{random_num}")

            await member.edit(nick=username)
            await ctx.send(OutputText.output(ctx.guild.id,f"Nickname changed to **{username}** for {member.mention}"))
        
        except discord.Forbidden:
            await ctx.send(OutputText.output(ctx.guild.id,"I don't have permission to change that nickname."))
        except discord.HTTPException as e:
            await ctx.send(OutputText.output(ctx.guild.id,f"Failed to change nickname: {e}"))
        except Exception as e:
            await ctx.send(OutputText.output(ctx.guild.id,f"Something went wrong: {e}"))

async def setup(client):
    await client.add_cog(WhoseGuy(client))
