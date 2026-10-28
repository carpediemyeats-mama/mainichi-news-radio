#!/usr/bin/env python3
"""Produce a gentle optional mindfulness radio episode with tested VOICEVOX + pydub.
Separate paths prevent changes to news, history, vocabulary, science, and pharmacist audio.
"""
import hashlib
import json
import tempfile
import time
from pathlib import Path

import requests
from pydub import AudioSegment
from pydub.generators import Sine

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "mindfulness" / "episode01.json"
OUT = ROOT / "site" / "mindfulness"
OUT.mkdir(parents=True, exist_ok=True)
API = "http://127.0.0.1:50021"


def silence(ms):
    return AudioSegment.silent(duration=int(ms), frame_rate=44100).set_channels(2)


def low_chime():
    """Original almost-inaudible opening/closing chord, with no rhythmic jingle."""
    a = Sine(196.00).to_audio_segment(duration=3500).apply_gain(-39)
    b = Sine(246.94).to_audio_segment(duration=3500).apply_gain(-44)
    c = Sine(293.66).to_audio_segment(duration=3500).apply_gain(-47)
    return a.overlay(b).overlay(c).set_channels(2).fade_in(1000).fade_out(1900)


def voice_id(name, style):
    response = requests.get(API + "/speakers", timeout=40)
    response.raise_for_status()
    for speaker in response.json():
        if speaker.get("name") == name:
            for st in speaker.get("styles", []):
                if st.get("name") == style:
                    print("VOICEVOX speaker confirmed:", name, style, st["id"], flush=True)
                    return st["id"]
    raise RuntimeError(f"VOICEVOX speaker or style missing: {name}/{style}")


def speak(text, speaker_id, rate, path):
    if not text or len(text) > 135:
        raise RuntimeError("Speech line absent or too long; check source script")
    for attempt in range(3):
        try:
            r = requests.post(API + "/audio_query", params={"text": text, "speaker": speaker_id}, timeout=90)
            r.raise_for_status()
            q = r.json()
            q["speedScale"] = rate
            q["intonationScale"] = 0.87
            q["pitchScale"] = -0.01
            q["volumeScale"] = 0.92
            q["prePhonemeLength"] = 0.14
            q["postPhonemeLength"] = 0.24
            r = requests.post(API + "/synthesis", params={"speaker": speaker_id}, json=q, timeout=240)
            r.raise_for_status()
            if not r.content.startswith(b"RIFF") or len(r.content) < 3000:
                raise RuntimeError("Invalid or empty synthesized WAV")
            path.write_bytes(r.content)
            return AudioSegment.from_wav(path).set_frame_rate(44100).set_channels(2)
        except Exception as err:
            print(f"Synthesis retry {attempt+1}/3: {err}", flush=True)
            if attempt == 2:
                raise
            time.sleep(4 * (attempt + 1))


def build():
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    if data["id"] != "mindfulness-episode-001" or len(data["chapters"]) != 5:
        raise RuntimeError("Wrong episode ID or chapter layout")
    lines = [line for ch in data["chapters"] for line in ch["lines"]]
    if not 25 <= len(lines) <= 45:
        raise RuntimeError("Unexpected script size")
    if not all(600 <= line["pause_ms"] <= 5000 for line in lines):
        raise RuntimeError("Pacing must be intentionally gentle")
    speaker_id = voice_id(data["voice"]["speaker"], data["voice"]["style"])
    rate = float(data["voice"]["rate"])
    if not 0.83 <= rate <= 1.0:
        raise RuntimeError("Unnatural speaking pace")

    whole = low_chime() + silence(900)
    chapter_marks = []
    with tempfile.TemporaryDirectory() as tmp:
        count = 0
        for ch in data["chapters"]:
            chapter_marks.append({"title": ch["title"], "start_seconds": round(len(whole) / 1000, 1)})
            for line in ch["lines"]:
                count += 1
                clip = speak(line["text"], speaker_id, rate, Path(tmp) / f"{count:03d}.wav")
                whole += clip + silence(line["pause_ms"])
                print("Mindfulness line", count, "at", round(len(whole) / 1000, 1), "seconds", flush=True)
    whole += low_chime() + silence(200)
    whole = whole.fade_in(80).fade_out(700)
    dest = OUT / "episode01.mp3"
    whole.export(dest, format="mp3", bitrate="128k", tags={
        "title": "こころの休憩室 第1回 頭の中がにぎやかな夜に",
        "artist": "VOICEVOX:青山龍星",
        "album": "こころの休憩室",
        "comment": "Original mindfulness script and quiet musical tone. Not medical treatment."
    })
    decoded = AudioSegment.from_mp3(dest)
    seconds = len(decoded) / 1000
    if not 210 <= seconds <= 720:
        raise RuntimeError(f"Unexpected runtime: {seconds:.1f}sec; adjust the script, not playback speed")
    if dest.stat().st_size < 300000 or abs(len(decoded) - len(whole)) > 600:
        raise RuntimeError("MP3 missing/corrupted or duration mismatch")
    meta = {
        "episode_id": data["id"],
        "episode_number": data["episode_number"],
        "title": data["title"],
        "series": data["series"],
        "audio_file": dest.name,
        "duration_seconds": round(seconds, 2),
        "duration_label": f"{int(seconds)//60}分{round(seconds)%60:02d}秒",
        "sha256": hashlib.sha256(dest.read_bytes()).hexdigest(),
        "chapters": chapter_marks,
        "voice_attribution": "VOICEVOX:青山龍星（ノーマル）",
        "notice": data["notice"]
    }
    (OUT / "episode01.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print("MINDFULNESS_MP3_VERIFIED", seconds, dest.stat().st_size, meta["sha256"], flush=True)


if __name__ == "__main__":
    build()
