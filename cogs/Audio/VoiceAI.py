import discord
from discord.ext import commands
import os
import asyncio
import edge_tts
import nacl  # Ensure pynacl is installed
import speech_recognition as sr
import tempfile
import time
import wave
import OutputText

try:
    from discord.ext import voice_recv
except Exception as e:
    print(f"[VoiceAI] Failed to import voice_recv: {type(e).__name__}: {e}")
    voice_recv = None

class VoiceAI(commands.Cog):
    """Cog for joining voice channels and speaking with TTS."""

    def __init__(self, client):
        self.client = client
        self.listen_tasks = {}
        self.speaking_guilds = set()
        self.processing_locks = {}
        self.voice_buffers = {}
        self.voice_targets = {}

    @commands.Cog.listener()
    async def on_ready(self):
        print("VoiceAI Cog is online!")

    def _supports_voice_receive(self) -> bool:
        return voice_recv is not None

    def _get_lock(self, guild_id: int) -> asyncio.Lock:
        if guild_id not in self.processing_locks:
            self.processing_locks[guild_id] = asyncio.Lock()
        return self.processing_locks[guild_id]

    async def _speak_in_voice(self, voice_client: discord.VoiceClient, text: str, guild_id: int):
        clean_text = (text or "").strip()
        if not clean_text:
            return

        output_file = f"audio/voice_{guild_id}_{int(time.time() * 1000)}.mp3"
        self.speaking_guilds.add(guild_id)
        try:
            tts = edge_tts.Communicate(clean_text, "en-GB-RyanNeural")
            await tts.save(output_file)

            if not os.path.exists(output_file):
                return

            done_event = asyncio.Event()

            def after_playback(error):
                if error:
                    print(f"Playback error: {error}")
                if os.path.exists(output_file):
                    os.remove(output_file)
                self.client.loop.call_soon_threadsafe(done_event.set)

            while voice_client.is_playing():
                await asyncio.sleep(0.1)

            source = discord.FFmpegPCMAudio(output_file)
            voice_client.play(source, after=after_playback)
            await done_event.wait()
        finally:
            self.speaking_guilds.discard(guild_id)

    async def _transcribe_pcm(self, pcm_bytes: bytes) -> str:
        print(f"[VoiceAI] Transcribing {len(pcm_bytes)} PCM bytes...")
        if not pcm_bytes or len(pcm_bytes) < 8000:
            print(f"[VoiceAI] PCM too short ({len(pcm_bytes)} bytes), skipping transcription.")
            return ""

        recognizer = sr.Recognizer()
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_path = tmp.name

        try:
            with wave.open(temp_path, "wb") as wav_file:
                wav_file.setnchannels(2)
                wav_file.setsampwidth(2)
                wav_file.setframerate(48000)
                wav_file.writeframes(pcm_bytes)
            print(f"[VoiceAI] WAV written to {temp_path}")

            with sr.AudioFile(temp_path) as source:
                audio = recognizer.record(source)
            result = recognizer.recognize_google(audio).strip()
            print(f"[VoiceAI] Transcription result: '{result}'")
            return result
        except sr.UnknownValueError:
            print(f"[VoiceAI] Transcription failed: Could not understand audio")
            return ""
        except Exception as e:
            print(f"[VoiceAI] Transcription error: {e}")
            return ""
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    async def _process_text(self, guild_id: int, target_user_id: int, spoken_text: str):
        print(f"[VoiceAI] Processing text: '{spoken_text}'")
        lock = self._get_lock(guild_id)
        if lock.locked():
            print(f"[VoiceAI] Lock already held, skipping processing.")
            return

        async with lock:
            if not spoken_text:
                print(f"[VoiceAI] Empty text after transcription, skipping.")
                return

            ai_cog = self.client.get_cog("AI")
            if ai_cog is None:
                print("[VoiceAI] AI cog not loaded; cannot generate voice response.")
                return

            print(f"[VoiceAI] Calling AI.generate() with text: '{spoken_text}'")
            try:
                ai_response = await ai_cog.generate(target_user_id, spoken_text)
                print(f"[VoiceAI] AI response: '{ai_response}'")
            except Exception as e:
                print(f"[VoiceAI] AI generation error: {e}")
                return

            guild = self.client.get_guild(guild_id)
            if guild is None or guild.voice_client is None:
                print(f"[VoiceAI] Guild or voice_client is None, cannot speak response.")
                return

            print(f"[VoiceAI] Speaking AI response...")
            await self._speak_in_voice(guild.voice_client, ai_response, guild_id)

    async def _listen_loop(self, guild_id: int, target_user_id: int):
        print(f"[VoiceAI] Listen loop started for guild {guild_id}, user {target_user_id}")
        await asyncio.sleep(0.4)
        loop_iteration = 0
        while True:
            loop_iteration += 1
            print(f"[VoiceAI] Listen loop iteration {loop_iteration}...")
            guild = self.client.get_guild(guild_id)
            if guild is None or guild.voice_client is None:
                print(f"[VoiceAI] Guild or voice_client is None, stopping listen loop.")
                return

            voice_client = guild.voice_client
            if guild_id in self.speaking_guilds:
                print(f"[VoiceAI] Currently speaking, waiting...")
                await asyncio.sleep(0.4)
                continue

            if voice_recv is None or not isinstance(voice_client, voice_recv.VoiceRecvClient):
                print("[VoiceAI] Voice receive is unavailable in this Discord library build.")
                return

            try:
                pcm_bytes = bytes(self.voice_buffers.get(guild_id, b""))
                buffer_len = len(self.voice_buffers.get(guild_id, b""))
                self.voice_buffers[guild_id] = bytearray()
                print(f"[VoiceAI] Buffer collected: {buffer_len} bytes")
            except Exception as e:
                print(f"[VoiceAI] Voice buffer read error: {e}")
                await asyncio.sleep(1.0)
                continue

            if pcm_bytes:
                print(f"[VoiceAI] Transcribing {len(pcm_bytes)} bytes from buffer...")
                spoken_text = await self._transcribe_pcm(pcm_bytes)
                if spoken_text:
                    await self._process_text(guild_id, target_user_id, spoken_text)
                else:
                    print(f"[VoiceAI] Transcription returned empty, skipping.")
            else:
                print(f"[VoiceAI] No audio in buffer, waiting for next cycle...")

            await asyncio.sleep(6.0)

    async def _ensure_receive_client(self, ctx):
        if voice_recv is None:
            print(f"[VoiceAI] voice_recv module is None, cannot connect")
            return False

        channel = ctx.author.voice.channel
        vc = ctx.voice_client
        print(f"[VoiceAI] _ensure_receive_client: current vc type = {type(vc).__name__ if vc else 'None'}")

        if vc and isinstance(vc, voice_recv.VoiceRecvClient):
            print(f"[VoiceAI] Already connected with VoiceRecvClient, moving to channel")
            await vc.move_to(channel)
            return True

        if vc and not isinstance(vc, voice_recv.VoiceRecvClient):
            print(f"[VoiceAI] Wrong VC type ({type(vc).__name__}), disconnecting and reconnecting as VoiceRecvClient")
            await vc.disconnect()

        print(f"[VoiceAI] Connecting to channel as VoiceRecvClient...")
        connected_vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
        print(f"[VoiceAI] Connected: type = {type(connected_vc).__name__}")
        return True

    def _start_voice_recv(self, ctx, target_user_id: int):
        guild_id = ctx.guild.id
        vc = ctx.voice_client
        print(f"[VoiceAI] _start_voice_recv: vc type = {type(vc).__name__}, vc module = {type(vc).__module__}")
        print(f"[VoiceAI] voice_recv module loaded: {voice_recv is not None}")
        print(f"[VoiceAI] isinstance check: {isinstance(vc, voice_recv.VoiceRecvClient) if voice_recv else 'N/A'}")
        
        if voice_recv is None or vc is None or not isinstance(vc, voice_recv.VoiceRecvClient):
            print(f"[VoiceAI] Not a VoiceRecvClient, returning False")
            return False

        self.voice_targets[guild_id] = target_user_id
        self.voice_buffers[guild_id] = bytearray()

        def on_audio(user, data):
            try:
                user_id = getattr(user, "id", None) if user else None
                target_id = self.voice_targets.get(guild_id)
                print(f"[VoiceAI] on_audio callback: user={user_id}, target={target_id}, data_type={type(data).__name__}")
                
                if guild_id in self.speaking_guilds:
                    print(f"[VoiceAI] Currently speaking, ignoring audio from user {user_id}")
                    return
                if user is None:
                    print(f"[VoiceAI] User is None, skipping")
                    return
                if user_id != target_id:
                    print(f"[VoiceAI] Audio from {user_id}, but target is {target_id}, skipping")
                    return
                    
                pcm = getattr(data, "pcm", None)
                if not pcm:
                    print(f"[VoiceAI] No PCM data in audio frame")
                    return
                    
                print(f"[VoiceAI] Buffering {len(pcm)} bytes of audio from user {user_id}")
                self.voice_buffers[guild_id].extend(pcm)
            except Exception as e:
                print(f"[VoiceAI] Voice receive callback error: {e}")

        try:
            if hasattr(vc, "is_listening") and vc.is_listening():
                print(f"[VoiceAI] Stopping existing listener...")
                vc.stop_listening()
            print(f"[VoiceAI] Creating BasicSink and calling vc.listen()...")
            sink = voice_recv.BasicSink(on_audio)
            print(f"[VoiceAI] Sink created: {type(sink).__name__}")
            vc.listen(sink)
            print(f"[VoiceAI] vc.listen() returned, is_listening() = {vc.is_listening() if hasattr(vc, 'is_listening') else 'N/A'}")
            print(f"[VoiceAI] Listening started successfully")
            return True
        except Exception as e:
            print(f"[VoiceAI] Voice receive start error: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def _start_listening(self, ctx, target_user_id: int):
        guild_id = ctx.guild.id
        old_task = self.listen_tasks.get(guild_id)
        if old_task and not old_task.done():
            old_task.cancel()

        self.voice_targets[guild_id] = target_user_id
        if not self._start_voice_recv(ctx, target_user_id):
            return False

        self.listen_tasks[guild_id] = asyncio.create_task(self._listen_loop(guild_id, target_user_id))
        return True

    def _stop_listening(self, guild_id: int):
        task = self.listen_tasks.get(guild_id)
        if task and not task.done():
            task.cancel()
        if guild_id in self.listen_tasks:
            del self.listen_tasks[guild_id]
        if guild_id in self.voice_targets:
            del self.voice_targets[guild_id]
        if guild_id in self.voice_buffers:
            del self.voice_buffers[guild_id]

        guild = self.client.get_guild(guild_id)
        if guild and guild.voice_client and hasattr(guild.voice_client, "stop_listening"):
            try:
                guild.voice_client.stop_listening()
            except Exception:
                pass

    @commands.command()
    async def join(self, ctx):
        """Joins the user's voice channel."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(OutputText.output(ctx.guild.id,"You're not in a voice channel."))
            return

        channel = ctx.author.voice.channel
        
        if ctx.voice_client:
            try:
                ok = await self._ensure_receive_client(ctx)
                if ok:
                    await ctx.send(OutputText.output(ctx.guild.id,"Moved to your channel."))
            except Exception as e:
                await ctx.send(OutputText.output(ctx.guild.id,f"Error connecting: {e}"))
                return
        else:
            try:
                await self._ensure_receive_client(ctx)
                await ctx.send(OutputText.output(ctx.guild.id,f"Connected to {channel}!"))
            except Exception as e:
                await ctx.send(OutputText.output(ctx.guild.id,f"Error connecting: {e}"))
                return

        if not self._supports_voice_receive() or voice_recv is None:
            await ctx.send(OutputText.output(ctx.guild.id, "Voice listening requires discord-ext-voice-recv (discord.py)."))
            return

        started = await self._start_listening(ctx, ctx.author.id)
        if not started:
            await ctx.send(OutputText.output(ctx.guild.id, "Couldn't start voice listening. Check voice receive setup."))
            return
        await ctx.send(OutputText.output(ctx.guild.id, f"Now listening to {ctx.author.display_name} in voice."))

    @commands.command(name="leave")
    async def leave(self, ctx):
        """Leaves the voice channel."""
        guild_id = ctx.guild.id
        self._stop_listening(guild_id)

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

    @commands.command(name="listen_on")
    async def listen_on(self, ctx):
        """Enable AI voice listening in the current VC without rejoining."""
        if ctx.voice_client is None:
            await ctx.send(OutputText.output(ctx.guild.id, "Join a voice channel first!"))
            return

        if not self._supports_voice_receive() or voice_recv is None:
            await ctx.send(OutputText.output(ctx.guild.id, "Voice listening requires discord-ext-voice-recv (discord.py)."))
            return

        try:
            await self._ensure_receive_client(ctx)
        except Exception as e:
            await ctx.send(OutputText.output(ctx.guild.id, f"Couldn't enable listening: {e}"))
            return

        started = await self._start_listening(ctx, ctx.author.id)
        if not started:
            await ctx.send(OutputText.output(ctx.guild.id, "Couldn't start voice listening. Check voice receive setup."))
            return
        await ctx.send(OutputText.output(ctx.guild.id, f"Voice listening enabled for {ctx.author.display_name}."))

    @commands.command(name="listen_off")
    async def listen_off(self, ctx):
        """Disable AI voice listening in the current guild."""
        guild_id = ctx.guild.id
        had_task = guild_id in self.listen_tasks
        self._stop_listening(guild_id)
        if had_task:
            await ctx.send(OutputText.output(ctx.guild.id, "Voice listening disabled."))
        else:
            await ctx.send(OutputText.output(ctx.guild.id, "Voice listening is already off."))

async def setup(client):
    await client.add_cog(VoiceAI(client))
