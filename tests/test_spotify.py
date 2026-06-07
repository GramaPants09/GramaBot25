"""Tests for Spotify link detection + expansion (stubbed spotipy)."""
from cogs.Audio import spotify


def test_is_spotify_url():
    assert spotify.is_spotify_url("https://open.spotify.com/track/abc123")
    assert spotify.is_spotify_url("https://open.spotify.com/intl-de/album/xyz")
    assert spotify.is_spotify_url("spotify:playlist:deadbeef")
    assert not spotify.is_spotify_url("just a normal search query")
    assert not spotify.is_spotify_url("https://youtube.com/watch?v=abc")
    assert not spotify.is_spotify_url(None)


class FakeSpotify:
    def __init__(self):
        self._page2 = {
            "items": [{"track": {"name": "Two", "artists": [{"name": "B"}]}}],
            "next": None,
        }

    def track(self, url):
        return {"name": "Solo", "artists": [{"name": "A"}, {"name": "B"}]}

    def album_tracks(self, url):
        return {"items": [{"name": "AlbumSong", "artists": [{"name": "A"}]}], "next": None}

    def playlist_items(self, url):
        return {
            "items": [
                {"track": {"name": "One", "artists": [{"name": "A"}]}},
                {"track": None},                                  # removed track
                {"track": {"name": "Local", "artists": [], "is_local": True}},  # local file
            ],
            "next": "page2",
        }

    def next(self, res):
        return self._page2


def test_expand_track(monkeypatch):
    monkeypatch.setattr(spotify, "_get_client", lambda: FakeSpotify())
    assert spotify.expand_spotify("https://open.spotify.com/track/x") == ["A, B - Solo"]


def test_expand_album(monkeypatch):
    monkeypatch.setattr(spotify, "_get_client", lambda: FakeSpotify())
    assert spotify.expand_spotify("https://open.spotify.com/album/x") == ["A - AlbumSong"]


def test_expand_playlist_paginates_and_skips_bad_items(monkeypatch):
    monkeypatch.setattr(spotify, "_get_client", lambda: FakeSpotify())
    result = spotify.expand_spotify("https://open.spotify.com/playlist/x")
    assert result == ["A - One", "B - Two"]  # None + is_local skipped, page2 included
