"""Resolve Spotify links to track names for the yt-dlp pipeline.

Spotify's API only gives metadata — you can't legally stream its audio — so we
turn a track/album/playlist link into ``"artist - title"`` strings and let the
existing yt-dlp/YouTube path actually play them. Uses the Client Credentials
flow (no user login). spotipy is imported lazily.

Env: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
"""
from __future__ import annotations

import os
import re

_SPOTIFY_RE = re.compile(
    r"(open\.spotify\.com/(?:intl-[a-z]+/)?(track|album|playlist)/|spotify:(track|album|playlist):)",
    re.IGNORECASE,
)

_client = None


def is_spotify_url(text) -> bool:
    return bool(text and _SPOTIFY_RE.search(str(text)))


def _get_client():
    global _client
    if _client is None:
        from spotipy import Spotify
        from spotipy.oauth2 import SpotifyClientCredentials

        cid = os.getenv("SPOTIFY_CLIENT_ID")
        secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        if not (cid and secret):
            raise RuntimeError("SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET not set")
        _client = Spotify(
            auth_manager=SpotifyClientCredentials(client_id=cid, client_secret=secret)
        )
    return _client


def _fmt(track) -> str | None:
    if not track or track.get("is_local"):
        return None
    name = track.get("name")
    if not name:
        return None
    artists = ", ".join(a["name"] for a in track.get("artists", []) if a.get("name"))
    return f"{artists} - {name}" if artists else name


def expand_spotify(url: str) -> list[str]:
    """Return ``["artist - title", ...]`` for a Spotify track/album/playlist URL."""
    sp = _get_client()
    out: list[str] = []

    if "track" in url:
        formatted = _fmt(sp.track(url))
        if formatted:
            out.append(formatted)

    elif "album" in url:
        res = sp.album_tracks(url)
        while res:
            for track in res.get("items", []):
                formatted = _fmt(track)
                if formatted:
                    out.append(formatted)
            res = sp.next(res) if res.get("next") else None

    elif "playlist" in url:
        res = sp.playlist_items(url)
        while res:
            for item in res.get("items", []):
                track = item.get("track") if item else None
                formatted = _fmt(track)
                if formatted:
                    out.append(formatted)
            res = sp.next(res) if res.get("next") else None

    return out
