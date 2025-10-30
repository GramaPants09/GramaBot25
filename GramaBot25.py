


#       This is GramaBot25, the first rendition of GramaBot, made, well, in 2025. Duh.
#       The Proud owner of gramabot is none other than GramaPants.


#
#       RUN FROM THE TERMINAL!!!!! RUNNING FROM VSCODE BREAKS OVERTIME
#
#           cd ~/Desktop/Discord_Bot; source venv/bin/activate; python GramaBot25.py 2>/dev/null
#


import os
from dotenv import load_dotenv
import sys
import threading
import json
import asyncio
import discord
if not discord.opus.is_loaded():
    discord.opus.load_opus("libopus.so.0")
from discord.ext import commands
from Local_Voice.main import voice_loop_entrypoint

voice_started = False
prefix_cache = {}

load_dotenv()
DISCORD_API = os.getenv("DISCORD_API")



def load_prefixes():
    global prefix_cache
    try:
        with open("cogs/jsonfiles/prefixes.json", "r") as f:
            prefix_cache = json.load(f)
    except FileNotFoundError:
        prefix_cache = {}


def get_server_prefix(client, message):
    return prefix_cache.get(str(message.guild.id), "$")

client = commands.Bot(command_prefix=get_server_prefix, intents=discord.Intents.all(), owner_id=448854769306435584)
client.remove_command("help")

@client.event
async def on_ready():
    global voice_started
    load_prefixes()
    await client.tree.sync()
    print(f"We have logged in as {client.user}")
 
    print(discord.opus.is_loaded()) # Checks for discord voice
    if not discord.opus.is_loaded():
        discord.opus.load_opus('libopus.so.0')


    # if not voice_started:
    #     voice_thread = threading.Thread(target=lambda: asyncio.run(voice_loop_entrypoint(client)), daemon=True)
    #     voice_thread.start()
    #     voice_started = True

@client.event
async def on_guild_join(guild):
    global prefix_cache

    # Update prefixes.json and cache
    prefix_cache[str(guild.id)] = "$"
    with open("cogs/jsonfiles/prefixes.json", "w") as f:
        json.dump(prefix_cache, f, indent=4)

    # Mutes json
    with open("cogs/jsonfiles/mutes.json", "r") as i:
        mute_role = json.load(i)
    mute_role[str(guild.id)] = None
    with open("cogs/jsonfiles/mutes.json", "w") as i:
        json.dump(mute_role, i, indent=4)

    # ModifyText json
    with open("cogs/jsonfiles/modify_text.json", "r") as j:
        text_modifiers = json.load(j)
    text_modifiers[str(guild.id)] = {
        "reversed_text": False,
        "australia_text": False,
        "balls_text": False,
        "language": "en"
    }
    with open("cogs/jsonfiles/modify_text.json", "w") as j:
        json.dump(text_modifiers, j, indent=4)

    # Ranked Aura json
    with open("cogs/jsonfiles/ranked_aura.json", "r") as k:
        ranked_aura = json.load(k)
    ranked_aura[str(guild.id)] = {"users": {}}
    for member in guild.members:
        if not member.bot:
            ranked_aura[str(guild.id)]["users"][str(member.id)] = {
                "Username": member.name,
                "ScoreHistory": [0]
            }
    with open("cogs/jsonfiles/ranked_aura.json", "w") as k:
        json.dump(ranked_aura, k, indent=4)

    # Music Queue json
    with open("cogs/jsonfiles/music_queue.json", "r") as m:
        music_queue = json.load(m)
    music_queue[str(guild.id)] = []
    with open("cogs/jsonfiles/music_queue.json", "w") as m:
        json.dump(music_queue, m, indent=4)

    # Loans json
    with open("cogs/jsonfiles/loans.json", "r") as l:
        loans = json.load(l)
    loans[str(guild.id)] = {"users": {}}
    for member in guild.members:
        loans[str(guild.id)]["users"][str(member.id)] = {
            "Username": member.name,
            "date_of_loan": None,
            "amount_loaned": 0,
            "Loans_in_past_week": 0
        }
    with open("cogs/jsonfiles/loans.json", "w") as l:
        json.dump(loans, l, indent=4)

    # Weapons json
    with open("cogs/jsonfiles/weapons.json", "r") as w:
        weapons = json.load(w)
    weapons[str(guild.id)] = {"users": {}}
    for member in guild.members:
        weapons[str(guild.id)]["users"][str(member.id)] = {
            "range_weapon": 0,
            "melee_weapon": 0
        }
    with open("cogs/jsonfiles/weapons.json", "w") as w:
        json.dump(weapons, w, indent=4)  # Fixed from dumping loans

