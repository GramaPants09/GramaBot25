import os
import asyncio
from aeneas.executetask import ExecuteTask
from aeneas.task import Task
import edge_tts
from pydub import AudioSegment

MP3_AUDIO_FILE = r"/home/gramapants/Desktop/Discord_Bot/Local_Voice/tts/tts_input_audio/input.mp3"
WAV_AUDIO_FILE = r"/home/gramapants/Desktop/Discord_Bot/Local_Voice/tts/tts_input_audio/input.wav"
TRANSCRIPTION_FILE = r"/home/gramapants/Desktop/Discord_Bot/Local_Voice/tts/tts_input_transcription/transcription.txt"
TIMING_OUTPUT_FILE = r"/home/gramapants/Desktop/Discord_Bot/Local_Voice/tts/tts_output_timings/timings.json"

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
        sound.export(WAV_AUDIO_FILE, format="wav")
        successful_conversion = True
    except Exception as e:
        print(f"Error converting audio: {e}")

    if successful_conversion and os.path.exists(MP3_AUDIO_FILE):
        os.remove(MP3_AUDIO_FILE)

def run_align():
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
    convert_audio()
    run_align()

if __name__ == "__main__":
    text = input("Enter txt to be converted: ")
    asyncio.run(main(text))
