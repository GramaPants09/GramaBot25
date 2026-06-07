"""VoiceAI — GramaBot joins voice calls and chats with whoever's in them.

Pipeline: discord-ext-voice-recv captures per-user audio -> STT adapter
(faster-whisper) -> AgentBrain (full tool access) -> ElevenLabs Butcher TTS ->
played back in the channel. A wake-word ("gramabot"/"butcher") opens a ~120s
conversation window so the bot doesn't talk over the whole call; ``$listen_on``
makes it always-on.

Primary STT path is the library's SpeechRecognitionSink (per-user phrase VAD);
if that's unavailable on the installed alpha wheel it falls back to a BasicSink
buffer + periodic flush. The bot mutes its own receiver while speaking so it
never transcribes itself into a loop.
"""
import asyncio
import os
import tempfile
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


class VoiceAI(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.speaking_guilds = set()
        self.windows = {}           # guild_id -> last activity time (loop clock)
        self.bound_text = {}        # guild_id -> text channel for replies/approvals
        self.locks = {}             # guild_id -> asyncio.Lock
        self.always_on = set()      # guild_ids answering without a wake word
        self.buffers = {}           # guild_id -> {user_id: bytearray}  (fallback)
        self._fallback_active = {}  # guild_id -> bool

    @commands.Cog.listener()
    async def on_ready(self):
        print("VoiceAI Cog is online!")

    # ----------------------------------------------------------------- plumbing
    def _brain(self):
        ai = self.client.get_cog("AI")
        return getattr(ai, "brain", None)

    def _lock(self, guild_id: int) -> asyncio.Lock:
        return self.locks.setdefault(guild_id, asyncio.Lock())

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
        self.bound_text[guild.id] = text_channel
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
            self._fallback_active[guild.id] = True
            self.buffers[guild.id] = {}
            asyncio.create_task(self._flush_loop(guild))
        return True

    def _stop_listening(self, guild):
        gid = guild.id
        self._fallback_active[gid] = False
        self.windows.pop(gid, None)
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
        if guild is None or guild.id in self.speaking_guilds:
            return
        asyncio.run_coroutine_threadsafe(self._handle(guild, user, text), self.client.loop)

    # -- BasicSink fallback path: buffer PCM per user, flush periodically --
    def _basic_on_audio(self, user, data):
        try:
            if user is None or getattr(user, "bot", False):
                return
            guild = getattr(user, "guild", None)
            if guild is None or guild.id in self.speaking_guilds:
                return
            pcm = getattr(data, "pcm", None)
            if not pcm:
                return
            self.buffers.setdefault(guild.id, {}).setdefault(user.id, bytearray()).extend(pcm)
        except Exception as e:
            print(f"[VoiceAI] basic audio error: {e}")

    async def _flush_loop(self, guild):
        gid = guild.id
        while self._fallback_active.get(gid) and guild.voice_client is not None:
            await asyncio.sleep(4.0)
            if gid in self.speaking_guilds:
                continue
            users = self.buffers.get(gid, {})
            for uid, buf in list(users.items()):
                if len(buf) < 48000:  # ~0.25s of 48k stereo 16-bit; too short to bother
                    continue
                pcm = bytes(buf)
                users[uid] = bytearray()
                member = guild.get_member(uid)
                if member is None:
                    continue
                text = await asyncio.to_thread(self._pcm_to_text, pcm)
                if text:
                    await self._handle(guild, member, text)

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
        lowered = text.lower()
        is_wake = any(w in lowered for w in WAKE_WORDS)
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
        vc = guild.voice_client
        if not clean or vc is None:
            return
        path = await tts_adapter.synthesize(clean)
        if not path or not os.path.exists(path):
            return

        gid = guild.id
        done = asyncio.Event()

        def after(err):
            if err:
                print(f"[VoiceAI] playback error: {err}")
            try:
                os.remove(path)
            except OSError:
                pass
            self.client.loop.call_soon_threadsafe(done.set)

        self.speaking_guilds.add(gid)
        try:
            while vc.is_playing():
                await asyncio.sleep(0.1)
            vc.play(discord.FFmpegPCMAudio(path), after=after)
            await done.wait()
            await asyncio.sleep(0.3)  # let the tail clear before we listen again
        finally:
            self.speaking_guilds.discard(gid)

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
                      f"In the call. Say 'gramabot' or 'butcher' to get my attention."))

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