@client.event
async def on_guild_remove(guild):
    for file in ["prefixes", "mutes", "modify_text", "music_queue"]:
        with open(f"cogs/jsonfiles/{file}.json", "r") as f:
            data = json.load(f)
        data.pop(str(guild.id), None)
        with open(f"cogs/jsonfiles/{file}.json", "w") as f:
            json.dump(data, f, indent=4)

@client.command()
async def setprefix(ctx, *, newprefix: str):
    global prefix_cache
    prefix_cache[str(ctx.guild.id)] = newprefix
    with open("cogs/jsonfiles/prefixes.json", "w") as f:
        json.dump(prefix_cache, f, indent=4)
    await ctx.send(f"Prefix changed to: {newprefix}")


@commands.has_permissions(administrator=True)
@client.command()
async def setchannel(ctx):
    guild_id = str(ctx.guild.id)   # always save keys as strings for JSON
    channel_id = ctx.channel.id    # save ID, not object

    # Load existing data or create empty dict
    try:
        with open("cogs/jsonfiles/aura_channel.json", "r") as f:
            channels = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        channels = {}

    # Update this guilds entry
    channels[guild_id] = channel_id

    # Save back to file
    with open("cogs/jsonfiles/aura_channel.json", "w") as f:
        json.dump(channels, f, indent=4)

    await ctx.send(f"GramaBot main channel set to **{ctx.channel.name}**")
        

@client.command(name="reload")
@commands.is_owner()
async def reload(ctx, extension: str):
    """Reloads a cog without restarting the bot."""
    try:
        await client.reload_extension(f"cogs.{extension}")
        await ctx.send(f"? Reloaded `{extension}` successfully.")
    except Exception as e:
        await ctx.send(f"? Failed to reload `{extension}`: `{e}`")


def discover_cogs():
    """Return a list of dotted module paths for all cogs in ./cogs (recursively)."""
    modules = []
    for root, _, files in os.walk("./cogs"):
        for filename in files:
            if filename.endswith(".py") and filename != "__init__.py":
                relative_path = os.path.relpath(os.path.join(root, filename), "./cogs")
                module = relative_path.replace(os.sep, ".")[:-3]
                modules.append(f"cogs.{module}")
    return modules


async def load():
    """Load all discovered cogs at startup."""
    for module in discover_cogs():
        try:
            await client.load_extension(module)
            print(f"{module} is loaded!")
        except Exception as e:
            print(f"Failed to load {module}: {e}")


@client.command(name="reload_all")
@commands.is_owner()
async def reload_all(ctx):
    """Reload or load all cogs (including new ones)."""
    reloaded = []
    failed = []

    for module in discover_cogs():
        try:
            if module in client.extensions:
                await client.reload_extension(module)
                action = "reloaded"
            else:
                await client.load_extension(module)
                action = "loaded"

            reloaded.append(f"{module} ({action})")
        except Exception as e:
            failed.append(f"{module} ({e})")

    msg = []
    if reloaded:
        msg.append(f"? Reloaded/Loaded: {', '.join(reloaded)}")
    if failed:
        msg.append(f"? Failed: {', '.join(failed)}")

    await ctx.send("\n".join(msg) if msg else "No cogs found.")

async def main():
    async with client:
        await load()
        await client.start(DISCORD_API)

if __name__ == "__main__":
    asyncio.run(main())