#!/usr/bin/env python3
"""Episode 2 of 心に余白を。 Reuse the verified episode 1 VOICEVOX pipeline.

Do not replace episode01 or touch any other radio program.
"""
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

from pydub import AudioSegment
import build_radio as audio_lib

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"kokoro_yohaku"/"episode02.json"
OUT=ROOT/"site"/"kokoro_yohaku"
MP3="kokoro-yohaku-episode02.mp3"
METADATA="episode02.json"

def build():
    OUT.mkdir(parents=True,exist_ok=True)
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    if source["id"]!="kokoro-yohaku-episode-002":raise ValueError("Wrong episode ID")
    chapters=source["chapters"]
    if len(chapters)!=5:raise ValueError("Episode 2 expects five chapters")
    narrator=source["narrator"]
    voice=audio_lib.resolve_voice(narrator["name"],narrator["style"])
    whole=audio_lib.soft_chime()+audio_lib.silence(550)
    markers=[]
    with tempfile.TemporaryDirectory() as temp:
        for ci,chapter in enumerate(chapters):
            if ci:whole+=audio_lib.silence(600)
            markers.append({"title":chapter["title"],"start_seconds":round(len(whole)/1000,2)})
            lines=audio_lib.chunks(chapter["text"])
            if not lines:raise RuntimeError("Empty chapter")
            print("SYNTHESIZING_CHAPTER",ci+1,len(lines),flush=True)
            for li,line in enumerate(lines):
                whole+=audio_lib.synth(line,voice,float(narrator["speed"]),
                    Path(temp)/f"{ci:02d}_{li:03d}.wav")
                whole+=audio_lib.silence(190 if li<len(lines)-1 else 330)
    whole+=audio_lib.silence(350)+audio_lib.soft_chime()
    whole=whole.fade_in(60).fade_out(600)
    target=OUT/MP3
    whole.export(target,format="mp3",bitrate="128k",tags={
        "title":"心に余白を。第2回 正しいことを言っているのに伝わらない",
        "artist":"心に余白を。",
        "comment":"VOICEVOX No.7 ノーマル / Original gentle jingle"
    })
    dur=float(subprocess.check_output(["ffprobe","-v","error",
        "-show_entries","format=duration","-of","csv=p=0",str(target)],
        text=True).strip())
    if target.stat().st_size<500000 or not 420<=dur<=600:
        raise RuntimeError(f"Audio must be 7-10 min: {dur}s {target.stat().st_size} bytes")
    if abs(dur-len(whole)/1000)>0.6:raise RuntimeError("Export mismatch")
    info={
        "episode_id":source["id"],"program":source["program"],"episode":2,
        "title":source["title"],"date":source["date"],"filename":MP3,
        "duration_seconds":round(dur,2),"chapters":markers,
        "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "narrator":"VOICEVOX No.7 ノーマル",
        "disclaimer":source["disclaimer"],"sources":source["sources"]
    }
    (OUT/METADATA).write_text(json.dumps(info,ensure_ascii=False,indent=2)+"\n",
        encoding="utf-8")
    print("SUCCESS_EPISODE02",target,round(dur,2),
        target.stat().st_size,info["sha256"],flush=True)

if __name__=="__main__":
    build()
