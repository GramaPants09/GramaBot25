# GramaBot25 v2 Agentic Upgrade — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn GramaBot25 into an agentic bot with a Claude tool-use brain, multi-user voice chat, Spotify-linked music, and a Butcher ElevenLabs voice — plus codebase cleanup.

**Architecture:** A central `AgentBrain` runs a bounded Claude tool-use loop; every ability (music, voice, aura, moderation, OpenClaw RPC) is a registered tool shimming into existing cogs. Voice in = faster-whisper STT; voice out = ElevenLabs TTS with edge fallback. Spotify links resolve to track names fed through the existing yt-dlp pipeline.

**Tech Stack:** discord.py 2.6, discord-ext-voice-recv, anthropic SDK, spotipy, faster-whisper, elevenlabs, edge-tts, yt-dlp, SQLite.

**Conventions:** New deps degrade gracefully when their key/library is missing (logged warning + fallback). Every module `py_compile`s clean. Unit tests use stubs (no network). Commit per task.

---

## File Structure

**New:**
- `cogs/AI/brain.py` — `AgentBrain`, `ToolContext`, the tool-use loop, Claude + OpenRouter-fallback seam.
- `cogs/AI/persona.py` — base Butcher system prompt + per-user overlays.
- `cogs/AI/memory.py` — `Memory` (SQLite) + `memory.json` importer.
- `cogs/AI/tools/__init__.py` — imports all tool modules so the registry populates.
- `cogs/AI/tools/registry.py` — `@tool` decorator, `Tool`, registry accessors, `anthropic_schemas()`.
- `cogs/AI/tools/music_tools.py`, `voice_tools.py`, `aura_tools.py`, `mod_tools.py`, `openclaw_tools.py`, `search_tools.py` — tool handlers.
- `cogs/AI/tools/openclaw.py` — WebSocket JSON-RPC client.
- `cogs/AI/approval.py` — Discord Approve/Reject button View for gated tools.
- `cogs/Audio/tts.py` — `synthesize()` (ElevenLabs → edge fallback).
- `cogs/Audio/stt.py` — backend-selected transcription + sink `process_cb` factory.
- `cogs/Audio/spotify.py` — `is_spotify_url`, `expand_spotify`.
- `tests/` — `test_registry.py`, `test_brain_loop.py`, `test_memory.py`, `test_spotify.py`, `test_tts.py`, `test_stt.py`, `test_persona.py`.

**Modified:**
- `cogs/AI/AI.py` — delegate to `AgentBrain`; keep commands.
- `cogs/AI/RespondInChat.py` — route to brain; fix `KeyError`.
- `cogs/Audio/VoiceAI.py` — multi-user, new STT/TTS adapters, brain routing.
- `cogs/Audio/Music.py` — Spotify expansion in `play`.
- `GramaBot25.py` — fix mojibake reload messages.
- `Local_Voice/tts/Speech_Aligner.py`, `Local_Voice/Phoneme_Split.py` — repo-relative paths.
- `requirements.txt` — add deps.

**Deleted:** `AI_updated_Ollama.py`, `cogs/AI/AI_backup.py`.

---

## Locked interfaces (use these signatures verbatim)

```python
# cogs/AI/tools/registry.py
@dataclass
class Tool:
    name: str
    description: str
    schema: dict                  # JSON schema -> Anthropic input_schema
    handler: Callable[..., Awaitable[str]]
    gated: bool = False

def tool(name: str, description: str, schema: dict, *, gated: bool = False): ...  # decorator
def get_tool(name: str) -> Tool | None: ...
def all_tools() -> list[Tool]: ...
def anthropic_schemas() -> list[dict]: ...   # [{"name","description","input_schema"}]

# cogs/AI/brain.py
@dataclass
class ToolContext:
    client: "discord.Client"
    guild: "discord.Guild | None"
    channel: "discord.abc.Messageable | None"
    user: "discord.abc.User | None"
    voice: bool = False
    request_approval: "Callable[[Tool, dict], Awaitable[bool]] | None" = None

class AgentBrain:
    def __init__(self, client, *, memory=None,
                 model="claude-sonnet-4-6", fast_model="claude-haiku-4-5",
                 max_iterations=8): ...
    async def respond(self, *, user, channel, guild, text,
                      voice: bool = False) -> str: ...

# Tool handler signature (every handler):
#   async def handler(ctx: ToolContext, **kwargs) -> str

# cogs/AI/memory.py
class Memory:
    def __init__(self, db_path: str = "data/brain.db"): ...
    def add_turn(self, user_id: str, channel_id: str, role: str, content: str) -> None: ...
    def history(self, user_id: str, channel_id: str, limit: int = 20) -> list[dict]: ...
    def get_summary(self, user_id: str, channel_id: str) -> str | None: ...
    def set_summary(self, user_id: str, channel_id: str, summary: str) -> None: ...
    @classmethod
    def import_json(cls, json_path: str, db_path: str) -> int: ...

# cogs/Audio/tts.py
async def synthesize(text: str, *, out_dir: str = "audio") -> str | None: ...   # path or None

# cogs/Audio/stt.py
def transcribe_wav(wav_path: str) -> str: ...
def make_process_cb(): ...   # returns a callable compatible with SpeechRecognitionSink(process_cb=)

# cogs/Audio/spotify.py
def is_spotify_url(text: str) -> bool: ...
def expand_spotify(url: str) -> list[str]: ...   # ["artist - title", ...]

# cogs/AI/tools/openclaw.py
async def openclaw_call(method: str, params: dict | None = None, *,
                        url: str | None = None, token: str | None = None,
                        timeout: float = 10.0) -> dict: ...
```

