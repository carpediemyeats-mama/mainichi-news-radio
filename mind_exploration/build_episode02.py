#!/usr/bin/env python3
"""Episode 2: optional present-moment grounding, not trauma exposure or treatment.
Reuses verified VOICEVOX/pydub code from episode 1; distinct source and MP3 assets.
"""
import hashlib
import json
import tempfile
from pathlib import Path
from pydub import AudioSegment

from build_radio import silence,resolve_speaker,speak,distribute_silence,soft_original_opening

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"mind_exploration"/"episode02_time_machine.json"
OUT=ROOT/"site"/"mind_exploration"
OUTPUT_NAME="mind-exploration-ep002-time-machine.mp3"
META_NAME="mind-exploration-ep002-time-machine.json"
EPISODE_ID="mind-exploration-episode-002"

def build():
    e=json.loads(SCRIPT.read_text(encoding="utf-8"))
    if e["id"]!=EPISODE_ID or e["episode_number"]!=2 or e["title"]!="脳の中のタイムマシン":
        raise ValueError("Wrong episode! Refuse to mix up radio programs.")
    sections=e["sections"]
    if [s["target_seconds"] for s in sections]!=[40,110,30]:
        raise ValueError("Incorrect timing map")
    all_lines=[line for section in sections for line in section["lines"]]
    if not 20<=len(all_lines)<=35 or any(len(line["text"])>110 for line in all_lines):
        raise ValueError("Unexpected narration line size")
    script_text="".join(line["text"] for line in all_lines)
    if not all(term in script_text for term in ["タイムマシン","色","音","今"]):
        raise ValueError("Incorrect episode content")
    if any(forbidden in script_text for forbidden in ["ことわざ","反省しよう","怒りをコントロール","深呼吸しなさい"]):
        raise ValueError("Unexpected or coercive episode text")
    voice=e["voice"]
    speaker=resolve_speaker(voice["speaker"],voice["style"])
    rate=float(voice["speed"])
    if not .87<=rate<=1.0:
        raise ValueError("Voice speed changed unexpectedly")
    assembled=silence(0)
    chapter_index=[]
    chapter_speech=[]
    with tempfile.TemporaryDirectory() as tmp:
        index=0
        for section in sections:
            chapter_index.append({"title":section["title"],"start_seconds":round(len(assembled)/1000.0,3)})
            clips=[]
            for line in section["lines"]:
                index+=1
                clips.append(speak(line["text"],speaker,rate,Path(tmp)/f"{index:03d}.wav"))
            chapter_speech.append(round(sum(len(clip) for clip in clips)/1000,3))
            chapter,distributed_pauses=distribute_silence(clips,section["lines"],section["target_seconds"]*1000)
            print("EP002_CHAPTER",section["id"],"voice_seconds",chapter_speech[-1],
                  "pause_ms",distributed_pauses,flush=True)
            assembled+=chapter
    if not 179900<=len(assembled)<=180100:
        raise ValueError("Must be almost exactly 180 seconds")
    assembled=assembled.overlay(soft_original_opening(),position=0).fade_in(80).fade_out(520)
    OUT.mkdir(exist_ok=True,parents=True)
    mp3=OUT/OUTPUT_NAME
    assembled.export(mp3,format="mp3",bitrate="128k",tags={
        "title":"心の探検ラジオ 第2回 脳の中のタイムマシン",
        "album":"心の探検ラジオ",
        "artist":"VOICEVOX:青山龍星",
        "comment":"mind-exploration-episode-002: optional present-moment grounding, no forced recollection"
    })
    decoded=AudioSegment.from_mp3(mp3)
    seconds=len(decoded)/1000.0
    if not 178.5<=seconds<=181.5 or abs(len(decoded)-len(assembled))>550:
        raise ValueError(f"Invalid MP3 length: {seconds}")
    if mp3.stat().st_size<260000:
        raise ValueError("Audio unexpectedly small")
    # Guard against accidentally using the prior episode or the proverb series.
    first=OUT/"mind-exploration-ep001-3min.mp3"
    if first.exists() and hashlib.sha256(first.read_bytes()).digest()==hashlib.sha256(mp3.read_bytes()).digest():
        raise RuntimeError("Episode 2 is identical to episode 1")
    meta={
      "episode_id":EPISODE_ID,"episode_number":2,"series":e["series"],"title":e["title"],
      "filename":OUTPUT_NAME,"duration_seconds":round(seconds,3),"duration_label":"3分00秒",
      "sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
      "chapters":chapter_index,"voice_attribution":"VOICEVOX:青山龍星（ノーマル）",
      "script_sha256":hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
      "spoken_lines":len(all_lines),"section_spoken_seconds":chapter_speech,
      "notice":e["notice"]
    }
    (OUT/META_NAME).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("EP002_VERIFIED",OUTPUT_NAME,round(seconds,3),mp3.stat().st_size,meta["sha256"],flush=True)

if __name__=="__main__":
    build()
