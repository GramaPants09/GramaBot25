import discord
from discord.ext import commands
import asyncio
import random
import aiohttp
import html
import OutputText

class MuteChaos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_muting = {}  # user_id: task

    @commands.command(name="isthisthingon")
    async def isthisthingon(self, ctx, user: discord.Member):
        if not user.voice or not user.voice.channel:
            await ctx.send(OutputText.output(ctx.guild.id,f"{user.display_name} is not in a voice channel."))
            return

        if user.id in self.active_muting:
            await ctx.send(OutputText.output(ctx.guild.id,f"{user.display_name} is already being muted!"))
            return

        await ctx.send(OutputText.output(ctx.guild.id,f"Starting random muting on {user.mention}! Type '$saveme' to escape. If you dare..."))

        task = asyncio.create_task(self.mute_loop(user))
        self.active_muting[user.id] = {"task": task, "controller": ctx.author.id}

    async def mute_loop(self, user: discord.Member):
        try:
            while True:
                try:
                    await user.edit(mute=True)
                    print(f"Muted {user.display_name}")
                except Exception as e:
                    print(f"Error muting {user.display_name}: {e}")

                await asyncio.sleep(random.uniform(0.3, 1.0))

                try:
                    await user.edit(mute=False)
                    print(f"Unmuted {user.display_name}")
                except Exception as e:
                    print(f"Error unmuting {user.display_name}: {e}")

                await asyncio.sleep(random.uniform(3.0, 6.0))
        except asyncio.CancelledError:
            try:
                await user.edit(mute=False)
            except:
                pass
            print(f"{user.display_name} mute task cancelled & cleaned up.")


    @commands.command(name="stopmuting")
    async def stopmuting(self, ctx, user: discord.Member):
        if user.id not in self.active_muting:
            await ctx.send(OutputText.output(ctx.guild.id,"This user is not being muted."))
            return

        controller_id = self.active_muting[user.id]["controller"]
        if ctx.author.id != controller_id:
            await ctx.send(OutputText.output(ctx.guild.id,"Only the one who started the muting can stop it."))
            return

        self.active_muting[user.id]["task"].cancel()
        del self.active_muting[user.id]
        await ctx.send(OutputText.output(ctx.guild.id,f"Muting stopped for {user.display_name}."))

    @commands.command(name="saveme")
    async def saveme(self, ctx):
        user = ctx.author

        if user.id not in self.active_muting:
            await ctx.send(OutputText.output(ctx.guild.id,"You're not currently being muted!"))
            return

        question, correct_answer = await self.fetch_trivia_question()
        if not question:
            await ctx.send(OutputText.output(ctx.guild.id,"Couldn't get a trivia question right now. Try again shortly."))
            return

        await ctx.send(OutputText.output(ctx.guild.id,f"Answer this to be free: **{question}**\nType your answer below! You have 15 seconds."))

        def check(m):
            return m.author == user and m.channel == ctx.channel

        try:
            msg = await self.bot.wait_for('message', check=check, timeout=15)
        except asyncio.TimeoutError:
            await ctx.send(OutputText.output(ctx.guild.id,"Time's up! Stay muted."))
            return

        if msg.content.strip().lower() == correct_answer.lower():
            self.active_muting[user.id]["task"].cancel()
            del self.active_muting[user.id]
            await ctx.send(OutputText.output(ctx.guild.id,f"Correct! You're free, {user.mention}."))
        else:
            await ctx.send(OutputText.output(ctx.guild.id,f"Wrong! The answer was **{correct_answer}**. Still muted."))

    async def fetch_trivia_question(self):
        url = "https://opentdb.com/api.php?amount=1&type=multiple"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return None, None
                data = await resp.json()

        if not data["results"]:
            return None, None

        trivia = data["results"][0]
        question = html.unescape(trivia["question"])
        correct = html.unescape(trivia["correct_answer"])
        incorrect = [html.unescape(ans) for ans in trivia["incorrect_answers"]]
        options = incorrect + [correct]
        random.shuffle(options)

        question_formatted = f"{question}\n" + "\n".join(
            [f"{i+1}. {opt}" for i, opt in enumerate(options)]
        )

        return question_formatted, correct

async def setup(bot):
    await bot.add_cog(MuteChaos(bot))
