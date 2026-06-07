"""The AI cog — GramaBot's conversational front door.

Thin discord layer over the AgentBrain: it owns the shared brain instance,
migrates the legacy memory.json once, and exposes the chat commands. All the
actual thinking + tool use lives in cogs/AI/brain.py.
"""
import asyncio
import os

import discord
from discord.ext import commands
from dotenv import find_dotenv, load_dotenv

import OutputText
import cogs.AI.tools  # noqa: F401 - importing registers all agent tools
from cogs.AI import approval
from cogs.AI.brain import AgentBrain
from cogs.AI.memory import Memory

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"), override=True)
load_dotenv(find_dotenv(usecwd=True), override=True)
load_dotenv(override=True)

MEMORY_JSON = os.path.join(ROOT_DIR, "cogs", "jsonfiles", "memory.json")
BRAIN_DB = os.path.join(ROOT_DIR, "data", "brain.db")
AUDIO_DIR = os.path.join(ROOT_DIR, "audio")
LOCAL_TTS_OWNER_ID = 448854769306435584

os.makedirs(AUDIO_DIR, exist_ok=True)


class AI(commands.Cog):
    def __init__(self, client):
        self.client = client

        # One-time migration of the old whole-file memory into SQLite.
        try:
            n = Memory.import_json(MEMORY_JSON, BRAIN_DB)
            if n and os.path.exists(MEMORY_JSON):
                os.replace(MEMORY_JSON, MEMORY_JSON + ".imported")
                print(f"[AI] Imported {n} legacy memory turns into {BRAIN_DB}")
        except Exception as e:
            print(f"[AI] memory import skipped: {e}")

        self.memory = Memory(db_path=BRAIN_DB)
        self.brain = AgentBrain(client, memory=self.memory)
        self._bot_exchanges = {}  # (channel_id, author_id) -> (count, window_start)

    @commands.Cog.listener()
    async def on_ready(self):
        print("AI.py is ready!")

    # ---------------------------------------------------------------- helpers
    def _should_use_local_tts(self, user_id) -> bool:
        return str(user_id) == str(LOCAL_TTS_OWNER_ID)

    def _speak_response_locally(self, user_id, text):
        if not self._should_use_local_tts(user_id):
            return
        clean = (text or "").strip()
        if clean:
            asyncio.create_task(self._run_local_tts(clean))

    async def _run_local_tts(self, text: str):
        try:
            from Local_Voice.speak_pipeline import speak_text_with_fish

            await speak_text_with_fish(text, play_ding=False)
        except Exception as e:
            print(f"[AI Local TTS] {e}")

    async def _respond(self, ctx, prompt, chat=False):
        gate = approval.make_gate(ctx.channel, ctx.author)
        return await self.brain.respond(
            user=ctx.author, channel=ctx.channel, guild=ctx.guild,
            text=prompt, chat=chat, request_approval=gate,
        )

    # Back-compat shim for callers that still use generate() (e.g. voice).
    async def generate(self, user_id, prompt, in_chat=False):
        return await self.brain.respond(
            user=user_id, channel=None, guild=None, text=prompt, chat=in_chat
        )

    # =============================================================== COMMANDS
    @commands.command()
    async def ask(self, ctx, *, prompt: str):
        response = await self._respond(ctx, prompt)
        await ctx.send(response)
        self._speak_response_locally(ctx.author.id, response)

    @commands.command(name="reset_ai")
    async def reset_ai(self, ctx):
        self.memory.clear(str(ctx.author.id), str(ctx.channel.id))
        self.memory.clear("chat", str(ctx.channel.id))  # shared group-chat thread
        await ctx.send("Memory reset, clean slate.")

    @commands.command()
    async def remember(self, ctx, *, message: str):
        self.memory.add_turn(
            str(ctx.author.id), str(ctx.channel.id), "user",
            f"(Remember this about me: {message})",
        )
        await ctx.send("Got it, locked in.")

    @commands.command()
    async def show_memory(self, ctx):
        hist = self.memory.history(str(ctx.author.id), str(ctx.channel.id), limit=15)
        if not hist:
            await ctx.send("No memory yet.")
            return
        lines = [f"{h['role']}: {h['content']}" for h in hist]
        await ctx.send("```" + "\n".join(lines)[:1900] + "```")

    @commands.command(aliases=["gramabot", "gramabot!", "gramabot?", "jarvis", "gb", "butcher"])
    async def grama_bot(self, ctx, *, prompt):
        try:
            response = await self._respond(ctx, prompt)
            guild_id = ctx.guild.id if ctx.guild else 0
            modified = OutputText.output(guild_id, response)
            await ctx.send(modified)
            self._speak_response_locally(ctx.author.id, modified)
        except Exception as e:
            await ctx.send(f"Oops, something went wrong: {e}")

    @discord.app_commands.command(name="gramabot", description="Talk to GramaBot.")
    async def grama_bot_slash(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        try:
            gate = approval.make_gate(interaction.channel, interaction.user)
            response = await self.brain.respond(
                user=interaction.user, channel=interaction.channel, guild=interaction.guild,
                text=prompt, request_approval=gate,
            )
            guild_id = interaction.guild.id if interaction.guild else 0
            modified = OutputText.output(guild_id, response)
            await interaction.followup.send(modified)
            self._speak_response_locally(interaction.user.id, modified)
        except Exception as e:
            await interaction.followup.send(f"Oops, something went wrong: {e}")

    def _bot_exchange_allowed(self, channel_id, author_id, *, limit=3, window=60.0):
        """Loop breaker: cap how many times we'll auto-reply to a given bot."""
        import time

        key = (channel_id, author_id)
        count, start = self._bot_exchanges.get(key, (0, 0.0))
        now = time.monotonic()
        if now - start > window:
            count, start = 0, now
        if count >= limit:
            return False
        self._bot_exchanges[key] = (count + 1, start)
        return True

    # ----- Bot-to-bot: if another bot @s me, banter back (e.g. Darwin) -------
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == self.client.user.id:
            return
        if message.author.bot and self.client.user.mentioned_in(message):
            if not self._bot_exchange_allowed(message.channel.id, message.author.id):
                return  # hit the bot-to-bot cap; stay quiet to break the loop
            clean = message.clean_content.replace(f"@{self.client.user.display_name}", "").strip()
            if not clean:
                return
            prompt = f"{message.author.display_name} says: {clean}"
            response = await self.brain.respond(
                user="chat", channel=message.channel, guild=message.guild,
                text=prompt, chat=True, mem_key="botchat",
            )
            await message.channel.send(f"<@{message.author.id}> {response}")

    @commands.Cog.listener()
    async def on_load(self):
        await self.client.tree.sync()


async def setup(client):
    await client.add_cog(AI(client))


# === Local-voice fallback handler (used by Cog_Manager) ===
async def handle_command(command: str, client) -> str:
    cog = client.get_cog("AI")
    if cog is None:
        return "My brain isn't loaded right now."
    try:
        return await cog.brain.respond(
            user="local_user", channel=None, guild=None, text=command, voice=True
        )
    except Exception as e:
        return f"AI fallback error: {e}"
