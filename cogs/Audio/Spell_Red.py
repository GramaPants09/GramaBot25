import discord
from discord.ext import commands
import asyncio
import edge_tts
import aiohttp
import os
import random
import subprocess
import time
import cogs.Aura.Other.Aura_Manager as AM

VOICE = "en-GB-RyanNeural"
WORD_API_URLS = [
    "https://random-word-api.herokuapp.com/word?number=1"
]
OWNER_ID = 448854769306435584

# Audio file paths
PIPE_FILE = "audio/pipe.mp3"
SFX_FILE = "audio/sfx.mp3"
INTRO_TTS_FILE = "audio/intro_tts.mp3"
WORD_TTS_FILE = "audio/word_tts.mp3"
FINAL_COMBINED_FILE = "audio/final_prompt.mp3"
CONCAT_FILE = "audio/concat_list.txt"

class Spell_Red(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.active_users = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("Spelling_Red.py is ready!")

    # @commands.Cog.listener()
    # async def on_voice_state_update(self, member, before, after):
    #     if before.channel is None and after.channel is not None and not member.bot:
    #         if member.id in self.active_users:
    #             return
    #         print(f"?? Starting spelling bee for {member.display_name}")
    #         task = asyncio.create_task(self.spelling_bee_loop(member))
    #         self.active_users[member.id] = task

    #     elif after.channel is None and before.channel is not None and not member.bot:
    #         if member.id in self.active_users:
    #             print(f"? Cancelling spelling bee for {member.display_name}")
    #             self.active_users[member.id].cancel()
    #             del self.active_users[member.id]

    # async def get_random_word(self):
    #     # Try several online APIs first
    #     retries = 2
    #     timeout = aiohttp.ClientTimeout(total=8)
    #     for url in WORD_API_URLS:
    #         for attempt in range(1, retries + 1):
    #             try:
    #                 async with aiohttp.ClientSession(timeout=timeout) as session:
    #                     async with session.get(url) as resp:
    #                         text = await resp.text()
    #                         if resp.status != 200:
    #                             print(f"?? Word API {url} returned status {resp.status} (attempt {attempt}): {text}")
    #                             continue
    #                         # try parse JSON
    #                         try:
    #                             data = await resp.json()
    #                         except Exception:
    #                             # fallback: use plain text
    #                             data = text

    #                         # normalize different API response shapes
    #                         word = None
    #                         if isinstance(data, list) and data:
    #                             word = data[0]
    #                         elif isinstance(data, dict):
    #                             # some APIs return object with 'word' key
    #                             word = data.get("word") or next(iter(data.values()), None)
    #                         elif isinstance(data, str):
    #                             # could be plain text or newline-separated
    #                             word = data.strip().split()[-1]

    #                         if not isinstance(word, str):
    #                             print(f"?? Unexpected word format from {url} (attempt {attempt}): {data}")
    #                             continue

    #                         word = word.strip().strip('"')
    #                         if ' ' in word or ',' in word:
    #                             print(f"?? Word contains space or comma from {url} (attempt {attempt}): '{word}', retrying.")
    #                             continue
    #                         if 0 < len(word) <= 15:
    #                             return word
    #                         else:
    #                             print(f"?? Word length invalid ({len(word)}) from {url} (attempt {attempt}), retrying.")
    #                             continue
    #             except Exception as e:
    #                 print(f"?? Error fetching word from {url} (attempt {attempt}): {e}")
    #             await asyncio.sleep(0.5)

    #     # Fallback: use local word lists in cogs/text_files (noun.txt, adj.txt)
    #     local_paths = ["cogs/text_files/noun.txt", "cogs/text_files/adj.txt", "cogs/text_files/noun.txt"]
    #     for p in local_paths:
    #         try:
    #             with open(p, "r", encoding="utf-8") as f:
    #                 lines = [l.strip() for l in f if l.strip() and ' ' not in l.strip() and ',' not in l.strip()]
    #                 if lines:
    #                     return random.choice(lines)
    #         except Exception as e:
    #             print(f"?? Could not read local words from {p}: {e}")

    #     print("?? Falling back to default word 'smurg'")
    #     return "smurg"

    # async def generate_tts(self, text, filename):
    #     if os.path.exists(filename):
    #         os.remove(filename)
    #     tts = edge_tts.Communicate(text, VOICE)
    #     await tts.save(filename)

    # async def create_full_prompt(self, member_name):
    #     """Create final_prompt.mp3 from 'Spell the word:' + pipe or word
    #     Returns the word the user should spell (str) or None if no word (pipe).
    #     """
    #     await self.generate_tts(f"Hey {member_name} Spell the word:", INTRO_TTS_FILE)

    #     random_num = random.randint(0, 100)
    #     word = None

    #     # pipe sound (disabled threshold kept but effectively never triggers here)
    #     if random_num <= -5:
    #         second_clip = PIPE_FILE
    #         print(f"?? {member_name} got the PIPE sound!")

    #     # 40% chance of backwards
    #     elif 5 >= random_num:
    #         base_word = await self.get_random_word()
    #         word = base_word[::-1]
    #         await self.generate_tts(word, WORD_TTS_FILE)
    #         second_clip = WORD_TTS_FILE
    #         print(f"? {member_name} must spell (backwards): {word}")

    #     else:
    #         word = await self.get_random_word()
    #         await self.generate_tts(word, WORD_TTS_FILE)
    #         second_clip = WORD_TTS_FILE
    #         print(f"? {member_name} must spell: {word}")

    #     # Create concat list file, combines the introTTS with the secondclip.
    #     with open(CONCAT_FILE, "w") as f:
    #         f.write(f"file '{os.path.abspath(INTRO_TTS_FILE)}'\n")
    #         f.write(f"file '{os.path.abspath(second_clip)}'\n")

    #     if os.path.exists(FINAL_COMBINED_FILE):
    #         os.remove(FINAL_COMBINED_FILE)

    #     cmd = f'ffmpeg -y -f concat -safe 0 -i {CONCAT_FILE} -c copy {FINAL_COMBINED_FILE}'
    #     subprocess.run(cmd, shell=True)

    #     os.remove(CONCAT_FILE)

    #     return word



    # async def cleanup_audio_files(self):
    #     for file in [INTRO_TTS_FILE, WORD_TTS_FILE, FINAL_COMBINED_FILE]:
    #         if os.path.exists(file):
    #             os.remove(file)
    #             print(f"Deleted {file}")

    # async def spelling_bee_loop(self, member):
    #     try:
    #         while True:
    #             wait_time = random.randint(5 * 60, 60 * 60)
    #             print(f"? Waiting {wait_time//60} mins for {member.display_name}")
    #             await asyncio.sleep(wait_time)

    #             if not member.voice or not member.voice.channel or member.guild.id == 1214330363581825194:
    #                 break

    #             # create the audio prompt and receive the target word (or None for pipe)
    #             word = await self.create_full_prompt(member.display_name)

    #             try:
    #                 vc = await member.voice.channel.connect()
    #                 vc.play(discord.FFmpegPCMAudio(FINAL_COMBINED_FILE))

    #                 while vc.is_playing():
    #                     await asyncio.sleep(1)

    #                 await vc.disconnect()
    #                 await self.cleanup_audio_files()
    #                 print(f"?? Finished spelling prompt for {member.display_name}")

    #                 # Create the channel where user can spell the word to get aura
    #                 guild = member.guild
    #                 channel_name = f"spell-{member.display_name}-{member.id}"[:100]
    #                 overwrites = {
    #                     guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False),
    #                     member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    #                     guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    #                 }
    #                 try:
    #                     private_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
    #                     await private_channel.send(f"{member.mention} Spell the word here. You have 30 seconds — the first message you send will be recorded.")

    #                     def check(m):
    #                         return m.channel.id == private_channel.id and m.author.id == member.id

    #                     # default to -1 (failure) unless overwritten by a correct response
    #                     spelling_time = -1
    #                     start = time.monotonic()
    #                     try:
    #                         msg = await self.client.wait_for('message', check=check, timeout=30)
    #                         elapsed = int(time.monotonic() - start)
    #                         user_answer = msg.content.strip().lower()
    #                         if word is None:
    #                             spelling_time = -1
    #                             print(f"No target word (pipe). Marking time -1 for {member.display_name}.")
    #                             await private_channel.send("No word was set for this prompt.")
    #                         else:
    #                             if user_answer == word.lower():
    #                                 spelling_time = elapsed
    #                                 await private_channel.send(f"Correct — time: {spelling_time} seconds.")
    #                                 print(f"{member.display_name} spelled correctly in {spelling_time}s")
    #                             else:
    #                                 spelling_time = -1
    #                                 await private_channel.send(f"Incorrect. The correct spelling was: \"{word}\".")
    #                                 print(f"{member.display_name} spelled incorrectly ({msg.content}); expected {word}")

    #                     except asyncio.TimeoutError:
    #                         spelling_time = -1
    #                         await private_channel.send("Timed out waiting for a response.")

    #                     # small delay so the user sees the confirmation
    #                     await asyncio.sleep(3)

    #                     # process the spelling result in the temporary channel, then delete it
    #                     try:
    #                         await self.process_spelling_result(member, spelling_time, private_channel)
    #                     except Exception as e:
    #                         print(f"Error in process_spelling_result: {e}")

    #                     try:
    #                         await private_channel.delete()
    #                     except Exception:
    #                         pass
    #                 except Exception as e:
    #                     print(f"Error creating/waiting in private channel: {e}")

    #             except Exception as e:
    #                 print(f"Error during VC join/play: {e}")
    #                 continue

    #     except asyncio.CancelledError:
    #         print(f"?? Spelling bee loop cancelled for {member.display_name}")

    # async def process_spelling_result(self, member, spelling_time: int, channel=None):
    #     """Placeholder to handle the spelling result after the private channel is deleted.

    #     - `spelling_time` is an int: seconds taken, or -1 for incorrect/timeout.
    #     Implement persistence, role assignment, logging, or other follow-up here.
    #     """
    #     try:
    #         aura_manager = self.client.get_cog("Aura_Manager")
    #         if spelling_time == -1:
    #             # failed or timed out
    #             try:
    #                 if channel:
    #                     await channel.send(f"{member.mention} You did not spell the word correctly or timed out. You earned 0 aura.")
    #                 else:
    #                     await member.send(f"You did not spell the word correctly or timed out. You earned 0 aura.")
    #             except Exception:
    #                 print(f"Could not notify user {member.display_name} about failed spelling.")
    #             print(f"[RESULT] {member.display_name}: failed or timed out (time={spelling_time}).")
    #             return

    #         # success: compute aura award. More time left => more aura.
    #         # using 30s window: award = max(1, 30 - spelling_time)
    #         # award = max(1, 30 - int(spelling_time))
    #         award =  300 - (spelling_time * 10)

    #         if aura_manager is not None:
    #             await aura_manager.add_aura(member.guild.id, member.id, award)
    #             total = await aura_manager.get_aura(member.guild.id, member.id)
    #         else:
    #             total = None

    #         try:
    #             if channel:
    #                 if total is not None:
    #                     await channel.send(f"{member.mention} Correct! You spelled it in {spelling_time} seconds and earned {award} aura. Total aura: {total}.")
    #                 else:
    #                     await channel.send(f"{member.mention} Correct! You spelled it in {spelling_time} seconds and earned {award} aura.")
    #             else:
    #                 if total is not None:
    #                     await member.send(f"Correct! You spelled it in {spelling_time} seconds and earned {award} aura. Total aura: {total}.")
    #                 else:
    #                     await member.send(f"Correct! You spelled it in {spelling_time} seconds and earned {award} aura.")
    #         except Exception:
    #             print(f"Could not notify user {member.display_name} about success.")

    #         print(f"[RESULT] {member.display_name}: success in {spelling_time}s, +{award} aura.")
    #     except Exception as e:
    #         print(f"Error processing spelling result for {member.display_name}: {e}")

        

            
            

    #     except Exception as e:
    #         print(f"Error processing spelling result for {member.display_name}: {e}")

    #     # wait 4 seconds before cleaning up
    #     await asyncio.sleep(4)
    #     # try:
    #     #     await private_channel.delete()
    #     # except Exception:
    #     #     pass

    # @commands.command(name="testbee")
    # async def test_bee(self, ctx):
    #     """Manually test the spelling bee prompt in your VC."""
    #     # restrict to owner
    #     if ctx.author.id != OWNER_ID:
    #         await ctx.send("You are not authorized to run this command.")
    #         return
    #     member = ctx.author

    #     if not member.voice or not member.voice.channel:
    #         await ctx.send("You're not in a voice channel!")
    #         return
    #     # create the audio prompt and get the target word
    #     word = await self.create_full_prompt(member.display_name)

    #     try:
    #         vc = await member.voice.channel.connect()
    #         vc.play(discord.FFmpegPCMAudio(FINAL_COMBINED_FILE))

    #         while vc.is_playing():
    #             await asyncio.sleep(1)

    #         await vc.disconnect()
    #         await self.cleanup_audio_files()
    #     except Exception as e:
    #         await ctx.send(f"Failed to play final prompt: {e}")
    #         return

    #     # Create the private channel and wait for user's first response (30s)
    #     guild = member.guild
    #     channel_name = f"spell-{member.display_name}-{member.id}"[:100]
    #     overwrites = {
    #         guild.default_role: discord.PermissionOverwrite(view_channel=False, send_messages=False),
    #         member: discord.PermissionOverwrite(view_channel=True, send_messages=True),
    #         guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
    #     }

    #     try:
    #         private_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
    #         await private_channel.send(f"{member.mention} Spell the word here. You have 30 seconds — the first message you send will be recorded.")

    #         def check(m):
    #             return m.channel.id == private_channel.id and m.author.id == member.id

    #         spelling_time = -1
    #         start = time.monotonic()
    #         try:
    #             msg = await self.client.wait_for('message', check=check, timeout=30)
    #             elapsed = int(time.monotonic() - start)
    #             user_answer = msg.content.strip().lower()
    #             if word is None:
    #                 spelling_time = -1
    #                 await private_channel.send("No word was set for this prompt.")
    #             else:
    #                 if user_answer == word.lower():
    #                     spelling_time = elapsed
    #                     await private_channel.send(f"Correct — time: {spelling_time} seconds.")
    #                 else:
    #                     spelling_time = -1
    #                     await private_channel.send(f"Incorrect. The correct spelling was: \"{word}\".")

    #         except asyncio.TimeoutError:
    #             spelling_time = -1
    #             await private_channel.send("Timed out waiting for a response.")

    #         # small delay so the user sees the confirmation
    #         await asyncio.sleep(3)

    #         # call the result handler in the private channel, then delete it
    #         try:
    #             await self.process_spelling_result(member, spelling_time, private_channel)
    #         except Exception as e:
    #             print(f"Error in process_spelling_result (testbee): {e}")

    #         try:
    #             await private_channel.delete()
    #         except Exception:
    #             pass

    #         # report back in invoking channel
    #         if spelling_time == -1:
    #             await ctx.send(f"Test complete: incorrect or timed out.")
    #         else:
    #             await ctx.send(f"Test complete: correct in {spelling_time} seconds.")

    #     except Exception as e:
    #         await ctx.send(f"Failed to create/wait in private channel: {e}")

    # @commands.command(name="testpipe")
    # async def test_pipe(self, ctx):
    #     """Play the pipe sound manually."""
    #     # restrict to owner
    #     if ctx.author.id != OWNER_ID:
    #         await ctx.send("You are not authorized to run this command.")
    #         return
    #     member = ctx.author

    #     if not member.voice or not member.voice.channel:
    #         await ctx.send("You're not in a voice channel!")
    #         return

    #     try:
    #         vc = await member.voice.channel.connect()
    #         vc.play(discord.FFmpegPCMAudio(PIPE_FILE))

    #         while vc.is_playing():
    #             await asyncio.sleep(1)

    #         await vc.disconnect()
    #         await ctx.send(f"? Pipe sound test complete.")
    #     except Exception as e:
    #         await ctx.send(f"Failed to play pipe.mp3: {e}")


    # @commands.command(name="testbackwards")
    # async def test_backwards(self, ctx):
    #     """Play the backwards, which is funny."""
    #     # restrict to owner
    #     if ctx.author.id != OWNER_ID:
    #         await ctx.send("You are not authorized to run this command.")
    #         return
    #     member = ctx.author

    #     if not member.voice or not member.voice.channel:
    #         await ctx.send("You're not in a voice channel!")
    #         return

    #     try:
    #         vc = await member.voice.channel.connect()
    #         vc.play(discord.FFmpegPCMAudio(PIPE_FILE))

    #         while vc.is_playing():
    #             await asyncio.sleep(1)

    #         await vc.disconnect()
    #         await ctx.send(f"? Pipe sound test complete.")

    #     except Exception as e:
    #         await ctx.send(f"Failed to play pipe.mp3: {e}")

async def setup(client):
    await client.add_cog(Spell_Red(client))

    # end of file helper: placeholder for processing results