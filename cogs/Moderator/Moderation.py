import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.tree.sync()
        print("Moderation.py is ready!")

    # Text Command - Clear
    @commands.command()
    @commands.has_permissions(manage_messages=True)
    async def clear(self, ctx, count: int):
        """Clears a certain amount of messages."""
        await ctx.channel.purge(limit=count+1)
        await ctx.send(f"{count} message(s) have been deleted.", delete_after=5)

    # Slash Command - Clear
    @discord.app_commands.command(name="clear", description="Clears a certain amount of messages.")
    @discord.app_commands.checks.has_permissions(manage_messages=True)
    async def slash_clear(self, interaction: discord.Interaction, count: int):
        await interaction.response.defer(ephemeral=True)  # Acknowledge the interaction immediately
        await interaction.channel.purge(limit=count)      # Do the actual message purging
        await interaction.followup.send(f"{count} message(s) have been deleted.")  # Send the result


    # Text Command - Kick
    @commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, modreason):
        """Kick a member from the server."""
        await ctx.guild.kick(member, reason=modreason)
        embed = discord.Embed(title="Success!", color=discord.Color.green())
        embed.add_field(name="Kicked", value=f"{member.mention} has been kicked.", inline=False)
        embed.add_field(name="Reason", value=modreason, inline=False)
        await ctx.send(embed=embed)

    # Slash Command - Kick
    @discord.app_commands.command(name="kick", description="Kick a member from the server.")
    @discord.app_commands.checks.has_permissions(kick_members=True)
    async def slash_kick(self, interaction: discord.Interaction, member: discord.Member, modreason: str):
        await interaction.guild.kick(member, reason=modreason)
        await interaction.response.send_message(f"{member.mention} has been kicked for: {modreason}", ephemeral=True)

    # Text Command - Ban
    @commands.command()
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, modreason):
        """Ban a member from the server."""
        await ctx.guild.ban(member, reason=modreason)
        embed = discord.Embed(title="Success!", color=discord.Color.green())
        embed.add_field(name="Banned", value=f"{member.mention} has been banned.", inline=False)
        embed.add_field(name="Reason", value=modreason, inline=False)
        await ctx.send(embed=embed)

    # Slash Command - Ban
    @discord.app_commands.command(name="ban", description="Ban a member from the server.")
    @discord.app_commands.checks.has_permissions(ban_members=True)
    async def slash_ban(self, interaction: discord.Interaction, member: discord.Member, modreason: str):
        await interaction.guild.ban(member, reason=modreason)
        await interaction.response.send_message(f"{member.mention} has been banned for: {modreason}", ephemeral=True)

    # Slash Command - Unban
    @discord.app_commands.command(name="unban", description="Unban a user by ID.")
    @discord.app_commands.checks.has_permissions(ban_members=True)
    async def slash_unban(self, interaction: discord.Interaction, user_id: int):
        user = discord.Object(id=user_id)
        await interaction.guild.unban(user)
        await interaction.response.send_message(f"<@{user_id}> has been unbanned.", ephemeral=True)

async def setup(client):
    await client.add_cog(Moderation(client))
