import discord
from discord.ext import commands
import yt_dlp
import os
import asyncio

TARGET_USER_ID = 448854769306435584
SFX_URL = "https://www.youtube.com/watch?v=FRj_hAO1Sgs"
SFX_FILE = "audio/no_ben.mp3"

class AutoUnmutePlaySFX(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("AutoUnmutePlaySFX Cog is ready!")

        # Download sound once when bot loads
        await self.download_sfx_once()

    async def download_sfx_once(self):
        if not os.path.exists(SFX_FILE):
            print("Downloading sound effect...")
            ydl_opts = {
                'format': 'bestaudio/best',
                'quiet': True,
                'outtmpl': 'sfx.%(ext)s',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([SFX_URL])
            print("Sound effect downloaded!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.id != TARGET_USER_ID:
            return

        if after.channel is None:
            return  # User left VC

        # Only react if they were muted or deafened
        if not after.mute and not after.deaf:
            return

        try:
            # Unmute / undeafen
            changed = False
            if after.mute:
                await member.edit(mute=False)
                changed = True
            if after.deaf:
                await member.edit(deafen=False)
                changed = True

            if changed:
                print(f"? Unmuted/undeafened {member.display_name}")

            voice_client = member.guild.voice_client
            already_in_channel = voice_client and voice_client.channel == after.channel

            if already_in_channel:
                print("Bot is already in the VC.")
                return

            # Join VC
            vc = await after.channel.connect()

            # Play the pre-downloaded SFX
            if os.path.exists(SFX_FILE):
                source = discord.FFmpegPCMAudio(SFX_FILE)
                vc.play(source)
                print("Playing sound effect...")

                while vc.is_playing():
                    await asyncio.sleep(1)

            # Leave VC after playback
            await vc.disconnect()
            print("Bot left VC after sound.")

        except discord.Forbidden:
            print("?? Permission error: Cannot unmute or join VC.")
        except Exception as e:
            print(f"?? Error in voice state handler: {e}")

async def setup(client):
    await client.add_cog(AutoUnmutePlaySFX(client))
