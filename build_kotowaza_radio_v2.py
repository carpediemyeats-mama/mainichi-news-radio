#!/usr/bin/env python3
"""Build an original multi-voice Japanese proverb radio drama as a verified MP3.

Independent of the existing mainichi-news build script. Requires VOICEVOX
engine at 127.0.0.1:50021, pydub, requests and ffmpeg.
"""
import datetime
import json
import math
import re
import tempfile
import time
from pathlib import Path

import requests
from pydub import AudioSegment
from pydub.generators import Sine

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "kotowaza" / "episode01_v2.json"
OUTPUT = ROOT / "site" / "kotowaza"
OUTPUT.mkdir(parents=True, exist_ok=True)
API = "http://127.0.0.1:50021"
RATE = 44100
CAST = {
    "narrator": ("No.7", "アナウンス", 1.08),
    "tomo": ("ずんだもん", "ノーマル", 1.03),
    "mika": ("四国めたん", "ノーマル", 1.08),
    "manager": ("春日部つむぎ", "ノーマル", 1.04),
}


def silence(duration=200):
    return AudioSegment.silent(duration=duration, frame_rate=RATE).set_channels(2)


def note(midi, length, db=-26):
    hz = 440 * 2 ** ((midi - 69) / 12)
    return (Sine(hz).to_audio_segment(duration=int(length))
            .set_frame_rate(RATE).set_channels(2).apply_gain(db)
            .fade_in(15).fade_out(min(100, int(length) // 3)))


def music(bars=2, background=False):
    """Original arcade-like melody, created without copyrighted tracks."""
    step = 260 if not background else 320
    total = bars * 8 * step + 230
    out = silence(total)
    harmony = [
        (48, [60, 64, 67, 72]), (43, [59, 62, 67, 71]),
        (45, [57, 60, 64, 69]), (41, [57, 60, 65, 69]),
    ]
    for bar in range(bars):
        bass, chord = harmony[bar % 4]
        for beat in range(8):
            pos = (bar * 8 + beat) * step
            if beat % 2 == 0:
                out = out.overlay(note(bass, step * 1.35, -35 if background else -25), position=pos)
            if beat % 4 == 0:
                for tone in chord[1:4]:
                    out = out.overlay(note(tone, step * 2, -45 if background else -36), position=pos)
            if not background and beat not in (3, 7):
                melody = chord[(beat + bar) % len(chord)] + 12
                out = out.overlay(note(melody, step * 0.67, -27), position=pos + 20)
    return out.fade_in(150).fade_out(320)


def sfx(name):
    if name == "intro":
        return music(3) + silence(150)
    if name in ("outro", "ending"):
        return music(2) + silence(100)
    if name == "arcade":
        out = silence(1050)
        for i, midi in enumerate([72, 76, 79, 84, 79, 76]):
            out = out.overlay(note(midi, 105, -22), position=90 + i * 155)
        return out
    if name in ("ding", "win"):
        out = silence(720)
        for i, midi in enumerate([76, 80, 84, 88]):
            out = out.overlay(note(midi, 230, -23), position=i * 135)
        return out
    if name == "coin":
        return note(84, 120, -22) + note(91, 195, -22) + silence(160)
    if name in ("boing", "magic", "pop"):
        return note(55, 160, -22) + note(67, 170, -20) + note(79, 190, -22)
    if name in ("alarm", "laser"):
        return (note(82, 170, -23) + note(77, 170, -23)) * 2
    if name == "slip":
        return note(83, 120, -22) + note(76, 120, -22) + note(69, 150, -22)
    if name == "record":
        return note(46, 155, -23) + silence(170)
    if name == "laugh":
        return note(74, 120, -25) + note(77, 120, -25) + note(74, 110, -25)
    if name == "mystery":
        return note(52, 260, -26) + note(51, 330, -27)
    if name == "quiz":
        return music(1) - 5
    return silence(190)


def word_chunks(text, maximum=95):
    parts = re.findall(r"[^。！？!?]+[。！？!?]?", text)
    result = []
    for part in parts:
        part = part.strip()
        while len(part) > maximum:
            cut = max(part.rfind("、", 0, maximum), part.rfind("，", 0, maximum))
            if cut < 32:
                cut = maximum
            else:
                cut += 1
            result.append(part[:cut])
            part = part[cut:]
        if part:
            result.append(part)
    return result


def get_speakers():
    res = requests.get(API + "/speakers", timeout=40)
    res.raise_for_status()
    available = res.json()
    ids = {}
    for role, (voice, style, speed) in CAST.items():
        matched = [
            s["id"] for person in available if person.get("name") == voice
            for s in person.get("styles", []) if s.get("name") == style
        ]
        if len(matched) != 1:
            raise RuntimeError(f"VOICEVOX voice not available: {role}: {voice} / {style}")
        ids[role] = (matched[0], speed)
        print("VOICE:", role, voice, style, matched[0], flush=True)
    if len({v[0] for v in ids.values()}) != len(ids):
        raise RuntimeError("Different characters must use different voices")
    return ids


def speak(text, role, voices, target):
    speaker, speed = voices[role]
    for retry in range(3):
        try:
            query = requests.post(API + "/audio_query",
                                  params={"text": text, "speaker": speaker}, timeout=100)
            query.raise_for_status()
            parameters = query.json()
            parameters["speedScale"] = speed
            parameters["volumeScale"] = 1.0
            wav = requests.post(API + "/synthesis",
                                params={"speaker": speaker}, json=parameters, timeout=240)
            wav.raise_for_status()
            if not wav.content.startswith(b"RIFF") or len(wav.content) < 3000:
                raise RuntimeError("VOICEVOX returned invalid WAV data")
            target.write_bytes(wav.content)
            return AudioSegment.from_wav(target).set_frame_rate(RATE).set_channels(2)
        except Exception as e:
            print(f"VOICEVOX synthesis retry {retry + 1}: {e}", flush=True)
            if retry == 2:
                raise
            time.sleep(3 * (retry + 1))


def with_background(voice_audio, bed):
    repeating = (bed * ((len(voice_audio) // len(bed)) + 1))[:len(voice_audio)]
    return repeating.apply_gain(-13).overlay(voice_audio)


def build():
    episode = json.loads(SOURCE.read_text(encoding="utf-8"))
    voices = get_speakers()
    if len(episode["vocabulary"]) != 6 or len(episode["scenes"]) < 4:
        raise RuntimeError("Missing 6-word lesson or chapters")
    all_lines = " ".join(
        line.get("text", "") for scene in episode["scenes"] for line in scene["lines"])
    for entry in episode["vocabulary"]:
        if all_lines.count(entry["term"]) < 2:
            raise RuntimeError(f"Vocabulary insufficiently practiced: {entry['term']}")
    bed = music(4, background=True)
    whole = silence(60)
    chapters = []
    with tempfile.TemporaryDirectory() as temp:
        tmp = Path(temp)
        count = 0
        for index, scene in enumerate(episode["scenes"]):
            if index > 0:
                whole += (music(1) - 8) + silence(150)
            chapters.append({"title": scene["title"],
                             "start_seconds": round(len(whole) / 1000, 1)})
            for line in scene["lines"]:
                if "sfx" in line:
                    whole += sfx(line["sfx"]) + silence(170)
                elif "quiz_pause_ms" in line:
                    wait = line["quiz_pause_ms"]
                    if wait < 2500 or wait > 12000:
                        raise RuntimeError("Invalid quiz thinking time")
                    # Clear answer interval: five gentle countdown beeps and silence.
                    blank = silence(wait)
                    for tick in range(wait // 1000):
                        blank = blank.overlay(note(74, 90, -33), position=tick * 1000 + 60)
                    whole += blank
                else:
                    if line["who"] not in voices:
                        raise RuntimeError("Unrecognized actor")
                    clips = []
                    for chunk in word_chunks(line["text"]):
                        count += 1
                        clips.append(speak(chunk, line["who"], voices,
                                           tmp / f"{count:04d}.wav"))
                    if not clips:
                        raise RuntimeError("Empty dialogue")
                    combined = silence(65)
                    for j, clip in enumerate(clips):
                        if j:
                            combined += silence(140)
                        combined += clip
                    combined += silence(135)
                    whole += with_background(combined, bed)
            print("CHAPTER", scene["title"], round(len(whole) / 1000, 1), flush=True)
    whole = whole.fade_in(100).fade_out(850)
    out = OUTPUT / "episode01_v2.mp3"
    whole.export(out, format="mp3", bitrate="128k",
                 tags={"title": "第1回 消えた金色のメダル（推理強化版）",
                       "album": "ことわざ事件簿！",
                       "artist": "ことわざ事件簿！ / VOICEVOX",
                       "comment": "Original script, procedural music and sound effects"})
    decoded = AudioSegment.from_mp3(out)
    if out.stat().st_size < 300000 or len(decoded) < 360000:
        raise RuntimeError("Published MP3 unexpectedly short or empty")
    if abs(len(decoded) - len(whole)) > 450:
        raise RuntimeError("MP3 length mismatch")
    duration = round(len(decoded) / 1000)
    build_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    metadata = {
        "episode_id": episode["id"], "series": episode["series"],
        "edition": episode["edition"], "title": episode["title"],
        "seconds": duration, "duration_label": f"{duration // 60}分{duration % 60}秒",
        "build_id": build_id, "filename": "episode01_v2.mp3",
        "chapters": chapters, "vocabulary": episode["vocabulary"]
    }
    (OUTPUT / "episode01_v2.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUCCESS", out, out.stat().st_size, "bytes", duration, "seconds", flush=True)
    if duration < 480 or duration > 780:
        print("NOTE: 10-minute target is approximate; actual:", duration, flush=True)


if __name__ == "__main__":
    build()
