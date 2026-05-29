import os
import warnings
import json
import re
from Local_Voice.Fish_ESP32 import fish_performance_test
import asyncio

with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore",
        message="pkg_resources is deprecated as an API.*",
        category=UserWarning,
    )
    # import pronouncing


TIMINGS_JSON = r"/home/gramapants/Desktop/Discord_Bot/Local_Voice/tts/tts_output_timings/timings.json"


def _clean_word(word: str) -> str:
    return re.sub(r"[^a-zA-Z']", "", (word or "")).strip().lower()


def build_movement_script(timings_json_path=TIMINGS_JSON):

    try:
        with open(timings_json_path, "r") as f:
            json_file = json.load(f)
    except Exception as e:
        print(f"Faild to load {timings_json_path}: {e}")
        return []

    timing_entries = []
    for fragment in json_file.get("fragments", []):
        raw_word = str(fragment.get("lines", "")).replace("[", "").replace("]", "").strip()
        word = _clean_word(raw_word)
        if not word:
            continue

        begin_time = float(fragment.get("begin", 0.0))
        end_time = float(fragment.get("end", begin_time))
        found_phonemes = pronouncing.phones_for_word(word.lower())
        timing_entries.append((word, begin_time, end_time, found_phonemes[0] if found_phonemes else None))

    print([entry[0] for entry in timing_entries])
    print("phonemes:", [entry[3] for entry in timing_entries])

    vowels = ['A', 'E', 'I', 'O', 'U']
    delay = 0
    script = []
    total_time = 0

    for word, begin_time, end_time, phoneme_string in timing_entries:
        delta_time = max((end_time - begin_time) * 1000, 1)
        total_time += delta_time

        if phoneme_string:
            phoneme_chunks = phoneme_string.split(" ")
        else:
            estimated_chunks = max(1, min(len(word) // 2, 4))
            phoneme_chunks = [word] * estimated_chunks

        time_per_chunk = delta_time / max(len(phoneme_chunks), 1)

        for chunk in phoneme_chunks:
            mouth_open = any(letter in vowels for letter in chunk)
            print(f"Chunk: {chunk}, mouth open: {mouth_open}, time per chunk: {time_per_chunk}")

            script.append({
                "part": "mouth",
                "state": "open" if mouth_open else "close",
                "duration": time_per_chunk,
                "delay": delay,
            })
            delay += time_per_chunk

            script.append({
                "part": "mouth",
                "state": "close" if mouth_open else "open",
                "duration": max(time_per_chunk * 0.35, 40),
                "delay": delay,
            })
            delay += max(time_per_chunk * 0.35, 40)

    if total_time > 0:
        script.insert(0, {"part": "head", "state": "turn", "duration": max(total_time + 250, 500), "delay": 0})

    for move in script:
        print(move)

    return script


async def animate_from_timings(timings_json_path=TIMINGS_JSON):
    script = build_movement_script(timings_json_path)
    if not script:
        return []

    await fish_performance_test(script)
    return script


def main():
    asyncio.run(animate_from_timings())




if __name__ == "__main__":
    main()
    #asyncio.run(fish_performance_test())