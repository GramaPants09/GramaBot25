"""VoiceAI — GramaBot joins voice calls and chats with whoever's in them.

Pipeline: discord-ext-voice-recv captures per-user audio -> STT adapter
(faster-whisper) -> AgentBrain (full tool access) -> ElevenLabs Butcher TTS ->
played back in the channel. A wake-word ("gramabot"/"butcher") opens a ~120s
conversation window so the bot doesn't talk over the whole call; ``$listen_on``
makes it always-on.

Primary STT path is the library's SpeechRecognitionSink (per-user phrase VAD);
if that's unavailable on the installed alpha wheel it falls back to a BasicSink
buffer + periodic flush. The bot mutes its own receiver while (and just after)
speaking, and de-dups its own echoed words, so it never loops on itself.
"""
import asyncio
import os
import tempfile
import threading
import wave

import discord
from discord.ext import commands

import OutputText
from cogs.Audio import stt as stt_adapter
from cogs.Audio import tts as tts_adapter

try:
    from discord.ext import voice_recv
except Exception as e:  # pragma: no cover
    print(f"[VoiceAI] voice_recv unavailable: {type(e).__name__}: {e}")
    voice_recv = None

WAKE_WORDS = ("gramabot", "grama bot", "butcher", "jarvis", "hey grama", "oi grama")
CONVO_WINDOW = 120.0
# How long after we finish speaking to stay "muted", covering the lag between a
# phrase being captured during playback and its transcription being delivered
# (SpeechRecognition phrase_time_limit ~10s + STT latency).
MUTE_TAIL_SECONDS = 12.0


