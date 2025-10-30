import discord
from discord.ext import commands

class HelpView(discord.ui.View):
    def __init__(self, ctx, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.bot = bot

        # Add one button per cog
        for cog_name in self.bot.cogs.keys():
            self.add_item(HelpButton(cog_name))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the command invoker to use the buttons
        return interaction.user == self.ctx.author


class HelpButton(discord.ui.Button):
    def __init__(self, cog_name):
        super().__init__(label=cog_name, style=discord.ButtonStyle.primary)
        self.cog_name = cog_name

    async def callback(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog(self.cog_name)
        if not cog:
            await interaction.response.send_message(
                f"No category named `{self.cog_name}` found.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"{self.cog_name} Commands",
            color=discord.Color.green()
        )

        for command in cog.get_commands():
            embed.add_field(
                name=f"${command.name}",
                value=command.help or "No description provided.",
                inline=False
            )

        await interaction.response.edit_message(embed=embed, view=self.view)


class CustomHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help_command(self, ctx, *, category: str = None):
        """
        Show the custom help menu or a specific category.
        Usage: $help [category]
        """
        if category is None:
            # DEFAULT PAGE = Table of contents
            embed = discord.Embed(
                title="?? Help Menu",
                description="Welcome to the help menu!\n\n"
                            "Use `$help <category>` to jump to a page, or click a button below.\n\n"
                            "**Available Categories:**",
                color=discord.Color.blue()
            )

            # List all categories (cogs) in table of contents
            for cog_name, cog in self.bot.cogs.items():
                cmd_count = len([cmd for cmd in cog.get_commands() if not cmd.hidden])
                embed.add_field(
                    name=cog_name,
                    value=f"{cmd_count} command(s)\n`$help {cog_name}`",
                    inline=False
                )

            view = HelpView(ctx, self.bot)
            await ctx.send(embed=embed, view=view)

        else:
            # Specific category help
            cog = self.bot.get_cog(category)
            if not cog:
                await ctx.send(
                    embed=discord.Embed(
                        title="Not Found",
                        description=f"No category named `{category}`.",
                        color=discord.Color.red()
                    )
                )
                return

            embed = discord.Embed(
                title=f"{category} Commands",
                color=discord.Color.green()
            )
            for command in cog.get_commands():
                embed.add_field(
                    name=f"${command.name}",
                    value=command.help or "No description provided.",
                    inline=False
                )

            await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CustomHelp(bot))
