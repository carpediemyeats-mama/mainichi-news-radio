#!/usr/bin/env python3
"""Independent, source-grounded pharmacist learning drama.
Reuses the tested VOICEVOX/musical synthesizer. Never changes news audio.
"""
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from pydub import AudioSegment

BASE=Path(__file__).resolve().parent
sys.path.insert(0,str(BASE))
import build_kotowaza_radio_v2 as radio

SOURCE=BASE/"kanri"/"episode01.json"
OUT=BASE/"site"/"kanri"
OUT.mkdir(parents=True,exist_ok=True)

# Resolved by actual VOICEVOX speaker name and style; no assumed numeric IDs.
radio.CAST={
    "narrator":("No.7","アナウンス",1.03),
    "manager":("四国めたん","ノーマル",1.05),
    "colleague":("青山龍星","ノーマル",1.08)
}

def build():
    episode=json.loads(SOURCE.read_text(encoding="utf-8"))
    if episode["id"]!="kanri-episode-001" or episode["master_version"]!="1.7":
        raise RuntimeError("Wrong episode or source master")
    chapters=episode["chapters"]
    if len(chapters)!=6:
        raise RuntimeError("Expected six compact, purposeful chapters")
    if sum("quiz_pause_ms" in line for ch in chapters for line in ch["lines"])<5:
        raise RuntimeError("Five interactive pauses required")
    voices=radio.get_speakers()
    bed=radio.music(4,background=True)
    whole=radio.music(3)+radio.silence(270)
    chapter_index=[]
    with tempfile.TemporaryDirectory() as folder:
        i=0
        for c,ch in enumerate(chapters):
            if c:
                whole+=radio.music(1).apply_gain(-8)+radio.silence(170)
            chapter_index.append({"title":ch["title"],"start_seconds":round(len(whole)/1000,1)})
            for line in ch["lines"]:
                if "sfx" in line:
                    whole+=radio.sfx(line["sfx"])+radio.silence(110)
                elif "quiz_pause_ms" in line:
                    pause=line["quiz_pause_ms"]
                    if not 2500<=pause<=10000:
                        raise ValueError("Invalid thinking pause")
                    gap=radio.silence(pause)
                    gap=gap.overlay(radio.note(76,120,-33),position=80)
                    whole+=gap
                else:
                    role=line["who"]
                    if role not in voices or not line["text"].strip():
                        raise ValueError("Invalid voice line")
                    dialogue=radio.silence(70)
                    for chunk in radio.word_chunks(line["text"],maximum=95):
                        i+=1
                        dialogue+=radio.speak(chunk,role,voices,Path(folder)/f"{i:04d}.wav")
                        dialogue+=radio.silence(145)
                    whole+=radio.with_background(dialogue,bed)
            print("CHAPTER",c+1,ch["title"],round(len(whole)/1000,1),flush=True)
    whole+=radio.music(2)
    whole=whole.fade_in(90).fade_out(850)
    mp3=OUT/"episode01.mp3"
    whole.export(mp3,format="mp3",bitrate="128k",tags={
        "title":episode["title"],
        "album":episode["series"],
        "artist":"VOICEVOX No.7 / 四国めたん / 青山龍星",
        "comment":"Original writing and procedural music; administrative source master v1.7"
    })
    decoded=AudioSegment.from_mp3(mp3)
    sec=round(len(decoded)/1000)
    if mp3.stat().st_size<200000 or not 240<=sec<=900 or abs(len(decoded)-len(whole))>600:
        raise RuntimeError(f"Audio validation failed: {sec}s, {mp3.stat().st_size} bytes")
    metadata={
        "episode_id":episode["id"],
        "title":episode["title"],
        "series":episode["series"],
        "master_version":episode["master_version"],
        "source_ids":episode["source_ids"],
        "seconds":sec,
        "duration_label":f"{sec//60}分{sec%60}秒",
        "filename":mp3.name,
        "sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
        "chapters":chapter_index,
        "voice_attribution":"VOICEVOX:No.7, 四国めたん, 青山龍星",
        "notice":episode["notice"]
    }
    (OUT/"episode01.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print("KANRI_SUCCESS",metadata["episode_id"],sec,mp3.stat().st_size,flush=True)

if __name__=="__main__":
    build()
