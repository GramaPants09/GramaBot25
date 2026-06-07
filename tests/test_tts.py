"""Tests for the TTS adapter's provider selection + fallback."""
import pytest

from cogs.Audio import tts


@pytest.mark.asyncio
async def test_empty_text_returns_none(tmp_path):
    assert await tts.synthesize("   ", out_dir=str(tmp_path)) is None


@pytest.mark.asyncio
async def test_no_key_uses_edge(tmp_path, monkeypatch):
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.delenv("ELEVENLABS_VOICE_ID", raising=False)
    called = {}

    async def fake_edge(text, out_dir):
        called["edge"] = text
        return "edge.mp3"

    monkeypatch.setattr(tts, "_edge", fake_edge)
    out = await tts.synthesize("oi mate", out_dir=str(tmp_path))
    assert out == "edge.mp3"
    assert called["edge"] == "oi mate"


@pytest.mark.asyncio
async def test_elevenlabs_error_falls_back_to_edge(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")

    async def boom(*a, **k):
        raise RuntimeError("eleven down")

    async def fake_edge(text, out_dir):
        return "edge.mp3"

    monkeypatch.setattr(tts, "_elevenlabs", boom)
    monkeypatch.setattr(tts, "_edge", fake_edge)
    out = await tts.synthesize("hello", out_dir=str(tmp_path))
    assert out == "edge.mp3"


@pytest.mark.asyncio
async def test_elevenlabs_used_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("ELEVENLABS_API_KEY", "k")
    monkeypatch.setenv("ELEVENLABS_VOICE_ID", "v")
    called = {}

    async def fake_eleven(text, api_key, voice_id, out_dir):
        called["eleven"] = (text, api_key, voice_id)
        return "butcher.wav"

    monkeypatch.setattr(tts, "_elevenlabs", fake_eleven)
    out = await tts.synthesize("right then", out_dir=str(tmp_path))
    assert out == "butcher.wav"
    assert called["eleven"][0] == "right then"
