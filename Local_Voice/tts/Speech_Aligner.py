import os
import asyncio
import subprocess
# from aeneas.executetask import ExecuteTask
# from aeneas.task import Task
import edge_tts
from pydub import AudioSegment

# Paths are relative to this file (Local_Voice/tts/) so the bot runs anywhere.
_TTS_DIR = os.path.dirname(os.path.abspath(__file__))
MP3_AUDIO_FILE = os.path.join(_TTS_DIR, "tts_input_audio", "input.mp3")
WAV_AUDIO_FILE = os.path.join(_TTS_DIR, "tts_input_audio", "input.wav")
TRANSCRIPTION_FILE = os.path.join(_TTS_DIR, "tts_input_transcription", "transcription.txt")
TIMING_OUTPUT_FILE = os.path.join(_TTS_DIR, "tts_output_timings", "timings.json")

def generate_txt_file(text):
    try:
        with open(TRANSCRIPTION_FILE, "w") as transcription:
            for word in text.split(" "):
                transcription.write(word + "\n")
    except Exception as e:
        print(f"Error Writing to {TRANSCRIPTION_FILE}: {e}")

async def generate_tts(voice="en-GB-RyanNeural"):
    try:
        with open(TRANSCRIPTION_FILE, "r") as transcription:
            text = transcription.read()

        tts = edge_tts.Communicate(text, voice)
        await tts.save(MP3_AUDIO_FILE)
    except Exception as e:
        print(f"Error producing TTS: {e}")

def convert_audio():
    successful_conversion = False
    try:
        sound = AudioSegment.from_mp3(MP3_AUDIO_FILE)
        sound = sound.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        sound.export(WAV_AUDIO_FILE, format="wav", codec="pcm_s16le")

        # Force a conservative PCM WAV via ffmpeg as a second pass for aeneas/scipy compatibility.
        normalized_wav = WAV_AUDIO_FILE + ".tmp.wav"
        subprocess.run([
            "ffmpeg", "-y", "-i", WAV_AUDIO_FILE,
            "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            normalized_wav
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.replace(normalized_wav, WAV_AUDIO_FILE)
        successful_conversion = True
    except Exception as e:
        print(f"Error converting audio: {e}")

    if successful_conversion and os.path.exists(MP3_AUDIO_FILE):
        os.remove(MP3_AUDIO_FILE)

    return successful_conversion

def run_align():
    if not os.path.exists(WAV_AUDIO_FILE):
        raise FileNotFoundError(f"Aligned WAV not found: {WAV_AUDIO_FILE}")

    config_string = "task_language=eng|os_task_file_format=json|is_text_type=plain"
    task = Task(config_string=config_string)
    task.audio_file_path_absolute = WAV_AUDIO_FILE
    task.text_file_path_absolute = TRANSCRIPTION_FILE
    task.sync_map_file_path_absolute = TIMING_OUTPUT_FILE

    ExecuteTask(task).execute()
    task.output_sync_map_file()
    print("Done! Check your JSON timings here:", task.sync_map_file_path_absolute)

async def main(text):
    generate_txt_file(text)
    await generate_tts()
    if not convert_audio():
        raise RuntimeError("TTS audio conversion failed before alignment")
    run_align()

if __name__ == "__main__":
    text = input("Enter txt to be converted: ")
    asyncio.run(main(text))