---

## Task 1: Tool registry

**Files:** Create `cogs/AI/tools/registry.py`, `cogs/AI/tools/__init__.py`; Test `tests/test_registry.py`.

- [ ] **Step 1 — failing test** (`tests/test_registry.py`): register a dummy tool via `@tool("ping","desc",{"type":"object","properties":{}})`; assert `get_tool("ping")` returns it, `all_tools()` contains it, and `anthropic_schemas()[0]` has keys `name/description/input_schema` with `input_schema` equal to the passed schema.
- [ ] **Step 2 — run, expect ImportError/FAIL.**
- [ ] **Step 3 — implement** the dataclass, module-level `_REGISTRY`, decorator (returns the fn unchanged), and accessors. `anthropic_schemas()` maps each Tool to `{"name","description","input_schema":schema}`.
- [ ] **Step 4 — run, expect PASS.**
- [ ] **Step 5 — commit:** `feat(ai): tool registry + @tool decorator`.

## Task 2: Memory (SQLite)

**Files:** Create `cogs/AI/memory.py`; Test `tests/test_memory.py`.

- [ ] **Step 1 — failing test:** with a temp db, `add_turn("u","c","user","hi")` then `history("u","c")` returns `[{"role":"user","content":"hi"}]`; `set_summary`/`get_summary` round-trip; `import_json` of a small fixture (`{"u":["User: hi","there"]}`) returns count and populates history.
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement:** `CREATE TABLE IF NOT EXISTS turns(user_id,channel_id,role,content,ts)` and `summaries(user_id,channel_id,summary)`; parameterized inserts; `history` orders by rowid, last `limit`; `import_json` parses the old `"User: x"` / bare-assistant convention into role-tagged turns keyed `(key, "legacy")`.
- [ ] **Step 4 — run, expect PASS.**
- [ ] **Step 5 — commit:** `feat(ai): SQLite memory + json importer`.

## Task 3: Persona

**Files:** Create `cogs/AI/persona.py`; Test `tests/test_persona.py`.

- [ ] **Step 1 — failing test:** `system_prompt_for("local_user")` contains the Butcher base; `system_prompt_for("915043571940343919")` contains both the base and that user's overlay; unknown id returns base only.
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement:** `BUTCHER_BASE` (gruff cockney, London slang, cynical, never narrate, no asterisks, hates the 13-month calendar, owned by GramaPants); move the 6 existing per-user prompts into `OVERLAYS`; `system_prompt_for(user_id, in_chat=False)` concatenates base + overlay.
- [ ] **Step 4 — run, expect PASS.**
- [ ] **Step 5 — commit:** `feat(ai): Butcher persona + per-user overlays`.

## Task 4: AgentBrain tool-use loop

**Files:** Create `cogs/AI/brain.py`; Test `tests/test_brain_loop.py`.

- [ ] **Step 1 — failing test:** inject a fake Claude client whose first response is a `tool_use` for a registered test tool (`echo`, returns its arg) and whose second response is final text. Assert: handler ran, the assistant tool_use message + the `tool_result` were appended in that order, final text returned. Second test: a `gated` tool with `request_approval` returning `False` is NOT executed and the loop reports denial.
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement:** `ToolContext`; `AgentBrain.respond` builds messages from `memory.history` + `persona.system_prompt_for`; loop ≤ `max_iterations`: call client with `tools=anthropic_schemas()`; for each `tool_use` block, look up the Tool, run approval if `gated`, dispatch handler with `ToolContext`, collect `tool_result` blocks; append assistant message then a user message of results; stop on a text-only stop. Provider seam: real client = `AsyncAnthropic`; if `ANTHROPIC_API_KEY` missing, fall back to the legacy OpenRouter chat (no tools) so chat still works. Persist turns to memory.
- [ ] **Step 4 — run, expect PASS.**
- [ ] **Step 5 — commit:** `feat(ai): AgentBrain bounded tool-use loop`.

