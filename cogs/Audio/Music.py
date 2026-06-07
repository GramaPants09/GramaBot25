from typing import Optional
import discord
from discord.ext import commands
import asyncio
import yt_dlp
import json
import os
import OutputText
import subprocess
import random
from pydub import AudioSegment

QUEUE_FILE = "cogs/jsonfiles/music_queue.json"

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch1',
    'geo_bypass': True,
    'nocheckcertificate': True
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.queue = self.load_queue()
        # All runtime playback state is per-guild (keyed by int guild id) so
        # multiple servers don't clobber each other. The active voice client is
        # always read from ctx.voice_client / guild.voice_client, never cached.
        self.is_playing = {}     # gid -> bool
        self.loop_song = {}      # gid -> bool
        self.loop_queue = {}     # gid -> bool
        self.volumes = {}        # gid -> float
        self.current_song = {}   # gid -> str
        self.local_queue = []
        self.local_audio_process = None
        self.local_paused = False


    def _vol(self, gid):
        return self.volumes.get(gid, 0.5)

    def load_queue(self):
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, "r") as f:
                return json.load(f)
        return {}

    def save_queue(self):
        with open(QUEUE_FILE, "w") as f:
            json.dump(self.queue, f)

    @commands.command()
    async def debugmsg(self, ctx):
        msg = ctx.message

        lines = [
            "**?? Raw Message Content:**",
            f"```{msg.content}```",
            "",
            "**?? Channel Mentions (`channel_mentions`):**",
        ]

        if msg.channel_mentions:
            for ch in msg.channel_mentions:
                lines.append(
                    f"- {ch.name} | id={ch.id} | type={type(ch).__name__}"
                )
        else:
            lines.append("- (none)")

        lines.extend([
            "",
            "**?? Message Mentions Dict:**",
            f"```{msg.mentions}```",
        ])

        await ctx.send("\n".join(lines))


    async def ensure_voice(self, ctx):
        target_channel = None

        # 1?? Use mentioned voice channel (#! or # both end up here)
        if ctx.message.channel_mentions:
            ch = ctx.message.channel_mentions[0]
            if isinstance(ch, discord.VoiceChannel):
                target_channel = ch
            else:
                await ctx.send(
                    OutputText.output(
                        ctx.guild.id,
                        "That channel is not a voice channel."
                    )
                )
                return False

        # 2?? Fallback to user's current VC
        elif ctx.author.voice and ctx.author.voice.channel:
            target_channel = ctx.author.voice.channel

        else:
            await ctx.send(
                OutputText.output(
                    ctx.guild.id,
                    "You're not in a voice channel. Mention one like `#!hell hole`."
                )
            )
            return False

        vc = ctx.voice_client

        if vc and vc.is_connected():
            if vc.channel != target_channel:
                await vc.move_to(target_channel)
        else:
            await target_channel.connect()

        return True

    async def get_stream_url(self, query):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
        if 'entries' in data:
            data = data['entries'][0]
        return data['url'], data.get('title', 'Unknown Title'), data.get('thumbnail', '')

    async def play_next(self, ctx):
        gid = ctx.guild.id
        guild_id = str(gid)
        if self.loop_song.get(gid) and self.current_song.get(gid):
            await self.play_song(ctx, self.current_song[gid])
        elif self.queue.get(guild_id):
            self.is_playing[gid] = True
            song = self.queue[guild_id][0] if self.loop_queue.get(gid) else self.queue[guild_id].pop(0)
            self.current_song[gid] = song
            self.save_queue()
            await self.play_song(ctx, song)
        else:
            self.is_playing[gid] = False
            await ctx.send(OutputText.output(gid, "Queue is empty. Leaving voice channel."))
            if ctx.voice_client:
                await ctx.voice_client.disconnect()

    async def play_song(self, ctx, query):
        gid = ctx.guild.id
        vc = ctx.voice_client
        if vc is None:
            self.is_playing[gid] = False
            return
        try:
            stream_url, title, thumbnail = await self.get_stream_url(query)
        except Exception:
            await ctx.send(OutputText.output(gid, "Could not find the song."))
            # Ensure forward progress so a bad track can't loop forever.
            if self.loop_song.get(gid):
                self.loop_song[gid] = False
                self.current_song[gid] = None
            elif self.loop_queue.get(gid) and self.queue.get(str(gid)):
                self.queue[str(gid)].pop(0)
                self.save_queue()
            await self.play_next(ctx)
            return

        def after_playing(error):
            fut = asyncio.run_coroutine_threadsafe(self.play_next(ctx), self.client.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error playing next song: {e}")

        source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
        vc.play(discord.PCMVolumeTransformer(source, volume=self._vol(gid)), after=after_playing)

        embed = discord.Embed(title="Now Playing", description=title, color=discord.Color.green())
        if thumbnail:
            embed.set_thumbnail(url=thumbnail)
        await ctx.send(embed=embed)

    @commands.command()
    async def monke(self, ctx):
        await self.play(ctx, query="monkey type beat")

    @commands.command(aliases=["depressed", "sadboy", "sadboi"])
    async def sad(self, ctx):
        # Use the same intro-style local playback logic: join VC, play file, then disconnect
        member = ctx.author
        if not member.voice or not member.voice.channel:
            await ctx.send(OutputText.output(ctx.guild.id, "You're not in a voice channel."))
            return

        meme_file_name = "audio/music.mp3"
        speed = 1.0

        # random chance to reverse the clip (keeps behavior consistent with intro triggers)
        rand = random.randint(1, 50)
        if rand <= 3:
            try:
                audio_file = AudioSegment.from_file(meme_file_name, format="mp3")
                reversed_audio = audio_file.reverse()
                reversed_audio.export("reversed_sad.mp3", format="mp3")
                meme_file_name = "reversed_sad.mp3"
            except Exception as e:
                print(f"Error creating reversed clip: {e}")

        meme_file = os.path.abspath(meme_file_name)

        vc: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=member.guild)

        if vc is None or not vc.is_connected():
            vc = await member.voice.channel.connect()

        if not os.path.exists(meme_file):
            await ctx.send(OutputText.output(ctx.guild.id, f"Audio file not found: {meme_file_name}"))
            return

        ffmpeg_opts = {
            'before_options': '',
            'options': f'-vn -af "atempo={speed}"'
        }

        def after_playing_sad(error):
            coro = vc.disconnect()
            fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Failed to disconnect after sad clip: {e}")

        source = discord.FFmpegPCMAudio(meme_file, **ffmpeg_opts)
        vc.play(source, after=after_playing_sad)

        embed = discord.Embed(title="Now Playing", description="Local: music.mp3", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(aliases=["turtle", "fuck", "turt", "jazz"])
    async def music(self, ctx):
        await self.play(ctx, query="turtle moaning")

    @commands.command()
    async def play(self, ctx, *, query: str):
        if not await self.ensure_voice(ctx):
            return
        
        # Remove channel mentions from query
        for ch in ctx.message.channel_mentions:
            query = query.replace(f"<#{ch.id}>", "").strip()

        if not query:
            await ctx.send(OutputText.output(ctx.guild.id, "No song specified."))
            return

        queries = [query]
        try:
            from cogs.Audio.spotify import is_spotify_url, expand_spotify

            if is_spotify_url(query):
                queries = expand_spotify(query)
                if not queries:
                    await ctx.send(OutputText.output(ctx.guild.id, "Couldn't read that Spotify link."))
                    return
                await ctx.send(OutputText.output(
                    ctx.guild.id, f"Pulling {len(queries)} track(s) off Spotify..."))
        except ImportError:
            pass
        except Exception as e:
            await ctx.send(OutputText.output(ctx.guild.id, f"Spotify error: {e}"))
            return

        guild_id = str(ctx.guild.id)
        self.queue.setdefault(guild_id, []).extend(queries)
        self.save_queue()

        if not self.is_playing.get(ctx.guild.id):
            await self.play_next(ctx)
        else:
            await ctx.send(OutputText.output(ctx.guild.id, "Added to the queue!"))

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send(OutputText.output(ctx.guild.id,"Skipping song..."))
        else:
            await ctx.send(OutputText.output(ctx.guild.id,"No song is playing."))

    @commands.command()
    async def queue(self, ctx):
        guild_id = str(ctx.guild.id)
        if guild_id in self.queue and self.queue[guild_id]:
            embed = discord.Embed(title="Music Queue", color=discord.Color.blue())
            for index, song in enumerate(self.queue[guild_id], start=1):
                embed.add_field(name=f"{index}.", value=song, inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(OutputText.output(ctx.guild.id,"Queue is empty."))

    @commands.command()
    async def volume(self, ctx, volume: int):
        gid = ctx.guild.id
        if ctx.voice_client and ctx.voice_client.source:
            self.volumes[gid] = volume / 100
            ctx.voice_client.source.volume = self.volumes[gid]
            await ctx.send(OutputText.output(gid, f"Volume set to {volume}%"))
        else:
            await ctx.send(OutputText.output(gid, "No audio playing."))

    @commands.command()
    async def loop(self, ctx, mode: str):
        gid = ctx.guild.id
        if mode == "song":
            self.loop_song[gid] = True
            self.loop_queue[gid] = False
            await ctx.send(OutputText.output(gid, "Looping current song."))
        elif mode == "queue":
            self.loop_queue[gid] = True
            self.loop_song[gid] = False
            await ctx.send(OutputText.output(gid, "Looping queue."))
        elif mode == "off":
            self.loop_song[gid] = False
            self.loop_queue[gid] = False
            await ctx.send(OutputText.output(gid, "Looping disabled."))
        else:
            await ctx.send(OutputText.output(gid, "Invalid mode! Use 'song', 'queue', or 'off'."))

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send(OutputText.output(ctx.guild.id,"Music paused."))
        else:
            await ctx.send(OutputText.output(ctx.guild.id,"Nothing to pause."))

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send(OutputText.output(ctx.guild.id,"Music resumed."))
        else:
            await ctx.send(OutputText.output(ctx.guild.id,"Nothing to resume."))

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client:
            gid = ctx.guild.id
            if ctx.voice_client.is_playing() or ctx.voice_client.is_paused():
                ctx.voice_client.stop()
            self.queue[str(gid)] = []
            self.save_queue()
            self.is_playing[gid] = False
            self.current_song[gid] = None
            await ctx.voice_client.disconnect()
            await ctx.send(OutputText.output(gid, "Stopped playback and left voice channel."))
        else:
            await ctx.send(OutputText.output(ctx.guild.id, "I'm not in a voice channel."))

    @commands.command()
    async def clear_queue(self, ctx):
        guild_id = str(ctx.guild.id)
        self.queue[guild_id] = []
        self.save_queue()
        await ctx.send(OutputText.output(ctx.guild.id,"Queue cleared."))

    @commands.Cog.listener()
    async def on_ready(self):
        print("Music cog is ready!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Triggers intro music when a specific user joins,
        and outro music when they leave a voice channel.
        """

        spencer_outro = ""
        rand = random.randint(1,10)
        # if rand >= 0:
        if rand == 1:
            spencer_outro = "audio/Spener_Ding.mp3"
        else:
            spencer_outro = "audio/Spener_Ding_fake.mp3"


        # --- Intro triggers (existing ones) ---
        intro_triggers = {
            448854769306435584: ("audio/newIntroMusic.mp3", 1.0),               # GramaPants09
            915043571940343919: ("audio/vineboom.mp3", 1.0),           # Friend
            1135674124585410662: ("audio/laugh_track.mp3", 1.0),      # spencer user
            691050015078219786: ("audio/fog_horn.mp3", 1.0),
            525799573445410817: ("audio/km.mp3", 1.0)
        }

        # --- Outro triggers (new ones) ---
        outro_triggers = {
            448854769306435584: ("audio/outrosong.mp3", 1.0),  # Example outro for same user
            915043571940343919: ("audio/ryan_outro.mp3", 1.0),
            1135674124585410662: (spencer_outro, 1.0)
        }

        


        # --------------------------
        # USER JOINS (INTRO)
        # --------------------------
        if member.id in intro_triggers and after.channel is not None and before.channel != after.channel:
            meme_file_name, speed = intro_triggers[member.id] # meme_file_name is the audio file name

            # random chance for jingle to be reversed, which is funny
            rand = random.randint(1,50)
            if rand <= 3:
            # if rand >= 0:
                audio_file = AudioSegment.from_file(meme_file_name, format="mp3")
                reversed_audio = audio_file.reverse()
                reversed_audio.export("reversed_intro.mp3", format="mp3")
                meme_file_name = "reversed_intro.mp3"

            meme_file = os.path.abspath(meme_file_name)

            vc: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=member.guild)

            if vc is None or not vc.is_connected():
                vc = await after.channel.connect()

            if not os.path.exists(meme_file):
                print(f"[ERROR] Intro file {meme_file} not found.")
                return

            ffmpeg_opts = {
                'before_options': '',
                'options': f'-vn -af "atempo={speed}"'
            }

            source = discord.FFmpegPCMAudio(meme_file, **ffmpeg_opts)

            def after_playing_intro(error):
                coro = vc.disconnect()
                fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
                try:
                    fut.result()
                except Exception as e:
                    print(f"Failed to disconnect after intro: {e}")

            vc.play(source, after=after_playing_intro)

        # --------------------------
        # USER LEAVES (OUTRO)
        # --------------------------
        elif member.id in outro_triggers and before.channel is not None and after.channel is None:
            meme_file_name, speed = outro_triggers[member.id]

            # random chance for jingle to be reversed, which is funny
            rand = random.randint(1,50)
            if rand <= 3:
            # if rand >= 0:
                audio_file = AudioSegment.from_file(meme_file_name, format="mp3")
                reversed_audio = audio_file.reverse()
                reversed_audio.export("reversed_outro.mp3", format="mp3")
                meme_file_name = "reversed_outro.mp3"


            meme_file = os.path.abspath(meme_file_name)

            if not os.path.exists(meme_file):
                print(f"[ERROR] Outro file {meme_file} not found.")
                return

            # Get the channel the user left (so the bot can join)
            channel = before.channel
            vc: discord.VoiceClient = discord.utils.get(self.client.voice_clients, guild=member.guild)

            if vc is None or not vc.is_connected():
                vc = await channel.connect()

            ffmpeg_opts = {
                'before_options': '',
                'options': f'-vn -af "atempo={speed}"'
            }

            source = discord.FFmpegPCMAudio(meme_file, **ffmpeg_opts)

            def after_playing_outro(error):
                coro = vc.disconnect()
                fut = asyncio.run_coroutine_threadsafe(coro, self.client.loop)
                try:
                    fut.result()
                except Exception as e:
                    print(f"Failed to disconnect after outro: {e}")

            vc.play(source, after=after_playing_outro)


    async def play_song_local(self, query):
        try:
            stream_url, title, _ = await self.get_stream_url(query)
        except Exception:
            return "Could not find the song."

        from Local_Voice import convert_to_pcm
        from Local_Voice.voice_loop_entrypoint import animate_fish_from_file

        temp_filename = "audio/local_stream.wav"
        command = [
            "ffmpeg", "-y", "-i", stream_url,
            "-ar", "44100", "-ac", "1", "-f", "wav", temp_filename
        ]
        subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        pcm_file = convert_to_pcm(temp_filename)

        if self.local_audio_process and self.local_audio_process.poll() is None:
            self.local_audio_process.kill()

        self.local_audio_process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", pcm_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        self.local_paused = False

        try:
            asyncio.create_task(animate_fish_from_file(pcm_file, tail_on_silence=True))
        except Exception as e:
            print(f"[Fish Animation Error] {e}")

        return f"Now playing {title}."

    async def skip_local(self):
        if self.local_audio_process and self.local_audio_process.poll() is None:
            self.local_audio_process.kill()

        if self.local_queue:
            self.local_queue.pop(0)
            if self.local_queue:
                return await self.play_song_local(self.local_queue[0])
            return "Skipped. No more songs in the local queue."
        return "Nothing to skip."

    async def stop_local(self):
        if self.local_audio_process and self.local_audio_process.poll() is None:
            self.local_audio_process.kill()
        self.local_queue.clear()
        return "Stopped playback and cleared the local queue."

    async def queue_local(self):
        if self.local_queue:
            return "Local Queue:\n" + "\n".join(f"{i+1}. {song}" for i, song in enumerate(self.local_queue))
        return "The local queue is empty."

    async def clear_local_queue(self):
        self.local_queue.clear()
        return "Local queue cleared manually."

    async def pause_local(self):
        if self.local_audio_process and not self.local_paused:
            os.system(f"kill -STOP {self.local_audio_process.pid}")
            self.local_paused = True
            return "Paused local audio."
        return "Nothing is playing or it's already paused."

    async def resume_local(self):
        if self.local_audio_process and self.local_paused:
            os.system(f"kill -CONT {self.local_audio_process.pid}")
            self.local_paused = False
            return "Resumed local audio."
        return "Nothing to resume."

    async def download_and_convert(self, query):
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=True))
        if 'entries' in data:
            data = data['entries'][0]
        title = data['title']
        filename = ytdl.prepare_filename(data)

        wav_file = filename.replace('.webm', '.wav').replace('.m4a', '.wav')
        if not os.path.exists(wav_file):
            subprocess.run(["ffmpeg", "-y", "-i", filename, "-ar", "16000", "-ac", "1", wav_file])
        return wav_file, title

    async def animate_from_file(self, wav_file):
        try:
            from Local_Voice import voice_loop_entrypoint
            await voice_loop_entrypoint.animate_fish_from_file(wav_file)
        except Exception as e:
            print(f"[Fish Animation Error] {e}")

    # ------------------------------------------------------------------
    # Agent-facing helpers (driven by the AgentBrain tools, no ctx needed)
    # ------------------------------------------------------------------
    async def _agent_play_next(self, guild, text_channel):
        gid_i = guild.id
        gid = str(gid_i)
        vc = guild.voice_client
        # Iterate (not recurse) past failures so a run of dead links can't blow
        # the stack or wedge the player.
        while True:
            if self.loop_song.get(gid_i) and self.current_song.get(gid_i):
                song = self.current_song[gid_i]
            elif self.queue.get(gid):
                song = self.queue[gid][0] if self.loop_queue.get(gid_i) else self.queue[gid].pop(0)
                self.current_song[gid_i] = song
                self.save_queue()
            else:
                self.is_playing[gid_i] = False
                if vc:
                    await vc.disconnect()
                return

            self.is_playing[gid_i] = True
            if vc is None:
                self.is_playing[gid_i] = False
                return

            try:
                stream_url, title, thumbnail = await self.get_stream_url(song)
            except Exception:
                if text_channel:
                    await text_channel.send(OutputText.output(gid_i, "Could not find the song."))
                # Guarantee forward progress before retrying the next track.
                if self.loop_song.get(gid_i):
                    self.loop_song[gid_i] = False
                    self.current_song[gid_i] = None
                elif self.loop_queue.get(gid_i) and self.queue.get(gid):
                    self.queue[gid].pop(0)
                    self.save_queue()
                continue

            def after_playing(error):
                fut = asyncio.run_coroutine_threadsafe(
                    self._agent_play_next(guild, text_channel), self.client.loop
                )
                try:
                    fut.result()
                except Exception as e:
                    print(f"[agent] play_next error: {e}")

            source = discord.FFmpegPCMAudio(stream_url, **FFMPEG_OPTIONS)
            vc.play(discord.PCMVolumeTransformer(source, volume=self._vol(gid_i)), after=after_playing)
            if text_channel:
                embed = discord.Embed(title="Now Playing", description=title, color=discord.Color.green())
                if thumbnail:
                    embed.set_thumbnail(url=thumbnail)
                await text_channel.send(embed=embed)
            return  # success — the after-callback schedules the next track

    async def agent_play(self, guild, member, text_channel, query):
        if guild is None:
            return "Music only works inside a server."
        if not (member and getattr(member, "voice", None) and member.voice.channel):
            return "You need to be in a voice channel first, mate."

        vc = guild.voice_client
        if vc and vc.is_connected():
            if vc.channel != member.voice.channel:
                await vc.move_to(member.voice.channel)
        else:
            await member.voice.channel.connect()

        gid = str(guild.id)
        queries = [query]
        try:
            from cogs.Audio.spotify import is_spotify_url, expand_spotify

            if is_spotify_url(query):
                queries = expand_spotify(query)
                if not queries:
                    return "Couldn't read anything off that Spotify link."
        except ImportError:
            pass

        self.queue.setdefault(gid, []).extend(queries)
        self.save_queue()

        started = False
        if not self.is_playing.get(guild.id):
            await self._agent_play_next(guild, text_channel)
            started = True

        if len(queries) > 1:
            return f"Queued {len(queries)} tracks." + (" Starting now." if started else "")
        return f"Playing {queries[0]}." if started else f"Queued: {queries[0]}."

    async def agent_control(self, guild, action):
        if guild is None:
            return "That only works inside a server."
        vc = guild.voice_client
        if action == "skip":
            if vc and vc.is_playing():
                vc.stop()
                return "Skipped."
            return "Nothing's playing."
        if action == "pause":
            if vc and vc.is_playing():
                vc.pause()
                return "Paused."
            return "Nothing to pause."
        if action == "resume":
            if vc and vc.is_paused():
                vc.resume()
                return "Resumed."
            return "Nothing to resume."
        if action == "stop":
            gid_i = guild.id
            if vc and (vc.is_playing() or vc.is_paused()):
                vc.stop()
            self.queue[str(gid_i)] = []
            self.save_queue()
            self.is_playing[gid_i] = False
            self.current_song[gid_i] = None
            if vc:
                await vc.disconnect()
            return "Stopped and cleared the queue."
        return f"Unknown action '{action}'."

    def agent_queue_text(self, guild):
        if guild is None:
            return "That only works inside a server."
        q = self.queue.get(str(guild.id), [])
        if not q:
            return "Queue's empty."
        lines = [f"{i + 1}. {s}" for i, s in enumerate(q[:10])]
        extra = f"\n(+{len(q) - 10} more)" if len(q) > 10 else ""
        return "Queue:\n" + "\n".join(lines) + extra

async def handle_command(command: str, client: commands.Bot) -> Optional[str]:
    cog = client.get_cog("Music")
    if not cog:
        return "Music cog not loaded."

    cmd, *args = command.strip().split(" ", 1)
    arg = args[0] if args else ""

    match cmd.lower():
        case "play":
            cog.local_queue.append(arg)
            if len(cog.local_queue) == 1:
                return await cog.play_song_local(arg)
            return f"Queued: {arg}"
        case "skip":
            return await cog.skip_local()
        case "stop":
            return await cog.stop_local()
        case "queue":
            return await cog.queue_local()
        case "clear":
            return await cog.clear_local_queue()
        case "pause":
            return await cog.pause_local()
        case "resume":
            return await cog.resume_local()
        case _:
            return None

async def setup(client):
    await client.add_cog(Music(client))
