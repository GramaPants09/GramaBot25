"""Tests for the STT adapter's backend selection + fallback."""
from cogs.Audio import stt


def test_select_backend_default(monkeypatch):
    monkeypatch.delenv("STT_BACKEND", raising=False)
    assert stt._select_backend() == "whisper"


def test_select_backend_honors_env(monkeypatch):
    monkeypatch.setenv("STT_BACKEND", "Deepgram")
    assert stt._select_backend() == "deepgram"


def test_primary_backend_used(monkeypatch):
    monkeypatch.setenv("STT_BACKEND", "google")
    monkeypatch.setattr(stt, "_google_transcribe", lambda p: "google text")
    assert stt.transcribe_wav("x.wav") == "google text"


def test_falls_back_to_google_on_error(monkeypatch):
    monkeypatch.setenv("STT_BACKEND", "whisper")

    def boom(_):
        raise RuntimeError("no wheel")

    monkeypatch.setattr(stt, "_whisper_transcribe", boom)
    monkeypatch.setattr(stt, "_google_transcribe", lambda p: "fallback text")
    # rebuild dispatch table reference used inside transcribe_wav
    monkeypatch.setitem(stt._BACKENDS, "whisper", boom)
    assert stt.transcribe_wav("x.wav") == "fallback text"


def test_total_failure_returns_empty(monkeypatch):
    monkeypatch.setenv("STT_BACKEND", "whisper")

    def boom(_):
        raise RuntimeError("down")

    monkeypatch.setitem(stt._BACKENDS, "whisper", boom)
    monkeypatch.setattr(stt, "_google_transcribe", boom)
    assert stt.transcribe_wav("x.wav") == ""


def test_make_process_cb_is_callable():
    assert callable(stt.make_process_cb())
