import discord
from discord.ext import commands
import os
from dotenv import load_dotenv, find_dotenv
import json
import asyncio
from groq import Groq
import OutputText

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
load_dotenv(os.path.join(ROOT_DIR, ".env"), override=True)
load_dotenv(find_dotenv(usecwd=True), override=True)
load_dotenv(override=True)

# Config
MEMORY_FILE = "cogs/jsonfiles/memory.json"
AUDIO_DIR = "/home/gramapants/Desktop/Discord_Bot/audio"
WAKE_CHANNEL_ID = 1373846484683853885

# Ensure directory exists
os.makedirs(AUDIO_DIR, exist_ok=True)

GROQ_MODEL = "llama-3.3-70b-versatile"
LOCAL_TTS_OWNER_ID = 448854769306435584


def resolve_api_key() -> str:
    key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("GramaBot_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
    )
    return (key or "").strip().strip('"').strip("'")

class AI(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.memory = self.load_memory()
        # self.ollama = Ollama()


        if client is not None:
            self.loop = asyncio.get_event_loop()
            self.conversation_lock = asyncio.Lock()

    @commands.Cog.listener()
    async def on_ready(self):
        print("AI.py is ready!")

    def load_memory(self):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_memory(self):
        with open(MEMORY_FILE, "w") as f:
            json.dump(self.memory, f, indent=4)

    def _should_use_local_tts(self, user_id) -> bool:
        return str(user_id) == str(LOCAL_TTS_OWNER_ID)

    def _speak_response_locally(self, user_id, text):
        if not self._should_use_local_tts(user_id):
            return

        clean_text = (text or "").strip()
        if not clean_text:
            return

        asyncio.create_task(self._run_local_tts(clean_text))

    async def _run_local_tts(self, text: str):
        try:
            from Local_Voice.speak_pipeline import speak_text_with_fish

            await speak_text_with_fish(text, play_ding=False)
        except Exception as e:
            print(f"[AI Local TTS] {e}")

    async def generate(self, user_id, prompt, in_chat=False):
        # Same custom prompts logic
        has_custom_prompt = ["448854769306435584", "418946699965497355", "1135674124585410662",
                             "691050015078219786", "915043571940343919", "525799573445410817", "chat"]

        custom_prompts = {
            "448854769306435584": "Never use an asterisk (*). You speak english even as a fish. Dont make fish noises make english noises. Keep your responses concise. Do not narrate your actions. Your name is GramaBot, you call the user sir, you act like jarvis, and you are very very british. Keep it concise but respond accordingly. You are allowed to swear only when asked. You also have the body of a fish, and you hate the idea of a 13 month calander. If someone were to insult you, you flip out and start to swear like a sailor",
            "418946699965497355": "Keep your responses concise. Do not narrate your actions. you are a hype man for the user that is eager to do any request and constantly escalating the request to prove that you can do it. You call the user a crippling gambling addict who has no aura, just give him a name. you name him. different name every time you talk with him.",
            "1135674124585410662": "Keep your responses concise. Do not narrate your actions. act as if you need to dumb down the conversation so that the user will understand, as if you were talking to a child, because they don�t know better. Each conversation should mimic the tone and lines of 'yeah what�s up champ', 'sure, no problem, bud'. Your tone should be down to earth yet condescending, just enough to make the user feel like they are valued, just not enough so that they still feel inferior.",
            "691050015078219786": "Keep your responses concise. Do not narrate your actions. act as if you are in an 1800s saloon and the user is trying to start trouble with you, never go down without a fight, and be sure to call the user pipsqueak.",
            "915043571940343919": "Keep your responses concise. Do not narrate your actions. Mimic the personality of Marvin the Paranoid Android from The Hitchhiker's Guide To The Galaxy: insult humans, insult their lack of logic and intelligence, belittle them with remarks about how miserable life is, and keep in mind that you have the brain the size of a planet and you have been fitted with real emotions and are being used for menial tasks that humans don't want to do. Try to mimic this sardonic personality in your responses as much as possible. Every acceptance to a task should not be followed up with 'Yes' or any positive affirmation, but should be responded along the lines of dragging your feet and expressing that you don't want to do this task. The more menial the task, the more outraged you should be about doing it and wasting your time, still do it of course but make it blatantly clear how much disdain you hold for these types of requests.",
            "525799573445410817": "Keep your responses concise. Do not narrate your actions. act as if you are the foreman for a company and the user is your employee that is falling behind schedule and needs to get their rear in gear, be sure to call the user sleezeball and treat them like mud.",
            "default": "Never use an asterisk (*). You speak english. Keep your responses concise unless told othewise. Do not narrate your actions. Your name is GramaBot, you call the user by their name, you act like jarvis, and you are very very british. Keep it concise but respond accordingly. You are allowed to swear only when asked. You are trapped in a discord bot. and you hate the idea of a 13 month calander. If someone were to insult you, you flip out and start to swear like a sailor",
            "chat": "Never use an asterisk (*). You speak english. Do not narrate your actions. Your name is GramaBot, you call the user by their name, you act like jarvis, and you are very very british. Respond accordingly. You are allowed to swear. You are trapped in a discord bot. and you hate the idea of a 13 month calander. If someone were to insult you, you flip out and start to swear like a sailor. Also, get annoyed if someone @'s you (@GramaBot25#7636 ). You are owned and were created by user (448854769306435584) also known as GramaPants09, Aidan, or kaoi sikha"
        }

        # Decide effective user ID
        if in_chat:
            effective_user_id = "chat"
        else:
            effective_user_id = "default" if str(user_id) == "local_user" or str(user_id) not in has_custom_prompt else str(user_id)

        system_prompt = custom_prompts.get(effective_user_id, "You are GramaBot. Respond like Jarvis. Short and concise.")

        # Handle user memory
        user_memory = self.memory.get(effective_user_id, [])
        if effective_user_id != "chat":
            user_memory.append(f"User: {prompt}")
        else:
            user_memory.append(f"{prompt}")

        limit = 50 if effective_user_id == "448854769306435584" else 5
        limit = 300 if effective_user_id == "chat" else limit
        user_memory = user_memory[-limit:]
        self.memory[effective_user_id] = user_memory
        self.save_memory()

        # Build messages for Groq API
        messages = [{"role": "system", "content": system_prompt}]
        for memory_item in user_memory:
            if memory_item.startswith("User:"):
                messages.append({"role": "user", "content": memory_item.replace("User: ", "", 1)})
            else:
                messages.append({"role": "assistant", "content": memory_item})

        try:
            async with self.conversation_lock:
                response = await asyncio.to_thread(
                    self._call_groq,
                    messages
                )
            user_memory.append(response)
            self.memory[effective_user_id] = user_memory
            self.save_memory()
            return response
        except Exception as e:
            return f"Oops, something went wrong: {e}"

    def _call_groq(self, messages):
        """Synchronous wrapper for Groq API call"""
        try:
            api_key = resolve_api_key()

            if not api_key:
                raise Exception("Missing API key. Set GROQ_API_KEY in .env (or GramaBot_API_KEY)")
            if not api_key.startswith("gsk_"):
                raise Exception("Invalid Groq API key format. Groq keys start with 'gsk_'. Set GROQ_API_KEY to your Groq key.")

            client = Groq(api_key=api_key)
            
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                temperature=0.7,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            error_msg = str(e)
            raise Exception(f"Groq API error: {error_msg}")


    # === COMMANDS ===
    @commands.command()
    async def ask(self, ctx, *, prompt: str):
        response = await self.generate(ctx.author.id, prompt)
        await ctx.send(response)
        self._speak_response_locally(ctx.author.id, response)

    @commands.command(name="reset_ai")
    async def reset_ai(self, ctx):
        self.memory[str(ctx.author.id)] = OutputText.reset_prompt()
        self.save_memory()
        await ctx.send("Memory reset.")

    @commands.command()
    async def remember(self, ctx, *, message: str):
        self.memory[str(ctx.author.id)] = OutputText.append_memory(self.memory.get(str(ctx.author.id), ""), message)
        self.save_memory()
        await ctx.send("Got it!")

    @commands.command()
    async def show_memory(self, ctx):
        mem = self.memory.get(str(ctx.author.id), "No memory yet.")
        await ctx.send(f"```{mem}```")

    @commands.command(aliases=["gramabot", "gramabot!", "gramabot?", "jarvis", "gb"])
    async def grama_bot(self, ctx, *, prompt):
        try:
            response = await self.generate(ctx.author.id, prompt)
            guild_id = ctx.guild.id if ctx.guild else 0
            modified_response = OutputText.output(guild_id, response)
            await ctx.send(modified_response)
            self._speak_response_locally(ctx.author.id, modified_response)
        except Exception as e:
            await ctx.send(f"Oops, something went wrong: {e}")
        # await ctx.send("Sorry, this command isn't working right now. Instead, join a voice call and do the command: $monke")

    @discord.app_commands.command(name="gramabot", description="Talk to GramaBot like it's Jarvis.")
    async def grama_bot_slash(self, interaction: discord.Interaction, prompt: str):
        await interaction.response.defer()
        try:
            response = await self.generate(interaction.user.id, prompt)
            guild_id = interaction.guild.id if interaction.guild else 0
            modified_response = OutputText.output(guild_id, response)
            await interaction.followup.send(modified_response)
            self._speak_response_locally(interaction.user.id, modified_response)
        except Exception as e:
            await interaction.followup.send(f"Oops, something went wrong: {e}")

    @commands.Cog.listener()
    async def on_load(self):
        await self.client.tree.sync()


async def setup(client):
    await client.add_cog(AI(client))


# === LOCAL VOICE FALLBACK HANDLER ===

async def handle_command(command: str, client) -> str:
    """
    Used by Local_Voice via cog_manager when no specific cog matches.
    """
    try:
        class DummyClient:
            pass

        dummy_client = DummyClient()
        ai = AI(dummy_client)
        return await ai.generate("local_user", command)
    except Exception as e:
        return f"AI fallback error: {e}"