## Task 5: Approval gate View

**Files:** Create `cogs/AI/approval.py`. (Manual/integration — no unit test; import-clean check.)

- [ ] **Step 1 — implement** `ApprovalView(discord.ui.View)` with Approve/Reject buttons restricted to admins/owner, plus `async def request_approval(channel, user, tool, args, timeout=60) -> bool` that posts an embed describing the tool call and awaits a click (default deny on timeout / no channel → owner-only allow). 
- [ ] **Step 2 — `python -m py_compile cogs/AI/approval.py`; expect clean.**
- [ ] **Step 3 — commit:** `feat(ai): destructive-tool approval gate`.

## Task 6: Tool handlers (music, voice, aura, mod, openclaw, search)

**Files:** Create `cogs/AI/tools/openclaw.py` + the six `*_tools.py`; wire imports in `tools/__init__.py`. Test `tests/test_registry.py` extended: assert expected tool names are all registered after `import cogs.AI.tools`.

- [ ] **Step 1 — failing test:** after `import cogs.AI.tools`, assert names present: `play_music, skip_music, pause_music, resume_music, stop_music, queue_status, join_voice, leave_voice, speak, get_aura, add_aura, set_aura, timeout_user, kick_user, ban_user, openclaw_rpc, web_search`; assert `timeout_user/kick_user/ban_user/openclaw_rpc` are `gated`.
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement handlers** as thin shims: music tools call `ctx.client.get_cog("Music")` methods; voice tools call `VoiceAI`; aura tools call the Aura manager; mod tools re-check `ctx.user`'s guild perms + role hierarchy then act; `openclaw_rpc` calls `openclaw_call`; `web_search` returns a stub message if no provider key. Each returns a short human-readable result string. `openclaw.py`: connect via `websockets`, send `{"jsonrpc":"2.0","id":1,"method","params","token"}`, await response, return result dict.
- [ ] **Step 4 — run, expect PASS; `py_compile` all new files.**
- [ ] **Step 5 — commit:** `feat(ai): tool handlers + OpenClaw RPC client`.

## Task 7: Port AI cog + RespondInChat to the brain

**Files:** Modify `cogs/AI/AI.py`, `cogs/AI/RespondInChat.py`.

- [ ] **Step 1 — implement:** `AI` cog instantiates one shared `AgentBrain` (with `Memory`), runs `memory.import_json` once on first load; `ask`/`grama_bot`/slash route through `brain.respond`. Keep `_speak_response_locally`. `RespondInChat`: route to the shared brain; **fix** the `del self.listening_channels[...]` `KeyError` by guarding with `if message.channel.id in self.listening_channels`.
- [ ] **Step 2 — `py_compile` both; import-load check** (`python -c "import cogs.AI.AI"` with deps may fail offline — at minimum compile clean).
- [ ] **Step 3 — commit:** `refactor(ai): route AI + RespondInChat through AgentBrain; fix KeyError`.

## Task 8: TTS adapter

**Files:** Create `cogs/Audio/tts.py`; Test `tests/test_tts.py`.

- [ ] **Step 1 — failing test:** monkeypatch the elevenlabs path to raise → assert `synthesize` falls through to the edge path (monkeypatched to write a dummy file) and returns that path; with no `ELEVENLABS_API_KEY`, assert it goes straight to edge.
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement:** if `ELEVENLABS_API_KEY` + `ELEVENLABS_VOICE_ID` set, call ElevenLabs (`eleven_flash_v2_5`, `output_format="pcm_48000"`) → wrap PCM into a WAV (48k/mono/s16le) at `out_dir/voice_<ts>.wav`; on any error or missing key, `edge_tts.Communicate(text, "en-GB-RyanNeural").save(mp3)`. Return the path.
- [ ] **Step 4 — run, expect PASS.**
- [ ] **Step 5 — commit:** `feat(audio): ElevenLabs TTS adapter w/ edge fallback`.

## Task 9: STT adapter

**Files:** Create `cogs/Audio/stt.py`; Test `tests/test_stt.py`.

