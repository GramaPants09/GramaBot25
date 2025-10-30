import os
import sys
import ctypes
import asyncio
import subprocess
import signal


# Main listening File

# Suppress ALSA lib error messages using ctypes (useful on RPi)
try:
    ctypes.cdll.LoadLibrary('libasound.so').snd_lib_error_set_handler(None)
except Exception:
    pass

# Now safe to import audio modules
import speech_recognition as sr
from pydub import AudioSegment

# Your existing manager that turns a command string into a reply
from Cog_Manager import handle_voice_command

# Use your aligner and phoneme splitter modules (they exist in this project)
import Local_Voice.tts.Speech_Aligner as Speech_Aligner
import Local_Voice.Phoneme_Split as Phoneme_Split

# For small head up/down actions when listening
from Local_Voice.Fish_ESP32 import send_test_action

# Paths and constants (keep these consistent with your Speech_Aligner module)
# Speech_Aligner uses these internal paths:
# MP3_AUDIO_FILE = "/home/....../Local_Voice/tts/tts_input_audio/input.mp3"
# WAV_AUDIO_FILE = "/home/....../Local_Voice/tts/tts_input_audio/input.wav"
# TIMING_OUTPUT_FILE = "/home/....../Local_Voice/tts/tts_output_timings/timings.json"
# If you changed those in Speech_Aligner, update below accordingly.
DING_MP3 = "audio/ding.mp3"
DING_WAV = "audio/ding.wav"
# The WAV that Speech_Aligner converts-to is WAV_AUDIO_FILE inside Speech_Aligner module.
# We will reference it via Speech_Aligner.WAV_AUDIO_FILE if available, else fallback.
try:
    WAV_OUTPUT = Speech_Aligner.WAV_AUDIO_FILE
except Exception:
    WAV_OUTPUT = "tts/tts_input_audio/input.wav"

# Wake words
WAKE_WORDS = ["hey", "gramabot", "jarvis", "gb", "bot", "bought", "grandma", "gabe", "billy"]

# Ensure audio directory exists
os.makedirs("audio", exist_ok=True)

