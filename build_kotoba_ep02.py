#!/usr/bin/env python3
"""Standalone second episode of vocabulary fantasy radio.
Reuse episode-one proven multi-voice VOICEVOX + pydub/audio engines.
Never touch episode-one files, news audio, or proverb episodes.
"""
import datetime
import hashlib
import json
import tempfile
from pathlib import Path
from pydub import AudioSegment
import build_kotoba_radio as master

audio = master.audio
ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "kotoba" / "episode02.json"
OUTPUT = ROOT / "site" / "kotoba"
OUTPUT.mkdir(parents=True, exist_ok=True)

def bell_thirteen():
    """Twelve deep bell strikes then precisely one higher small bell.
    This audio clue is central to the radio-only mystery."""
    segment = audio.silence(100)
    for i in range(12):
        strike = audio.note(48, 360, -24).overlay(audio.note(60, 300, -34))
        segment += strike + audio.silence(170)
    segment += audio.silence(340)
    segment += audio.note(87, 360, -20) + audio.silence(260)
    return segment

def intro_theme(bars):
    return master.fairy_theme(bars)

def effects(name):
    if name=="bell13":
        return bell_thirteen()
    if name=="intro":
        return intro_theme(4)+audio.silence(200)
    if name in ("outro","ending"):
        return intro_theme(2)+audio.silence(160)
    if name=="quiz":
        return intro_theme(1)-8
    return master.effect(name)

def build():
    episode=json.loads(SOURCE.read_text(encoding="utf-8"))
    words=episode["vocabulary"]
    scenes=episode["scenes"]
    if episode["id"]!="kotoba-episode-002" or episode["edition"]!="第2回":
        raise ValueError("Invalid second episode")
    if len(words)!=10 or len(scenes)!=6:
        raise ValueError("Expected ten words and six chapters")
    text=" ".join(x.get("text","") for scene in scenes for x in scene["lines"])
    for w in words:
        if text.count(w["term"])<2:
            raise ValueError("Vocabulary under-practiced: "+w["term"])
    if len({w["id"] for w in words})!=len(words):
        raise ValueError("Duplicated IDs")
    quiz_positions=[line["quiz_pause_ms"] for scene in scenes for line in scene["lines"] if "quiz_pause_ms" in line]
    if len(quiz_positions)<8 or not all(4000<=n<=8000 for n in quiz_positions):
        raise ValueError("Insufficient genuine thinking pauses")
    if not any("bell13"==line.get("sfx") for scene in scenes for line in scene["lines"]):
        raise ValueError("The radio-only auditory clue is missing")
    voices=audio.get_speakers()
    bed=audio.music(4,background=True)
    track=audio.silence(75)
    chapters=[]
    segments=0
    with tempfile.TemporaryDirectory() as directory:
        for idx,scene in enumerate(scenes):
            if idx:
                track+=intro_theme(1).apply_gain(-9)+audio.silence(190)
            chapters.append({"title":scene["title"],"start_seconds":round(len(track)/1000,1)})
            for line in scene["lines"]:
                if "sfx" in line:
                    track+=effects(line["sfx"])+audio.silence(180)
                elif "quiz_pause_ms" in line:
                    ms=line["quiz_pause_ms"]
                    blank=audio.silence(ms)
                    for beat in range(ms//1000):
                        blank=blank.overlay(audio.note(78,70,-39),position=beat*1000+50)
                    track+=blank
                else:
                    role=line["who"]
                    if role not in voices:raise ValueError("Missing speaker "+role)
                    combined=audio.silence(75)
                    for piece in audio.word_chunks(line["text"],maximum=85):
                        segments+=1
                        speech=audio.speak(piece,role,voices,Path(directory)/f"{segments:04d}.wav")
                        combined+=speech+audio.silence(155)
                    track+=audio.with_background(combined,bed)
            print("CHAPTER",scene["title"],"total seconds",round(len(track)/1000,1),flush=True)
    track=track.fade_in(120).fade_out(850)
    mp3=OUTPUT/"episode02.mp3"
    track.export(mp3,format="mp3",bitrate="128k",tags={
        "title":episode["edition"]+" "+episode["title"],
        "album":episode["series"],
        "artist":"ことば幻獣ラジオ / VOICEVOX",
        "comment":"Four distinct VOICEVOX voices, original score and sound effects; 12 bells plus small bell clue"
    })
    decoded=AudioSegment.from_mp3(mp3)
    seconds=round(len(decoded)/1000)
    if mp3.stat().st_size<300000 or not 600<=seconds<=1020:
        raise RuntimeError("Unexpected MP3 size or runtime "+str(seconds))
    if abs(len(decoded)-len(track))>450:
        raise RuntimeError("MP3 duration mismatch")
    meta={
        "episode_id":episode["id"],"series":episode["series"],"edition":episode["edition"],
        "title":episode["title"],"summary":episode["summary"],
        "filename":"episode02.mp3","seconds":seconds,
        "duration_label":f"{seconds//60}分{seconds%60}秒",
        "build_id":datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
        "chapters":chapters,"vocabulary":words,
        "spoken_chunks":segments,"thinking_pauses_ms":quiz_positions,
        "auditory_clue":"deep bell 12 strokes, high bell 1 stroke"
    }
    (OUTPUT/"episode02.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUCCESS episode02.mp3",mp3.stat().st_size,"bytes",seconds,"seconds",meta["sha256"],flush=True)
    if seconds>900:
        print("NOTE: episode is longer than 15-minute ideal and should be reviewed",flush=True)

if __name__=="__main__":
    build()
