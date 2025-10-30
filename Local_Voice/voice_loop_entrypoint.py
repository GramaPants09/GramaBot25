# Local_Voice/voice_loop_entrypoint.py

import asyncio
import subprocess
from pydub import AudioSegment
import os

FISH_SPEAK_SCRIPT = "Fish_Scripts/Fish_Speak_Animation.py"

async def animate_fish_from_file(pcm_file, tail_on_silence=True):
    try:
        audio = AudioSegment.from_wav(pcm_file)
        duration_sec = str(len(audio) / 1000.0)

        args = ["/usr/bin/python3", FISH_SPEAK_SCRIPT, "Music", duration_sec]
        if tail_on_silence:
            args.append("--tail")

        await asyncio.create_subprocess_exec(*args)
    except Exception as e:
        print(f"[animate_fish_from_file Error] {e}")