- [ ] **Step 1 — failing test:** with `STT_BACKEND` unset and faster-whisper unavailable, `transcribe_wav` must not raise — it returns "" or a Google result; selection logic returns the configured backend name from a `_select_backend()` helper (test that `_select_backend()` honors the env var).
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement:** `_select_backend()` reads `STT_BACKEND` (default `whisper`); lazy-load faster-whisper (`WhisperModel("small", compute_type="int8")`, cached module-global); `transcribe_wav` downmixes/resamples to 16k mono (ffmpeg subprocess) then runs the backend; `make_process_cb()` returns a callable the SpeechRecognitionSink can call. On import failure of faster-whisper, log + fall back to `speech_recognition.recognize_google`.
- [ ] **Step 4 — run, expect PASS.**
- [ ] **Step 5 — commit:** `feat(audio): pluggable STT adapter (faster-whisper default)`.

## Task 10: Voice rework

**Files:** Modify `cogs/Audio/VoiceAI.py`.

- [ ] **Step 1 — implement:** replace single-target filtering with multi-user; prefer `voice_recv.extras.speechrecognition.SpeechRecognitionSink(process_cb=stt.make_process_cb(), text_cb=on_final)` where `on_final(user, text)` schedules brain routing on the loop; fall back to the existing BasicSink+buffer path (now using `stt.transcribe_wav`) if the extras sink is unavailable. Route finalized `"<name> said: <text>"` → shared `AgentBrain.respond(..., voice=True)` → `tts.synthesize` → play. Keep the `speaking_guilds` self-mute gate. Add wake-word/120s-window trigger gating.
- [ ] **Step 2 — `py_compile cogs/Audio/VoiceAI.py`; expect clean.**
- [ ] **Step 3 — commit:** `feat(audio): multi-user voice chat through AgentBrain + Butcher TTS`.

## Task 11: Spotify

**Files:** Create `cogs/Audio/spotify.py`; Modify `cogs/Audio/Music.py`; Test `tests/test_spotify.py`.

- [ ] **Step 1 — failing test:** `is_spotify_url` true for `open.spotify.com/track/...` and `spotify:track:...`, false for a plain query/YouTube URL. With a stubbed spotipy client, `expand_spotify` on a playlist returns flattened `"artist - title"` strings, paginates via `next`, and skips `None`/`is_local` items.
- [ ] **Step 2 — run, expect FAIL.**
- [ ] **Step 3 — implement** `spotify.py` (lazy `SpotifyClientCredentials`, track/album/playlist branches, pagination, guards). In `Music.play`: if `is_spotify_url(query)`, `tracks = expand_spotify(query)`; enqueue all; else current behavior. Friendly message if creds missing.
- [ ] **Step 4 — run, expect PASS.**
- [ ] **Step 5 — commit:** `feat(audio): Spotify link resolution into yt-dlp queue`.

## Task 12: Cleanups + deps

**Files:** Delete `AI_updated_Ollama.py`, `cogs/AI/AI_backup.py`; Modify `GramaBot25.py`, `Local_Voice/tts/Speech_Aligner.py`, `Local_Voice/Phoneme_Split.py`, `requirements.txt`.

- [ ] **Step 1 — implement:** delete the two dead files; replace `?` glyphs in `reload`/`reload_all` with ✅/❌; replace hardcoded `/home/gramapants/Desktop/Discord_Bot/...` with paths derived from a repo-root constant; append `anthropic`, `spotipy`, `faster-whisper`, `elevenlabs`, `audioop-lts; python_version >= "3.13"` to requirements.
- [ ] **Step 2 — `py_compile` the modified Python files; expect clean.**
- [ ] **Step 3 — commit:** `chore: remove dead AI files, fix mojibake + hardcoded paths, add deps`.

## Task 13: Full verification

- [ ] **Step 1 —** `python -m py_compile` across all changed/new `.py` files; `pytest -q` for the unit suite (all green).
- [ ] **Step 2 —** Adversarial multi-agent code review of the branch diff; triage findings.
- [ ] **Step 3 —** Fix confirmed issues; final commit.

---

## Self-review notes

- **Spec coverage:** brain+tools (T1–T7), TTS (T8), STT+voice (T9–T10), Spotify (T11), OpenClaw (T6), persona (T3), memory (T2), cleanups (T12). All spec sections mapped.
- **Type consistency:** handler signature `async (ctx, **kwargs) -> str`, `Tool` fields, `AgentBrain.respond` kwargs, and adapter signatures are reused identically across tasks.
- **Graceful degradation:** every external key (Anthropic, ElevenLabs, Spotify, STT) has a defined fallback so the bot boots without it.
