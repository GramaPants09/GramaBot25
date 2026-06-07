"""Text-to-speech adapter: ElevenLabs (Butcher voice) with edge-TTS fallback.

``synthesize(text)`` returns a path to a playable audio file (a 48kHz mono WAV
from ElevenLabs, or an MP3 from edge-TTS). It never raises for normal failures —
if ElevenLabs is unconfigured or errors, it transparently falls back to edge so
the bot is never struck dumb. Heavy libs are imported lazily.

Env:
    ELEVENLABS_API_KEY   ElevenLabs key (enables the Butcher voice)
    ELEVENLABS_VOICE_ID  the voice to speak in
    ELEVENLABS_MODEL     model id (default eleven_flash_v2_5)
    EDGE_TTS_VOICE       fallback voice (default en-GB-RyanNeural)
"""
from __future__ import annotations

import asyncio
import os
import time
import wave

DEFAULT_MODEL = "eleven_flash_v2_5"
FALLBACK_VOICE = "en-GB-RyanNeural"


async def synthesize(text: str, *, out_dir: str = "audio") -> str | None:
    clean = (text or "").strip()
    if not clean:
        return None
    os.makedirs(out_dir, exist_ok=True)

    api_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if api_key and voice_id:
        try:
            path = await _elevenlabs(clean, api_key, voice_id, out_dir)
            if path:
                return path
        except Exception as e:
            print(f"[TTS] ElevenLabs failed ({e}); falling back to edge-TTS.")
    return await _edge(clean, out_dir)


async def _elevenlabs(text: str, api_key: str, voice_id: str, out_dir: str) -> str | None:
    from elevenlabs.client import ElevenLabs

    model = os.getenv("ELEVENLABS_MODEL", DEFAULT_MODEL)
    client = ElevenLabs(api_key=api_key)

    def _generate() -> bytes:
        stream = client.text_to_speech.convert(
            voice_id=voice_id,
            model_id=model,
            text=text,
            output_format="pcm_48000",  # 48kHz mono 16-bit PCM — no resample needed
        )
        return b"".join(stream)

    pcm = await asyncio.to_thread(_generate)
    if not pcm:
        return None
    path = os.path.join(out_dir, f"voice_{int(time.time() * 1000)}.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(pcm)
    return path


async def _edge(text: str, out_dir: str) -> str | None:
    try:
        import edge_tts
    except Exception as e:
        print(f"[TTS] edge-tts not available: {e}")
        return None
    voice = os.getenv("EDGE_TTS_VOICE", FALLBACK_VOICE)
    path = os.path.join(out_dir, f"voice_{int(time.time() * 1000)}.mp3")
    try:
        await edge_tts.Communicate(text, voice).save(path)
        return path
    except Exception as e:
        print(f"[TTS] edge-tts failed: {e}")
        return None