class VoiceAI(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.speaking_counts = {}   # guild_id -> int (ref-count of in-flight _speak)
        self.muted_until = {}       # guild_id -> loop-clock deadline
        self.last_spoken = {}       # guild_id -> normalized last TTS text (echo guard)
        self.windows = {}           # guild_id -> last activity time (loop clock)
        self.bound_text = {}        # guild_id -> text channel for replies/approvals
        self.locks = {}             # guild_id -> asyncio.Lock
        self.always_on = set()      # guild_ids answering without a wake word
        self.buffers = {}           # guild_id -> {user_id: bytearray}  (fallback)
        self.buffers_lock = threading.Lock()  # producer thread vs flush loop
        self._fallback_active = {}  # guild_id -> bool
        self._flush_tasks = {}      # guild_id -> asyncio.Task

    @commands.Cog.listener()
    async def on_ready(self):
        print("VoiceAI Cog is online!")

    # ----------------------------------------------------------------- plumbing
    def _brain(self):
        ai = self.client.get_cog("AI")
        return getattr(ai, "brain", None)

    def _lock(self, guild_id: int) -> asyncio.Lock:
        return self.locks.setdefault(guild_id, asyncio.Lock())

    def _enter_speaking(self, gid):
        self.speaking_counts[gid] = self.speaking_counts.get(gid, 0) + 1

    def _exit_speaking(self, gid):
        n = self.speaking_counts.get(gid, 0) - 1
        if n <= 0:
            self.speaking_counts.pop(gid, None)
        else:
            self.speaking_counts[gid] = n

    def _is_speaking(self, gid) -> bool:
        return self.speaking_counts.get(gid, 0) > 0

    async def _ensure_recv_client(self, channel):
        """Connect to (or move into) ``channel`` as a VoiceRecvClient."""
        if voice_recv is None:
            return None
        guild = channel.guild
        vc = guild.voice_client
        if vc and isinstance(vc, voice_recv.VoiceRecvClient):
            if vc.channel != channel:
                await vc.move_to(channel)
            return vc
        if vc:  # wrong client type (e.g. plain music client) — reconnect
            await vc.disconnect(force=True)
        return await channel.connect(cls=voice_recv.VoiceRecvClient)

    # --------------------------------------------------------------- listening
    def _make_sink(self):
        try:
            from discord.ext.voice_recv.extras import speechrecognition as srx

            return srx.SpeechRecognitionSink(
                process_cb=stt_adapter.make_process_cb(),
                text_cb=self._on_text,
            ), "sr"
        except Exception as e:
            print(f"[VoiceAI] SpeechRecognitionSink unavailable ({e}); using BasicSink fallback.")
            return voice_recv.BasicSink(self._basic_on_audio), "basic"

    async def _start_listening(self, guild, text_channel) -> bool:
        vc = guild.voice_client
        if vc is None or voice_recv is None or not isinstance(vc, voice_recv.VoiceRecvClient):
            return False
        gid = guild.id
        self.bound_text[gid] = text_channel

        # Tear down any previous listener + flush task before starting fresh.
        self._cancel_flush(gid)
        try:
            if hasattr(vc, "is_listening") and vc.is_listening():
                vc.stop_listening()
        except Exception:
            pass

        sink, kind = self._make_sink()
        try:
            vc.listen(sink)
        except Exception as e:
            print(f"[VoiceAI] vc.listen failed: {e}")
            return False

        if kind == "basic":
            self._fallback_active[gid] = True
            with self.buffers_lock:
                self.buffers[gid] = {}
            self._flush_tasks[gid] = asyncio.create_task(self._flush_loop(guild))
        return True

    def _cancel_flush(self, gid):
        self._fallback_active[gid] = False
        task = self._flush_tasks.pop(gid, None)
        if task and not task.done():
            task.cancel()

    def _stop_listening(self, guild):
        gid = guild.id
        self._cancel_flush(gid)
        self.windows.pop(gid, None)
        with self.buffers_lock:
            self.buffers.pop(gid, None)
        vc = guild.voice_client
        if vc and hasattr(vc, "stop_listening"):
            try:
                vc.stop_listening()
            except Exception:
                pass

    # -- SpeechRecognitionSink path: text_cb gives us finalised per-user text --
    def _on_text(self, user, text):
        # Runs on the receive thread — hop back onto the loop.
        if not text or user is None or getattr(user, "bot", False):
            return
        guild = getattr(user, "guild", None)
        if guild is None or self._is_speaking(guild.id):
            return
        asyncio.run_coroutine_threadsafe(self._handle(guild, user, text), self.client.loop)

    # -- BasicSink fallback path: buffer PCM per user, flush periodically --
    def _basic_on_audio(self, user, data):
        try:
            if user is None or getattr(user, "bot", False):
                return
            guild = getattr(user, "guild", None)
            if guild is None or self._is_speaking(guild.id):
                return
            pcm = getattr(data, "pcm", None)
            if not pcm:
                return
            with self.buffers_lock:
                self.buffers.setdefault(guild.id, {}).setdefault(user.id, bytearray()).extend(pcm)
        except Exception as e:
            print(f"[VoiceAI] basic audio error: {e}")

    async def _flush_loop(self, guild):
        gid = guild.id
        while self._fallback_active.get(gid):
            await asyncio.sleep(4.0)
            if self._is_speaking(gid):
                continue
            # Snapshot + clear each user's buffer atomically vs the producer thread,
            # then transcribe outside the lock.
            snapshot = []
            with self.buffers_lock:
                users = self.buffers.get(gid, {})
                for uid, buf in list(users.items()):
                    if len(buf) < 48000:  # ~0.25s of 48k stereo 16-bit; too short
                        continue
                    snapshot.append((uid, bytes(buf)))
                    users[uid] = bytearray()
            for uid, pcm in snapshot:
                member = guild.get_member(uid)
                if member is None:
                    continue
                text = await asyncio.to_thread(self._pcm_to_text, pcm)
                if text:
                    # Don't block the flush cadence on the full reply chain.
                    asyncio.create_task(self._handle(guild, member, text))

    def _pcm_to_text(self, pcm: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            path = f.name
        try:
            with wave.open(path, "wb") as w:
                w.setnchannels(2)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes(pcm)
            return stt_adapter.transcribe_wav(path)
        finally:
            try:
                os.remove(path)
            except OSError:
                pass

    # ----------------------------------------------------------- conversation
    async def _handle(self, guild, member, text):
        gid = guild.id
        now = asyncio.get_event_loop().time()
        # Captured during/just-after our own playback — drop (covers STT lag).
        if now < self.muted_until.get(gid, 0):
            return
        norm = " ".join(text.lower().split())
        if norm and norm == self.last_spoken.get(gid):
            return  # echo of our own last line — break the loop

        is_wake = any(w in norm for w in WAKE_WORDS)
        active = gid in self.always_on or (now - self.windows.get(gid, 0) < CONVO_WINDOW)
        if not (is_wake or active):
            return

        lock = self._lock(gid)
        if lock.locked():
            return  # already mid-response; drop overlapping speech
        async with lock:
            self.windows[gid] = now
            brain = self._brain()
            if brain is None:
                return
            channel = self.bound_text.get(gid)
            prompt = f'[Voice call. {member.display_name} just said this out loud.] {text}'
            try:
                response = await brain.respond(
                    user=member, channel=channel, guild=guild, text=prompt, voice=True
                )
            except Exception as e:
                print(f"[VoiceAI] brain error: {e}")
                return
            await self._speak(guild, response)

    async def _speak(self, guild, text):
        clean = (text or "").strip()
        if not clean:
            return
        path = await tts_adapter.synthesize(clean)
        if not path or not os.path.exists(path):
            return

        gid = guild.id
        vc = guild.voice_client
        if vc is None or not vc.is_connected():
            self._cleanup_file(path)
            return

        done = asyncio.Event()

        def after(err):
            if err:
                print(f"[VoiceAI] playback error: {err}")
            self.client.loop.call_soon_threadsafe(done.set)

        self._enter_speaking(gid)
        self.last_spoken[gid] = " ".join(clean.lower().split())
        try:
            # Bounded wait if the VC is busy (e.g. music) — don't hang forever.
            waited = 0.0
            while vc.is_playing() and waited < 5.0:
                await asyncio.sleep(0.1)
                waited += 0.1
            if vc.is_playing():
                print("[VoiceAI] VC busy; skipping voice reply.")
                return
            vc.play(discord.FFmpegPCMAudio(path), after=after)
            await done.wait()
            await asyncio.sleep(0.3)  # let the tail clear
        except Exception as e:
            print(f"[VoiceAI] speak error: {e}")
        finally:
            # Keep the guild muted long enough to cover capture->delivery STT lag.
            self.muted_until[gid] = self.client.loop.time() + MUTE_TAIL_SECONDS
            self._exit_speaking(gid)
            self._cleanup_file(path)

    @staticmethod
    def _cleanup_file(path):
        try:
            os.remove(path)
        except OSError:
            pass

    # ------------------------------------------------------- agent-facing API
    async def agent_join(self, guild, member, text_channel=None):
        if not (member and getattr(member, "voice", None) and member.voice.channel):
            return "They need to be in a voice channel first."
        try:
            await self._ensure_recv_client(member.voice.channel)
        except Exception as e:
            return f"Couldn't join voice: {e}"
        await self._start_listening(guild, text_channel or self.bound_text.get(guild.id))
        self.always_on.add(guild.id)
        return f"Joined {member.voice.channel.name} and I'm all ears."

    async def agent_leave(self, guild):
        if guild is None or guild.voice_client is None:
            return "I'm not in a voice channel."
        self.always_on.discard(guild.id)
        self._stop_listening(guild)
        await guild.voice_client.disconnect()
        return "Left the voice channel."

    async def agent_speak(self, guild, text):
        if guild is None or guild.voice_client is None:
            return "I'm not in a voice channel to speak in."
        await self._speak(guild, text)
        return f"Said: {text}"

    # =============================================================== COMMANDS
    @commands.command()
    async def join(self, ctx):
        """Join your voice channel and start listening."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send(OutputText.output(ctx.guild.id, "You're not in a voice channel."))
            return
        if voice_recv is None:
            await ctx.send(OutputText.output(ctx.guild.id,
                          "Voice listening needs discord-ext-voice-recv installed."))
            return
        try:
            await self._ensure_recv_client(ctx.author.voice.channel)
        except Exception as e:
            await ctx.send(OutputText.output(ctx.guild.id, f"Error connecting: {e}"))
            return
        started = await self._start_listening(ctx.guild, ctx.channel)
        if not started:
            await ctx.send(OutputText.output(ctx.guild.id, "Couldn't start voice listening."))
            return
        self.windows[ctx.guild.id] = asyncio.get_event_loop().time()
        await ctx.send(OutputText.output(ctx.guild.id,
                      "In the call. Say 'gramabot' or 'butcher' to get my attention."))

    @commands.command(name="leave")
    async def leave(self, ctx):
        """Leave the voice channel."""
        msg = await self.agent_leave(ctx.guild)
        await ctx.send(OutputText.output(ctx.guild.id, msg))

    @commands.command(name="speak")
    async def speak(self, ctx, *, text):
        """Say something out loud."""
        if ctx.voice_client is None:
            await ctx.send("Join a voice channel first!")
            return
        await self._speak(ctx.guild, text)
        await ctx.send(OutputText.output(ctx.guild.id, f"Saying: {text}"))

    @commands.command(name="listen_on")
    async def listen_on(self, ctx):
        """Answer everything in the call (no wake word needed)."""
        if ctx.voice_client is None:
            await ctx.send(OutputText.output(ctx.guild.id, "Join a voice channel first!"))
            return
        self.always_on.add(ctx.guild.id)
        self.bound_text[ctx.guild.id] = ctx.channel
        await ctx.send(OutputText.output(ctx.guild.id, "Always-on: I'll chime in on everything now."))

    @commands.command(name="listen_off")
    async def listen_off(self, ctx):
        """Go back to wake-word only."""
        self.always_on.discard(ctx.guild.id)
        await ctx.send(OutputText.output(ctx.guild.id, "Back to wake-word only."))


async def setup(client):
    await client.add_cog(VoiceAI(client))
