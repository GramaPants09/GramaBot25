import discord
from discord.ext import commands


def _chunk_lines_to_fields(title_prefix, lines, max_field_chars=900, max_fields=24):
    """Turn a list of lines into at most max_fields embed fields, each under max_field_chars."""
    if not lines:
        return [(title_prefix, "No items.")]

    fields = []
    cur = []
    cur_len = 0
    for line in lines:
        if cur_len + len(line) + 1 > max_field_chars:
            fields.append((f"{title_prefix}", "\n".join(cur)))
            cur = [line]
            cur_len = len(line) + 1
            if len(fields) >= max_fields:
                break
        else:
            cur.append(line)
            cur_len += len(line) + 1

    if cur and len(fields) < max_fields:
        fields.append((f"{title_prefix}", "\n".join(cur)))

    # If we hit the max_fields limit and there are remaining lines, indicate truncation
    total_chars = sum(len(v) for _, v in fields)
    if len(fields) >= max_fields and sum(1 for _ in lines) > 0 and sum(len(l) for l in lines) > total_chars:
        fields = fields[: max_fields - 1] + [(f"{title_prefix}", "...and more. Use `$help <category>` to view any category.")]

    return fields

class HelpView(discord.ui.View):
    def __init__(self, ctx, bot, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.bot = bot

        # Add one button per cog
        # Discord limits interactive components; cap buttons to first 20 cogs
        cog_names = list(self.bot.cogs.keys())[:20]
        for cog_name in cog_names:
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

        # Chunk commands into fields to avoid hitting embed field limits
        cmd_lines = []
        for command in cog.get_commands():
            usage = f"${command.name} {command.signature}" if getattr(command, 'signature', None) else f"${command.name}"
            desc = command.help or "No description provided."
            cmd_lines.append(f"{usage} — {desc}")

        for name, value in _chunk_lines_to_fields("Commands", cmd_lines):
            embed.add_field(name=name, value=value, inline=False)

        await interaction.response.edit_message(embed=embed, view=self.view)


class CustomHelp(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Ensure every command has a help description; if missing, provide a sensible default.
        for command in self.bot.walk_commands():
            if getattr(command, 'help', None) is None or str(command.help).strip() == "":
                # prefer short_doc (first line of the callback docstring) if present
                short = getattr(command, 'short_doc', None) or (command.callback.__doc__ or "").strip().splitlines()[0] if getattr(command, 'callback', None) and getattr(command.callback, '__doc__', None) else None
                if short:
                    command.help = short
                else:
                    # fall back to a generic usage hint
                    sig = command.signature or ""
                    command.help = f"No description provided. Usage: ${command.name} {sig}"

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

            # List all categories (cogs) in table of contents (chunk into safe embed fields)
            lines = []
            for cog_name, cog in self.bot.cogs.items():
                cmd_count = len([cmd for cmd in cog.get_commands() if not cmd.hidden])
                lines.append(f"{cog_name}: {cmd_count} command(s) — `$help {cog_name}`")

            for name, value in _chunk_lines_to_fields("Categories", lines):
                embed.add_field(name=name, value=value, inline=False)

            view = HelpView(ctx, self.bot)
            try:
                await ctx.send(embed=embed, view=view)
            except Exception as e:
                print(f"Error sending help view: {e}")
                # fallback: send embed without interactive view
                await ctx.send(embed=embed)
            # Inform if there are more categories than buttons
            if len(self.bot.cogs) > 20:
                await ctx.send("Note: some categories are omitted from the buttons. Use `$help <category>` to view any category.")

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
            # Chunk commands into fields to avoid hitting embed field limits
            cmd_lines = []
            for command in cog.get_commands():
                usage = f"${command.name} {command.signature}" if getattr(command, 'signature', None) else f"${command.name}"
                desc = command.help or "No description provided."
                cmd_lines.append(f"{usage} — {desc}")

            for name, value in _chunk_lines_to_fields("Commands", cmd_lines):
                embed.add_field(name=name, value=value, inline=False)
            try:
                await ctx.send(embed=embed)
            except Exception as e:
                print(f"Error sending help embed for category {category}: {e}")
                await ctx.send("Unable to display help right now.")


async def setup(bot):
    await bot.add_cog(CustomHelp(bot))
