import discord
from discord.ext import commands
import os
import asyncio
import edge_tts
import nacl  # Ensure pynacl is installed
import OutputText

class VoiceAI(commands.Cog):
    """Cog for joining voice channels and speaking with TTS."""

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("VoiceAI Cog is online!")

    @commands.command()
    async def join(self, ctx):
        """Joins the user's voice channel."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(OutputText.output(ctx.guild.id,"You're not in a voice channel."))
            return

        channel = ctx.author.voice.channel
        
        if ctx.voice_client:
            await ctx.voice_client.move_to(channel)
            await ctx.send(OutputText.output(ctx.guild.id,"Moved to your channel."))
        else:
            try:
                await channel.connect()
                await ctx.send(OutputText.output(ctx.guild.id,f"Connected to {channel}!"))
            except Exception as e:
                await ctx.send(OutputText.output(ctx.guild.id,f"Error connecting: {e}"))

    @commands.command(name="leave")
    async def leave(self, ctx):
        """Leaves the voice channel."""
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await ctx.send(OutputText.output(ctx.guild.id,"Disconnected from the voice channel."))
        else:
            await ctx.send(OutputText.output(ctx.guild.id,"I'm not in a voice channel."))

    @commands.command(name="speak")
    async def speak(self, ctx, *, text):
        """Speaks the given text using TTS."""
        if ctx.voice_client is None:
            await ctx.send("Join a voice channel first!")
            return

        voice = "en-GB-RyanNeural"
        #voice = "hi-IN-MadhurNeural"
        #voice = "en-US-RogerNeural"
        output_file = "audio/voice.mp3"

        try:
            # Generate TTS audio
            tts = edge_tts.Communicate(text, voice)
            await tts.save(output_file)
            
            # Ensure file was created
            if not os.path.exists(output_file):
                await ctx.send(OutputText.output(ctx.guild.id,"TTS failed: No audio file created."))
                return
            
            def after_playback(error):
                if error:
                    print(f"Playback error: {error}")
                if os.path.exists(output_file):
                    os.remove(output_file)
            
            # Play audio
            if not ctx.voice_client.is_playing():
                source = discord.FFmpegPCMAudio(output_file)
                ctx.voice_client.play(source, after=after_playback)
                await ctx.send(OutputText.output(ctx.guild.id,f"Saying: {text}"))
            else:
                await ctx.send(OutputText.output(ctx.guild.id,"Already speaking!"))
            
            # Wait for playback
            while ctx.voice_client.is_playing():
                await asyncio.sleep(1)
            
        except Exception as e:
            await ctx.send(OutputText.output(ctx.guild.id,f"Error: {e}"))

async def setup(client):
    await client.add_cog(VoiceAI(client))
