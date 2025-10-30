import os
import re
import sys
import time
import random
import asyncio
from gpiozero import OutputDevice

# Outdated, Used when connected to rpi



# === GPIO SETUP ===
MOUTH_OPEN = OutputDevice(27)
MOUTH_CLOSE = OutputDevice(22)
TAIL_FLOP = OutputDevice(17)
HEAD_UP = OutputDevice(18)

# === Long vowel emphasis ===
LONG_VOWELS = ['ee', 'ea', 'ie', 'ei', 'oa', 'oo', 'ou', 'ue', 'ai']

# === Helper: Word timing based on relative word length and vowels ===
async def get_word_timings(text, total_duration):
    words = re.findall(r"\b\w+\b", text)
    word_lengths = []
    for w in words:
        weight = len(w)
        if any(vowel in w.lower() for vowel in LONG_VOWELS):
            weight *= 1.5
        word_lengths.append(weight)

    total_weight = sum(word_lengths)
    timings = []
    t = 0.0
    for word, weight in zip(words, word_lengths):
        dur = (weight / total_weight) * total_duration
        timings.append((word, t, t + dur))
        t += dur
    return timings

# === Prepares word animation with optional pauses ===
async def prepare_sequence(text, duration):
    words = re.findall(r'\b\w+\b|[.,!?]', text)
    words_timed = await get_word_timings(text, duration)
    full_sequence = []
    j = 0
    for i, word in enumerate(words):
        if re.match(r'[.!?]', word):
            if j > 0:
                w, s, e = words_timed[j - 1]
                full_sequence.append((w, s, e, False))
                pause_start = e
                pause_end = pause_start + 0.35
                full_sequence.append(("__pause__", pause_start, pause_end, True))  # Trigger tail flop
        else:
            if j < len(words_timed):
                w, s, e = words_timed[j]
                full_sequence.append((w, s, e, False))
                j += 1
    return full_sequence

# === Optional: Flop tail before speaking to simulate "thinking" ===
async def tail_flop_randomly(duration=2.5):
    print(f"[Fish] Flopping tail for {duration:.1f}s (thinking)...")
    end_time = time.time() + duration
    while time.time() < end_time:
        TAIL_FLOP.on()
        await asyncio.sleep(0.1)
        TAIL_FLOP.off()
        await asyncio.sleep(random.uniform(0.3, 0.6))

# === Animate the fish ===
async def animate_fish(word_timing_list, max_duration):
    HEAD_UP.on()
    start_time = time.time()

    for word, start, end, flop in word_timing_list:
        duration = end - start
        elapsed = time.time() - start_time
        if elapsed + duration > max_duration - 0.05:
            break

        if word == "__pause__":
            MOUTH_OPEN.off()
            MOUTH_CLOSE.on()
            if flop:
                HEAD_UP.off()
                await asyncio.sleep(0.05)
                TAIL_FLOP.on()
                await asyncio.sleep(0.1)
                TAIL_FLOP.off()
                await asyncio.sleep(0.05)
                HEAD_UP.on()
                await asyncio.sleep(max(0, duration - 0.2))
            else:
                await asyncio.sleep(duration)
            continue

        # Mouth animation
        MOUTH_OPEN.on()
        MOUTH_CLOSE.off()
        await asyncio.sleep(duration * 0.75)
        MOUTH_OPEN.off()
        MOUTH_CLOSE.on()
        await asyncio.sleep(duration * 0.25)

    MOUTH_OPEN.off()
    MOUTH_CLOSE.on()
    TAIL_FLOP.off()
    HEAD_UP.off()

# === MAIN ENTRY ===
async def main():
    if len(sys.argv) < 3:
        print("Usage: python3 Fish_Speak_Animation.py '<text>' <duration_in_seconds> [optional_thinking_delay]")
        sys.exit(1)

    TEXT = sys.argv[1]
    DURATION = float(sys.argv[2])
    THINK_DELAY = float(sys.argv[3]) if len(sys.argv) > 3 else 2.5

    # await tail_flop_randomly(THINK_DELAY)
    word_sequence = await prepare_sequence(TEXT, DURATION)
    await animate_fish(word_sequence, DURATION)

if __name__ == "__main__":
    asyncio.run(main())
