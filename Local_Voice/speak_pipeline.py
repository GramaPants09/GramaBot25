import asyncio
import os
import subprocess

import Local_Voice.Phoneme_Split as Phoneme_Split
import Local_Voice.tts.Speech_Aligner as Speech_Aligner
from Local_Voice.Fish_ESP32 import fish_performance_test, send_test_action


DING_MP3 = "audio/ding.mp3"
DING_WAV = "audio/ding.wav"

try:
	WAV_OUTPUT = Speech_Aligner.WAV_AUDIO_FILE
except Exception:
	WAV_OUTPUT = "tts/tts_input_audio/input.wav"


_speech_lock = asyncio.Lock()


def convert_mp3_to_wav(mp3_file, wav_file):
	if os.path.exists(mp3_file) and (not os.path.exists(wav_file)):
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


async def play_audio_file(filename):
	if not os.path.exists(filename):
		print(f"[Playback] Audio file not found: {filename}")
		return False

	try:
		proc = await asyncio.create_subprocess_exec(
			"ffplay", "-nodisp", "-autoexit", "-hide_banner", "-loglevel", "error", filename,
			stdout=subprocess.DEVNULL,
			stderr=subprocess.PIPE
		)
		_, stderr = await proc.communicate()
		if proc.returncode != 0:
			err = stderr.decode(errors="ignore").strip() if stderr else "unknown ffplay error"
			print(f"[Playback] ffplay failed ({proc.returncode}): {err}")
			return False

		print(f"[Playback] Played audio: {filename}")
		return True
	except Exception as e:
		print("[Playback] Failed to play audio:", e)
		return False


def _normalize_tts_text(text: str) -> str:
	return " ".join((text or "").replace("```", " ").split())


async def speak_text_with_fish(text: str, play_ding: bool = False, head_turn: bool = True):
	clean_text = _normalize_tts_text(text)
	if not clean_text:
		return None

	async with _speech_lock:
		try:
			if head_turn:
				try:
					asyncio.create_task(send_test_action("head", "turn", duration=1000))
				except Exception:
					pass

			if play_ding:
				convert_mp3_to_wav(DING_MP3, DING_WAV)
				if os.path.exists(DING_WAV):
					await play_audio_file(DING_WAV)

			await Speech_Aligner.main(clean_text)

			pcm_file = convert_to_pcm(WAV_OUTPUT) if os.path.exists(WAV_OUTPUT) else None
			audio_file = pcm_file if pcm_file and os.path.exists(pcm_file) else WAV_OUTPUT
			if not os.path.exists(audio_file):
				print("[speak_text_with_fish] No audio file produced after TTS.")
				return None

			print(f"[speak_text_with_fish] Using audio file: {audio_file}")

			loop = asyncio.get_running_loop()
			script = await loop.run_in_executor(None, Phoneme_Split.build_movement_script)
			if not script:
				print("[speak_text_with_fish] No fish movement script generated.")
				await play_audio_file(audio_file)
				return audio_file

			await asyncio.gather(
				fish_performance_test(script),
				play_audio_file(audio_file),
			)
			return audio_file
		except Exception as e:
			print("[speak_text_with_fish] Error during speak flow:", e)
			return None