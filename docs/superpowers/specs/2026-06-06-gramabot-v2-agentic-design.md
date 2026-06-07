# GramaBot25 v2 — Agentic Brain, Voice Chat, Spotify & Butcher Voice

**Date:** 2026-06-06
**Owner:** GramaPants (Aidan)
**Status:** Approved design → implementation

## Goal

Upgrade GramaBot25 from a flat single-shot chatbot into an **agentic bot** that:

1. Has a real **brain** (Claude) wrapped in a tool-use loop, so it can *take actions* — abilities like OpenClaw.
2. **Joins Discord voice calls and chats with humans** (the owner + friends) by voice.
3. Plays music linked to **Spotify**.
4. Speaks in a gruff-cockney **"Billy-Butcher-inspired" voice** (ElevenLabs).

Plus general fixer-upper cleanup of the existing codebase.

## Non-goals (explicitly dropped / deferred)

- **Bot-to-bot voice conversation.** The owner clarified the bot should "just chat to me or my friends." Two bots hearing each other acoustically is unproven, and the text-relay alternative needs a second token. Dropped for now — a clean relay seam is left so a second bot can be added later without rework.
- Cloning Karl Urban's actual voice. Legally/contractually blocked (ElevenLabs clones only your *own* voice; right-of-publicity risk). The persona lives in the *writing*; the voice is a generic gruff-cockney voice the owner builds in ElevenLabs.
- Migrating off discord.py to Pycord. discord.py 2.6 + discord-ext-voice-recv is correct here.

## Confirmed decisions

| Decision | Choice |
|---|---|
| Deploy host | PC / Mac (decent CPU) |
| STT | faster-whisper (local), pluggable adapter, cloud fallback available |
| Brain | Claude only — Sonnet 4.6 orchestrator, Haiku 4.5 fast executor |
| TTS | ElevenLabs Flash v2.5 (`pcm_48000`), edge-TTS auto-fallback |
| Spotify | Metadata-only resolve (spotipy, Client Credentials) → yt-dlp plays from YouTube |
| Voice trigger | Wake-word ("gramabot"/"butcher"/@mention) opens a ~120s conversation window |
| Default persona | Butcher (gruff cockney); existing per-user roast prompts preserved as overlays |
| Destructive tools | Human Approve button + independent Discord-permission recheck |

## Architecture

### Component 1 — `AgentBrain` (the spine)

New: `cogs/AI/brain.py`, `cogs/AI/tools/` (package), `cogs/AI/memory.py`.

- **Provider:** Anthropic SDK. `AgentBrain.respond(user_id, channel_id, text, *, voice=False)` runs a **bounded tool-use loop** (max ~8 iterations) against Sonnet 4.6; trivial/fast paths may use Haiku 4.5. Model ids and the iteration cap are config constants.
- **Tool registry:** a `@tool(name, description, schema)` decorator collects `{name → (schema, async handler)}`. Handlers are thin shims that call existing cogs via `client.get_cog(...)`. The brain is given the JSON schemas; on a `tool_use` block it dispatches to the handler, appends the assistant tool-use message **then** the `tool_result`, and loops.
- **Tools (v1):**
  - Music: `play_music(query_or_spotify_url)`, `skip`, `pause`, `resume`, `stop`, `queue_status`
  - Voice: `join_voice`, `leave_voice`, `speak(text)`
  - Aura: `get_aura(user)`, `add_aura(user, amount)`, `set_aura(user, amount)`
  - Moderation (**gated**): `timeout_user`, `kick_user`, `ban_user`
  - `openclaw_rpc(method, params)` (**gated**) — WebSocket RPC to the OpenClaw gateway
  - `web_search(query)` — pluggable, optional in v1 (no-op/stub if no provider key)
- **Safety:** destructive + RPC + hardware tools require a Discord **Approve/Reject button** before execution, and each handler re-checks the *invoking Discord user's* permissions and role hierarchy — the model requesting an action is never authorization. Loop cap + per-tool cooldowns + 429 backoff.
- **Memory:** `cogs/AI/memory.py` — SQLite at `data/brain.db`, table keyed by `(user_id, channel_id)`, storing role-tagged turns + a rolling summary. One-time importer migrates existing `cogs/jsonfiles/memory.json`. Replaces the whole-file-rewrite pattern.
- **Personas:** base system prompt = Butcher (gruff cockney, London slang, cynical, never narrates actions, no asterisks). The existing 6 per-user custom prompts are retained as optional flavor overlays appended to the base.

### Component 2 — Voice conversation (rework `cogs/Audio/VoiceAI.py`)

- **Multi-user listening:** stop filtering to a single target user. Tag each finalized utterance with the speaker's display name; pass `"<name> said: <text>"` to the brain.
- **STT adapter** (`cogs/Audio/stt.py`): default faster-whisper (`WhisperModel("small", compute_type="int8")`, 16k mono float32). Pluggable via `STT_BACKEND` env (`whisper` | `deepgram` | `google`). Graceful: if faster-whisper import fails (e.g. no 3.14 wheel), fall back to the existing Google recognizer with a logged warning.
- **Segmentation:** use the library's `voice_recv.extras.speechrecognition.SpeechRecognitionSink` (per-user buffering + phrase VAD + downmix) with `process_cb` injecting the STT adapter — replacing the blind 6-second poll loop. Fallback to the current BasicSink path if the extras sink is unavailable on the installed wheel.
- **Flow:** finalized transcript → `AgentBrain.respond(..., voice=True)` (full tool access) → **TTS adapter** → play in VC. Keep the `speaking_guilds` self-mute gate (prevents transcribing its own TTS).
- **Trigger:** mirror `RespondInChat` — wake-word / @mention opens a ~120s window during which all speech in the channel is answered; window resets on each exchange.

