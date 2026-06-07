"""Make GramaBot jump into text chat when addressed.

A wake-word / @mention opens a ~120s window during which the bot answers
everything in that channel, then goes quiet again. All thinking is delegated to
the shared AgentBrain owned by the AI cog.
"""
import asyncio

import discord
from discord.ext import commands

import OutputText

CONVO_WINDOW_SECONDS = 120


class RespondInChat(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.listening_channels = {}  # {channel_id: last_activity_time}

    def _brain(self):
        ai = self.client.get_cog("AI")
        return getattr(ai, "brain", None)

    @commands.Cog.listener()
    async def on_ready(self):
        print("RespondInChat is ready")

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore self, other bots (the AI cog handles bot-to-bot), and commands.
        if message.author == self.client.user or message.author.bot:
            return
        if message.content.startswith("$"):
            return

        if "fuck off" in message.content.lower():
            self.listening_channels.pop(message.channel.id, None)
            await message.channel.send("Fine. Be that way.")
            return

        is_wake = self.client.user in message.mentions
        active = message.channel.id in self.listening_channels
        now = asyncio.get_event_loop().time()

        if active and not is_wake:
            started = self.listening_channels[message.channel.id]
            if now - started >= CONVO_WINDOW_SECONDS:
                self.listening_channels.pop(message.channel.id, None)
                return
        elif not is_wake:
            return  # not addressed and no active window

        brain = self._brain()
        if brain is None:
            return

        self.listening_channels[message.channel.id] = now
        prompt = (
            f'[Group chat. The person who just spoke is "{message.author.display_name}". '
            f"Answer them directly.] {message.content}"
        )
        try:
            response = await brain.respond(
                user=message.author, channel=message.channel, guild=message.guild,
                text=prompt, chat=True,
            )
        except Exception as e:
            print(f"[RespondInChat] brain error: {e}")
            return
        guild_id = message.guild.id if message.guild else 0
        await message.channel.send(OutputText.output(guild_id, response))


async def setup(client):
    await client.add_cog(RespondInChat(client))
