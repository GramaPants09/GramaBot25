import discord
from discord.ext import commands
import random
import re
from datetime import datetime, timedelta
import OutputText

class BlacklistBot(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.blacklisted_words = {}  # word: datetime it was blacklisted

    @commands.command(name='thatsaslursomewhere')
    async def blacklist_random_word(self, ctx):
        channel = ctx.channel
        word_candidates = []

        # Pull words from recent messages
        async for message in channel.history(limit=200):
            if message.author.bot:
                continue
            words = re.findall(r'\b\w+\b', message.content.lower())
            word_candidates.extend(words)

        if not word_candidates:
            await ctx.send(OutputText.output(ctx.guild.id,"Couldn't find any words to blacklist."))
            return

        # Blacklist a random word (timestamped)
        random_word = random.choice(word_candidates)
        self.blacklisted_words[random_word] = datetime.now()

        # Console output
        print(f"[BLACKLISTED] '{random_word}' is now blacklisted.")

        await ctx.send(":lock:" + OutputText.output(ctx.guild.id," A random word has now been blacklisted. Good luck.") + ":zipper_mouth_face:")

    @commands.command(name='allisforgiven')
    async def clear_blacklist(self, ctx):
        if not self.blacklisted_words:
            await ctx.send("There are no blacklisted words to forgive.")
            return

        forgiven = list(self.blacklisted_words.keys())
        self.blacklisted_words.clear()

        forgiven_words = ', '.join(f"**{w}**" for w in forgiven)
        await ctx.send(f":dove:" + OutputText.output(ctx.guild.id,f"All is forgiven. The following words are no longer forbidden: {forgiven_words}"))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        content = message.content.lower()
        message_time = message.created_at.replace(tzinfo=None)

        for word, added_time in self.blacklisted_words.items():
            if word in content and message_time > added_time:
                try:
                    await message.channel.send(
                        f":no_entry_sign: **{message.author.display_name}** has used the forbidden word, and will suffer punishment."
                    )

                    # Set timeout (mute) for 5 seconds
                    until = datetime.now() + timedelta(seconds=5)
                    await message.author.edit(timed_out_until=until)

                except discord.Forbidden:
                    await message.channel.send("I don't have permission to punish people.")
                except Exception as e:
                    print(f"Error timing out user: {e}")
                break


# Setup function to load the cog
async def setup(bot):
    await bot.add_cog(BlacklistBot(bot))
