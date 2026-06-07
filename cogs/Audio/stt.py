"""Speech-to-text adapter with a pluggable backend.

``transcribe_wav(path)`` returns recognised text (or "" on failure — it never
raises for normal errors). The backend is chosen by ``STT_BACKEND``:

    whisper   faster-whisper, local, free, accurate (default)
    deepgram  Deepgram prerecorded API (needs DEEPGRAM_API_KEY), low latency
    google    SpeechRecognition's Google recogniser (no setup, weakest)

If the chosen backend can't load (e.g. no faster-whisper wheel on Python 3.14),
it falls back to Google so the bot still hears. ``make_process_cb`` returns a
callback compatible with discord-ext-voice-recv's SpeechRecognitionSink.

Env: STT_BACKEND, WHISPER_MODEL (default 'small'), WHISPER_COMPUTE (default 'int8'),
DEEPGRAM_API_KEY.
"""
from __future__ import annotations

import os

_whisper_model = None


def _select_backend() -> str:
    return (os.getenv("STT_BACKEND") or "whisper").strip().lower()


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        size = os.getenv("WHISPER_MODEL", "small")
        compute = os.getenv("WHISPER_COMPUTE", "int8")
        _whisper_model = WhisperModel(size, compute_type=compute)
    return _whisper_model


def _whisper_transcribe(wav_path: str) -> str:
    model = _get_whisper()
    segments, _info = model.transcribe(wav_path, beam_size=1)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _google_transcribe(wav_path: str) -> str:
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio = recognizer.record(source)
    try:
        return recognizer.recognize_google(audio).strip()
    except sr.UnknownValueError:
        return ""


def _deepgram_transcribe(wav_path: str) -> str:
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        raise RuntimeError("DEEPGRAM_API_KEY not set")
    import requests

    with open(wav_path, "rb") as f:
        resp = requests.post(
            "https://api.deepgram.com/v1/listen?model=nova-3&smart_format=true",
            headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
            data=f.read(),
            timeout=30,
        )
    resp.raise_for_status()
    data = resp.json()
    return (
        data.get("results", {})
        .get("channels", [{}])[0]
        .get("alternatives", [{}])[0]
        .get("transcript", "")
        .strip()
    )


_BACKENDS = {
    "whisper": _whisper_transcribe,
    "deepgram": _deepgram_transcribe,
    "google": _google_transcribe,
}


def transcribe_wav(wav_path: str) -> str:
    backend = _select_backend()
    fn = _BACKENDS.get(backend, _whisper_transcribe)
    try:
        return fn(wav_path)
    except Exception as e:
        if fn is not _google_transcribe:
            print(f"[STT] {backend} backend failed ({e}); falling back to Google.")
            try:
                return _google_transcribe(wav_path)
            except Exception as e2:
                print(f"[STT] Google fallback failed ({e2}).")
        return ""


def make_process_cb():
    """Return a recogniser callable for SpeechRecognitionSink(process_cb=...).

    The sink hands us a SpeechRecognition AudioData; we serialise it to a WAV
    and run the configured backend. Tolerant of the exact arg order across
    alpha versions of the library.
    """

    def process(*args):
        import tempfile

        audio = next((a for a in args if hasattr(a, "get_wav_data")), None)
        if audio is None:
            return None
        try:
            data = audio.get_wav_data()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                f.write(data)
                path = f.name
            try:
                return transcribe_wav(path) or None
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
        except Exception as e:
            print(f"[STT] process_cb error: {e}")
            return None

    return process
