import os
import sys
import ctypes
import asyncio
import subprocess
import signal
from concurrent.futures import ThreadPoolExecutor

# Suppress ALSA lib error messages (works on RPi)
try:
    ctypes.cdll.LoadLibrary('libasound.so').snd_lib_error_set_handler(None)
except Exception:
    pass

import speech_recognition as sr
import edge_tts
from pydub import AudioSegment
from Cog_Manager import handle_voice_command

# Paths and constants
VOICE = "en-GB-RyanNeural"
FILENAME = "audio/local_audio.wav"
DING_MP3 = "audio/ding.mp3"
DING_WAV = "audio/ding.wav"
WAKE_WORDS = ["hey", "gramabot", "jarvis", "gb", "bot", "bought", "grandma", "gabe", "billy"]
FISH_SPEAK_SCRIPT = "Fish_Scripts/Fish_Speak_Animation.py"

os.makedirs("audio", exist_ok=True)

# ThreadPoolExecutor for blocking calls
executor = ThreadPoolExecutor()

# === Helper functions ===
def convert_mp3_to_wav(mp3_file, wav_file):
    if os.path.exists(mp3_file) and not os.path.exists(wav_file):
        subprocess.run([
            "ffmpeg", "-y", "-i", mp3_file,
            "-ar", "44100", "-ac", "1", "-f", "wav", wav_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def convert_to_pcm(filename):
    pcm_filename = filename.replace(".wav", "_pcm.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", filename,
        "-ar", "44100", "-ac", "1", "-f", "wav", pcm_filename
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pcm_filename

async def play_audio_and_animate(filename, text=None):
    try:
        if text:
            audio = AudioSegment.from_wav(filename)
            duration_sec = str(len(audio) / 1000.0)
            fish_args = ["/usr/bin/python3", FISH_SPEAK_SCRIPT, text.strip(), duration_sec]
        else:
            fish_args = ["/usr/bin/python3", FISH_SPEAK_SCRIPT, "Silence", "1.0"]

        fish_process = await asyncio.create_subprocess_exec(*fish_args)

        process = await asyncio.create_subprocess_exec(
            "ffplay", "-nodisp", "-autoexit", filename,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        await asyncio.gather(
            process.communicate(),
            fish_process.wait()
        )

    except Exception as e:
        print("Playback or animation failed:", e)

async def generate_tts(text, filename):
    if os.path.exists(filename):
        os.remove(filename)
    tts = edge_tts.Communicate(text, VOICE)
    await tts.save(filename)

async def run(text):
    convert_mp3_to_wav(DING_MP3, DING_WAV)
    await play_audio_and_animate(DING_WAV)

    tail_process = await asyncio.create_subprocess_exec(
        "python3", "Fish_Scripts/Fish_Flap_Tail.py"
    )

    await generate_tts(text, FILENAME)
    pcm_file = convert_to_pcm(FILENAME)

    try:
        tail_process.send_signal(signal.SIGINT)
        await tail_process.wait()
    except Exception as e:
        print(f"[Tail Flap] Could not terminate: {e}")

    await play_audio_and_animate(pcm_file, text=text)

# === Blocking function for listening ===
def blocking_listen():
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.pause_threshold = 1
    with sr.Microphone() as source:
        print("[Speech] Listening...")
        audio = r.listen(source, timeout=3, phrase_time_limit=15)
        return r.recognize_google(audio).lower()

# === Async wrapper that runs blocking_listen in thread ===
async def recognize_speech():
    # Raise head up asynchronously
    head_up_proc = await asyncio.create_subprocess_exec(
        "python3", FISH_SPEAK_SCRIPT, "--head-up"
    )

    try:
        # Run the blocking listen in a separate thread so it doesn't block event loop
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, blocking_listen)
        return result

    except sr.WaitTimeoutError:
        print("[Speech] Timeout.")
    except sr.UnknownValueError:
        print("[Speech] Could not understand audio.")
    except sr.RequestError as e:
        print(f"[Speech] Recognition error: {e}")
    finally:
        # Lower head asynchronously and wait for head up process to finish
        head_down_proc = await asyncio.create_subprocess_exec(
            "python3", FISH_SPEAK_SCRIPT, "--head-down"
        )
        await head_down_proc.wait()
        await head_up_proc.wait()

    return None

async def wait_for_wake_word():
    while True:
        text = await recognize_speech()
        if text:
            print("Heard:", text)
            for wake_word in WAKE_WORDS:
                if wake_word in text:
                    command = text.replace(wake_word, "", 1).strip()
                    return command
        await asyncio.sleep(0.05)  # Tiny yield

async def follow_up_loop(client):
    while True:
        text = await recognize_speech()
        if not text:
            print("[Follow-up] No response. Ending conversation.")
            break
        if "stop" in text:
            print("[Follow-up] Detected stop command.")
            break
        print("[Follow-up] Heard:", text)
        response = await handle_voice_command(text, client)
        await run(response)

async def main(client):
    while True:
        command = await wait_for_wake_word()
        if command:
            response = await handle_voice_command(command, client)
            await run(response)
            await follow_up_loop(client)
        await asyncio.sleep(0.1)  # Yield control to event loop

async def voice_loop_entrypoint(client):
    print("[Local_Voice] Voice loop entry started.")
    await send_startup_message(client)
    await main(client)

async def send_startup_message(client):
    try:
        print("[Local_Voice] Attempting to send startup message...")
        channel = client.get_channel(1373846484683853885)
        if channel:
            await channel.send("Local voice system is now online and listening for wake words.")
        else:
            print("[Local_Voice] Wake channel not found.")
    except Exception as e:
        print(f"[Local_Voice] Error sending startup message: {e}")