# Helper: convert ding mp3 -> wav (used for startup ding)
def convert_mp3_to_wav(mp3_file, wav_file):
    if os.path.exists(mp3_file) and (not os.path.exists(wav_file)):
        subprocess.run([
            "ffmpeg", "-y", "-i", mp3_file,
            "-ar", "44100", "-ac", "1", "-f", "wav", wav_file
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# Convert produced WAV to PCM-like file for playback (keeps behavior you had)
def convert_to_pcm(filename):
    pcm_filename = filename.replace(".wav", "_pcm.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", filename,
        "-ar", "44100", "-ac", "1", "-f", "wav", pcm_filename
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pcm_filename

# Play audio using ffplay (non-blocking via asyncio subprocess)
async def play_audio_file(filename):
    if not os.path.exists(filename):
        print(f"[Playback] Audio file not found: {filename}")
        return
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffplay", "-nodisp", "-autoexit", filename,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        await proc.communicate()
    except Exception as e:
        print("[Playback] Failed to play audio:", e)

# Run the full speak flow:
# 1) Generate TTS + timing using Speech_Aligner (this produces WAV + timings JSON).
# 2) Convert WAV to PCM-suffixed file (keeps previous playback behavior).
# 3) Run Phoneme_Split.main() which will create and send the movement script to ESP32.
# 4) Play the audio while fish moves (Phoneme_Split already waits for fish reply when sending).
async def run_speak_flow(text):
    try:
        try:
            asyncio.create_task(send_test_action("head", "turn", duration=1000))
        except Exception:
            pass
        # Play ding first if available
        convert_mp3_to_wav(DING_MP3, DING_WAV)
        if os.path.exists(DING_WAV):
            await play_audio_file(DING_WAV)

        # 1) Use Speech_Aligner to generate the TTS audio and timings.
        # Speech_Aligner.main is async and will:
        #   - write transcription
        #   - call edge_tts to save MP3
        #   - convert to WAV and produce timings.json via aeneas
        await Speech_Aligner.main(text)

        # 2) Convert the produced WAV to a pcm-style filename for playback (optional)
        pcm_file = convert_to_pcm(WAV_OUTPUT) if os.path.exists(WAV_OUTPUT) else None

        # 3) Start the phoneme -> ESP32 pipeline (this will call fish_performance_test internally)
        # Phoneme_Split.main() is currently synchronous and calls asyncio.run() internally to send the sequence.
        # Call it in an executor to avoid blocking the event loop.
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, Phoneme_Split.main)

        # 4) Play the produced PCM (if exists); otherwise play the WAV
        if pcm_file and os.path.exists(pcm_file):
            await play_audio_file(pcm_file)
        elif os.path.exists(WAV_OUTPUT):
            await play_audio_file(WAV_OUTPUT)
        else:
            print("[run_speak_flow] No audio file to play after TTS.")
    except Exception as e:
        print("[run_speak_flow] Error during speak flow:", e)

# Speech recognition wrapper using speech_recognition
async def recognize_speech(timeout=3):
    r = sr.Recognizer()
    r.energy_threshold = 300
    r.pause_threshold = 1

    # Use the default microphone device. If you need a specific device index, set it here:
    mic_kwargs = {}
    # mic_kwargs["device_index"] = 1   # <-- uncomment and set if necessary

    try:
        with sr.Microphone(**mic_kwargs) as source:
            print("[Local_Voice] Listening...")

            

            # Blocking listen (speech_recognition is synchronous)
            # run inside executor so we can keep async API
            loop = asyncio.get_running_loop()
            audio = await loop.run_in_executor(None, lambda: r.listen(source, timeout=timeout, phrase_time_limit=15))

            

            # Recognize (Google recognizer used previously)
            try:
                text = await loop.run_in_executor(None, lambda: r.recognize_google(audio).lower())
                return text
            except sr.UnknownValueError:
                print("[Speech] Could not understand audio.")
            except sr.RequestError as e:
                print(f"[Speech] Recognition error: {e}")
            except Exception as e:
                print(f"[Speech] Unexpected recognition error: {e}")
    except sr.WaitTimeoutError:
        print("[Speech] Timeout waiting for speech.")
    except Exception as e:
        print("[Speech] Microphone error:", e)

    return None

# Wait continuously until a wake word is heard; returns the remainder (command)
async def wait_for_wake_word():
    while True:
        text = await recognize_speech()
        if text:
            print("[Local_Voice] Heard:", text)
            for wake_word in WAKE_WORDS:
                if wake_word in text:
                    # remove only the first occurrence

                    try:
                        asyncio.create_task(send_test_action("head", "turn", duration=1000))
                    except Exception:
                        pass


                    command = text.replace(wake_word, "", 1).strip()
                    print(f"[Local_Voice] Wake word '{wake_word}' detected, command -> '{command}'")
                    return command
        await asyncio.sleep(0.2)
# After initial response, allow quick follow-ups; stops on "stop" or silence
async def follow_up_loop(client):
    while True:
        text = await recognize_speech(timeout=10)
        if not text:
            print("[Follow-up] No response. Ending conversation.")
            break
        if "stop" in text:
            print("[Follow-up] Detected stop command.")
            break
        print("[Follow-up] Heard follow-up:", text)
        response = await handle_voice_command(text, client)
        await run_speak_flow(response)

# Main voice loop
async def main(client):
    while True:
        command = await wait_for_wake_word()
        if command:
            response = await handle_voice_command(command, client)
            await run_speak_flow(response)
            await follow_up_loop(client)

# Entrypoint that your bot can call (e.g., create_task from Cog_Manager)
async def voice_loop_entrypoint(client):
    print("[Local_Voice] Voice loop starting...")
    try:
        await send_startup_message(client)
    except Exception as e:
        print("[Local_Voice] Could not send startup message:", e)
    await main(client)

# Optional: notify a channel when starting
async def send_startup_message(client):
    try:
        print("[Local_Voice] Sending startup message (if channel found).")
        channel = client.get_channel(1373846484683853885)
        if channel:
            await channel.send("? Local voice system is now online and listening for wake words.")
        else:
            print("[Local_Voice] Wake channel not found.")
    except Exception as e:
        print(f"[Local_Voice] Error sending startup message: {e}")

# For manual testing (if you run this file directly)
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--test", action="store_true", help="Run a simple test speak flow")
    args = parser.parse_args()

    if args.test:
        async def test():
            # quick test (replace with any text)
            await run_speak_flow("Hello! This is a local voice test.")
        asyncio.run(test())