### Component 3 — TTS adapter (new `cogs/Audio/tts.py`)

- `synthesize(text) -> wav_path`: ElevenLabs Flash v2.5 (`eleven_flash_v2_5`), output `pcm_48000` (no resample), keyed on `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID`.
- **Fallback:** if the key is missing or the call errors, use edge-TTS `en-GB-RyanNeural`. The bot never goes silent.
- Single entry point used by `VoiceAI` (and available to the local fish pipeline for the owner). Config: `ELEVENLABS_MODEL` defaults to `eleven_flash_v2_5`.

### Component 4 — Spotify (new `cogs/Audio/spotify.py`, hook in `Music.play`)

- `expand_spotify(url) -> list[str]`: spotipy `SpotifyClientCredentials`; supports track / album / playlist with `sp.next()` pagination; guards `None` (removed) and `is_local` items; returns `"artist - title"` strings.
- In `Music.play`: if the query matches a Spotify URL, expand and enqueue all resolved tracks; otherwise unchanged. Config: `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`. No-op with a friendly message if creds absent.

### Component 5 — OpenClaw ability

- `cogs/AI/tools/openclaw.py`: thin async WebSocket JSON-RPC client to `OPENCLAW_WS_URL` (default `ws://127.0.0.1:18789`) using `OPENCLAW_TOKEN`. Exposed as the gated `openclaw_rpc` tool. Verify the gateway is reachable at call time; clear error if not.

### Component 6 — Fixer-upper cleanups

- Delete dead files: `AI_updated_Ollama.py`, `cogs/AI/AI_backup.py`.
- Fix `RespondInChat` "fuck off" `KeyError` (guard the `del` with a membership check).
- Fix `?` mojibake in `GramaBot25.py` reload/reload_all messages (use real ✅/❌).
- Make hardcoded `/home/gramapants/...` paths repo-root-relative (`Speech_Aligner.py`, `Phoneme_Split.py`, `AI.py` `AUDIO_DIR`) so it runs on the Mac.
- `requirements.txt`: add `anthropic`, `spotipy`, `faster-whisper`, `elevenlabs`, `audioop-lts` (Python ≥3.13). Keep `openai` (OpenRouter fallback retained behind the seam).
- (Stretch) Make `Music` playback state per-guild instead of global.

## Configuration (`.env`)

```
DISCORD_API=...              # existing
ANTHROPIC_API_KEY=...        # new — the brain
ELEVENLABS_API_KEY=...       # new — Butcher voice
ELEVENLABS_VOICE_ID=...      # new — the voice you build
SPOTIFY_CLIENT_ID=...        # new — music
SPOTIFY_CLIENT_SECRET=...    # new — music
TENOR_KEY=...                # existing — gifs
OPENCLAW_WS_URL=ws://127.0.0.1:18789   # optional
OPENCLAW_TOKEN=...                      # optional
STT_BACKEND=whisper          # optional: whisper|deepgram|google
```

Every key is optional except `DISCORD_API`; each subsystem degrades gracefully (logged warning + fallback or friendly user message) when its key is absent, so the bot always boots.

## Build order

1. **Brain foundation** — tool registry, Claude provider, SQLite memory; port `AI` cog to use `AgentBrain` (text chat with tools working).
2. **TTS adapter** — ElevenLabs + edge fallback; Butcher persona.
3. **Voice rework** — multi-user, faster-whisper STT adapter, SpeechRecognitionSink, brain routing, Butcher TTS.
4. **Spotify** — resolver + `Music.play` hook.
5. **OpenClaw tool + destructive-tool approval gating.**
6. **Cleanups** — woven throughout, verified at the end.

## Testing strategy

- **Brain/tools:** unit-test the tool registry (registration, schema, dispatch) and the loop with a stubbed Claude client (mock `tool_use` → assert handler called → assert `tool_result` fed back). Test the approval gate blocks destructive tools without confirmation.
- **Spotify:** unit-test `expand_spotify` URL parsing + pagination + None/local guards with a stubbed spotipy client.
- **STT/TTS adapters:** test backend selection + fallback paths with mocked providers (no network in tests).
- **Memory:** test SQLite read/write/summary + the `memory.json` import.
- **Voice loop:** integration-tested manually in a real VC (network + audio hardware); covered by smoke checks, not unit tests.
- Every module must `py_compile` clean; cogs must import without side effects at load.

## Risks

- **Python 3.14** may lack faster-whisper/ctranslate2 wheels and removed `audioop` → STT adapter must fall back to Google, and `audioop-lts` is required for the SpeechRecognitionSink path. Verify the deploy venv's Python version early.
- discord-ext-voice-recv is alpha (pinned `0.5.2a179`) — don't auto-upgrade; keep the BasicSink fallback.
- ElevenLabs over-the-wire latency is ~250–300ms+, not the advertised 75ms — acceptable for chat, benchmark from the host.
- yt-dlp's YouTube extractor breaks often — document periodic upgrades.
