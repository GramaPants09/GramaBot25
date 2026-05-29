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
from Local_Voice.Fish_ESP32 import send_test_action
from Local_Voice.speak_pipeline import speak_text_with_fish

# Wake words
WAKE_WORDS = ["hey", "gramabot", "jarvis", "gb", "bot", "bought", "grandma", "gabe", "billy"]

# Ensure audio directory exists
os.makedirs("audio", exist_ok=True)

async def run_speak_flow(text):
    await speak_text_with_fish(text, play_ding=True)

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