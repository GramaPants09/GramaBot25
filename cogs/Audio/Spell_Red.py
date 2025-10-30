import discord
from discord.ext import commands
import asyncio
import edge_tts
import aiohttp
import os
import random
import subprocess

VOICE = "en-GB-RyanNeural"
WORD_API_URL = "https://random-word-api.vercel.app/api?words=1"

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

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if before.channel is None and after.channel is not None and not member.bot:
            if member.id in self.active_users:
                return
            print(f"?? Starting spelling bee for {member.display_name}")
            task = asyncio.create_task(self.spelling_bee_loop(member))
            self.active_users[member.id] = task

        elif after.channel is None and before.channel is not None and not member.bot:
            if member.id in self.active_users:
                print(f"? Cancelling spelling bee for {member.display_name}")
                self.active_users[member.id].cancel()
                del self.active_users[member.id]

    async def get_random_word(self):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(WORD_API_URL) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        word = data[0]
                        if len(word) <= 15:
                            return word
                        else:
                            return await self.get_random_word()
        except Exception as e:
            print(f"?? Error fetching word: {e}")
        return "banana"

    async def generate_tts(self, text, filename):
        if os.path.exists(filename):
            os.remove(filename)
        tts = edge_tts.Communicate(text, VOICE)
        await tts.save(filename)

    async def create_full_prompt(self, member_name):
        """Create final_prompt.mp3 from 'Spell the word:' + pipe or word"""
        await self.generate_tts(f"Hey {member_name}Spell the word:", INTRO_TTS_FILE)


        random_num= random.randint(0,100)

        if random_num <= 20:
            second_clip = PIPE_FILE
            print(f"?? {member_name} got the PIPE sound!")
        else:
            word = await self.get_random_word()
            await self.generate_tts(word, WORD_TTS_FILE)
            second_clip = WORD_TTS_FILE
            print(f"? {member_name} must spell: {word}")

        # Create concat list file
        with open(CONCAT_FILE, "w") as f:
            f.write(f"file '{os.path.abspath(INTRO_TTS_FILE)}'\n")
            f.write(f"file '{os.path.abspath(second_clip)}'\n")

        if os.path.exists(FINAL_COMBINED_FILE):
            os.remove(FINAL_COMBINED_FILE)

        cmd = f'ffmpeg -y -f concat -safe 0 -i {CONCAT_FILE} -c copy {FINAL_COMBINED_FILE}'
        subprocess.run(cmd, shell=True)

        os.remove(CONCAT_FILE)

    async def cleanup_audio_files(self):
        for file in [INTRO_TTS_FILE, WORD_TTS_FILE, FINAL_COMBINED_FILE]:
            if os.path.exists(file):
                os.remove(file)
                print(f"Deleted {file}")

    async def spelling_bee_loop(self, member):
        try:
            while True:
                wait_time = random.randint(5 * 60, 60 * 60)
                print(f"? Waiting {wait_time//60} mins for {member.display_name}")
                await asyncio.sleep(wait_time)

                if not member.voice or not member.voice.channel:
                    break

                await self.create_full_prompt(member.display_name)

                try:
                    vc = await member.voice.channel.connect()
                    vc.play(discord.FFmpegPCMAudio(FINAL_COMBINED_FILE))

                    while vc.is_playing():
                        await asyncio.sleep(1)

                    await vc.disconnect()
                    await self.cleanup_audio_files()
                    print(f"?? Finished spelling prompt for {member.display_name}")
                except Exception as e:
                    print(f"Error during VC join/play: {e}")
                    continue

        except asyncio.CancelledError:
            print(f"?? Spelling bee loop cancelled for {member.display_name}")

    @commands.command(name="testbee")
    async def test_bee(self, ctx):
        """Manually test the spelling bee prompt in your VC."""
        member = ctx.author

        if not member.voice or not member.voice.channel:
            await ctx.send("You're not in a voice channel!")
            return

        await self.create_full_prompt(member.display_name)

        try:
            vc = await member.voice.channel.connect()
            vc.play(discord.FFmpegPCMAudio(FINAL_COMBINED_FILE))

            while vc.is_playing():
                await asyncio.sleep(1)

            await vc.disconnect()
            await self.cleanup_audio_files()
            await ctx.send(f"Test complete.")
        except Exception as e:
            await ctx.send(f"Failed to play final prompt: {e}")

    @commands.command(name="testpipe")
    async def test_pipe(self, ctx):
        """Play the pipe sound manually."""
        member = ctx.author

        if not member.voice or not member.voice.channel:
            await ctx.send("You're not in a voice channel!")
            return

        try:
            vc = await member.voice.channel.connect()
            vc.play(discord.FFmpegPCMAudio(PIPE_FILE))

            while vc.is_playing():
                await asyncio.sleep(1)

            await vc.disconnect()
            await ctx.send(f"? Pipe sound test complete.")
        except Exception as e:
            await ctx.send(f"Failed to play pipe.mp3: {e}")

async def setup(client):
    await client.add_cog(Spell_Red(client))