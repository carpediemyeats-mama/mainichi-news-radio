#!/usr/bin/env python3
"""Five-minute proverb-focused audio programme.

Uses the verified VOICEVOX voices, audio processing, and original BGM from
build_kotowaza_radio.py; does not touch any existing episodes.
"""
import datetime
import hashlib
import json
import tempfile
from pathlib import Path

from pydub import AudioSegment
import build_kotowaza_radio as audio

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "kotowaza" / "episode01_v3.json"
OUTDIR = ROOT / "site" / "kotowaza"
MP3 = OUTDIR / "episode01_v3.mp3"
META = OUTDIR / "episode01_v3.json"

def build():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    vocab, scenes = source["vocabulary"], source["scenes"]
    if source["id"] != "kotowaza-episode-001-v3":
        raise RuntimeError("Wrong episode ID")
    if len(vocab) != 6 or not 4 <= len(scenes) <= 6:
        raise RuntimeError("Incorrect lesson or chapter count")
    all_text = " ".join(x.get("text", "") for s in scenes for x in s["lines"])
    for entry in vocab:
        if all_text.count(entry["term"]) < 2:
            raise RuntimeError("Term not sufficiently featured: " + entry["term"])
    roles = audio.get_speakers()
    background = audio.music(4, background=True)
    whole = audio.silence(80)
    chapter_times = []
    question_pauses = 0
    word_count = 0

    with tempfile.TemporaryDirectory() as dirname:
        temp = Path(dirname)
        for chapter_no, scene in enumerate(scenes):
            if chapter_no:
                whole += audio.sfx("ding").apply_gain(-10) + audio.silence(100)
            chapter_times.append({
                "title": scene["title"],
                "start_seconds": round(len(whole) / 1000, 1)
            })
            for line in scene["lines"]:
                if "sfx" in line:
                    whole += audio.sfx(line["sfx"]) + audio.silence(100)
                elif "quiz_pause_ms" in line:
                    milliseconds = line["quiz_pause_ms"]
                    if not 3500 <= milliseconds <= 7000:
                        raise RuntimeError("Expected an actual listener thinking pause")
                    question_pauses += 1
                    thinking = audio.silence(milliseconds)
                    for tick in range(milliseconds // 1000):
                        thinking = thinking.overlay(
                            audio.note(74, 80, -38), position=tick * 1000 + 60)
                    whole += thinking
                else:
                    role = line["who"]
                    if role not in roles:
                        raise RuntimeError("Unrecognised voice: " + role)
                    speech = audio.silence(50)
                    for chunk in audio.word_chunks(line["text"], maximum=90):
                        word_count += 1
                        audio_part = audio.speak(
                            chunk, role, roles, temp / f"{word_count:04d}.wav")
                        speech += audio_part + audio.silence(110)
                    whole += audio.with_background(speech, background)
            print("CHAPTER", scene["title"], len(whole) / 1000, flush=True)

    if question_pauses != 5:
        raise RuntimeError("Expected two mid-show quizzes and three final quizzes")
    OUTDIR.mkdir(parents=True, exist_ok=True)
    whole = whole.fade_in(110).fade_out(750)
    whole.export(MP3, format="mp3", bitrate="128k", tags={
        "title": "第1回 ゲームセンターのことばチャレンジ！ 5分版",
        "album": "ことわざ事件簿！",
        "artist": "ことわざ事件簿！ / VOICEVOX",
        "comment": "Original short script, original procedural music and effects."
    })
    decoded = AudioSegment.from_mp3(MP3)
    seconds = round(len(decoded) / 1000)
    if not 240 <= seconds <= 360:
        raise RuntimeError(f"Expected approximately five minutes, got {seconds}s")
    if MP3.stat().st_size < 350_000 or abs(len(decoded) - len(whole)) > 450:
        raise RuntimeError("Invalid or truncated MP3")
    result = {
        "episode_id": source["id"],
        "series": source["series"],
        "edition": source["edition"],
        "title": source["title"],
        "filename": MP3.name,
        "seconds": seconds,
        "duration_label": f"{seconds // 60}分{seconds % 60}秒",
        "sha256": hashlib.sha256(MP3.read_bytes()).hexdigest(),
        "build_id": datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "chapters": chapter_times,
        "vocabulary": vocab,
        "answer_pauses": question_pauses
    }
    META.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("SUCCESS", MP3, MP3.stat().st_size, "bytes", seconds,
          "seconds", "thinking pauses:", question_pauses, flush=True)

if __name__ == "__main__":
    build()
