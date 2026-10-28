#!/usr/bin/env python3
"""Make true five-minute versions, never speeding up voices or overwriting originals.
Independent of the two long episodes, news, science or proverb shows.
Uses the previously successful VOICEVOX/pydub audio engine.
"""
import datetime
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from pydub import AudioSegment
import build_kotoba_radio as master
import build_kotoba_ep02 as ep02

audio = master.audio
ROOT = Path(__file__).resolve().parent
SOURCE_DIR = ROOT / "kotoba"
OUTPUT = ROOT / "site" / "kotoba"
OUTPUT.mkdir(parents=True, exist_ok=True)
MAX_SECONDS = 300

def effect(name):
    if name == "bell13":
        return ep02.bell_thirteen()
    if name == "intro":
        return master.fairy_theme(2) + audio.silence(120)
    if name in ("ending","outro"):
        return master.fairy_theme(1) + audio.silence(80)
    if name == "quiz":
        return master.fairy_theme(1).apply_gain(-8)
    return master.effect(name)

def build(name, voices, bed):
    source = SOURCE_DIR / name
    if not name.endswith("_short.json") or not source.is_file():
        raise ValueError("Only dedicated 5-minute sources may be used: " + name)
    content=json.loads(source.read_text(encoding="utf-8"))
    scenes=content["scenes"]
    vocab=content["vocabulary"]
    episode_number=int(name.removesuffix("_short.json").removeprefix("episode"))
    expected_id=f"kotoba-episode-{episode_number:03d}-short"
    if content["id"] != expected_id or not 4<=len(vocab)<=6 or len(scenes)!=4:
        raise ValueError("Bad short episode identity, scenes or vocabulary: " + str(content["id"]))
    all_text="".join(line.get("text","") for scene in scenes for line in scene["lines"])
    for word in vocab:
        if all_text.count(word["term"])<2: raise RuntimeError("Insufficient word practice: "+word["term"])
    pauses=[line["quiz_pause_ms"] for scene in scenes for line in scene["lines"] if "quiz_pause_ms" in line]
    if len(pauses)<3 or not all(4000<=p<=7500 for p in pauses):
        raise RuntimeError("Not enough thinking time")
    # Listener/editor gate: roughly readable script, clear speakers, natural tempo, and quiz pauses.
    speakers={line["who"] for scene in scenes for line in scene["lines"] if "who" in line}
    if speakers!={"narrator","poko","luna","mina"}:
        raise RuntimeError("All four clearly differentiated voices required")
    if not 650<=len(all_text)<=1700:
        raise RuntimeError("Check script for ear-first pacing; too long or too short")

    result=audio.silence(70)
    chapters=[]
    count=0
    with tempfile.TemporaryDirectory() as folder:
        for i,scene in enumerate(scenes):
            if i:
                result+=master.fairy_theme(1).apply_gain(-10) + audio.silence(100)
            chapters.append({"title":scene["title"],"start_seconds":round(len(result)/1000,1)})
            for line in scene["lines"]:
                if "sfx" in line:
                    result+=effect(line["sfx"])+audio.silence(95)
                elif "quiz_pause_ms" in line:
                    millis=line["quiz_pause_ms"]
                    # Actual 5-second pause is rendered into the MP3, with quiet clock ticks.
                    wait=audio.silence(millis)
                    for sec in range(millis//1000):
                        wait=wait.overlay(audio.note(74,65,-42),position=sec*1000+65)
                    result+=wait
                else:
                    role=line["who"]
                    voice=audio.silence(40)
                    for piece in audio.word_chunks(line["text"],maximum=85):
                        count+=1
                        clip=audio.speak(piece,role,voices,Path(folder)/f"{name}_{count:04d}.wav")
                        voice+=clip+audio.silence(115)
                    result+=audio.with_background(voice,bed)
            print("CHAPTER",name,scene["title"],"at",round(len(result)/1000,1),"sec",flush=True)
    result=result.fade_in(90).fade_out(600)
    filename=name.removesuffix(".json")+".mp3"
    target=OUTPUT/filename
    result.export(target,format="mp3",bitrate="128k",tags={
        "title":content["edition"]+" "+content["title"],
        "album":"ことば幻獣ラジオ・5分版",
        "artist":"ことば幻獣ラジオ / VOICEVOX",
        "comment":"Fresh short edition, four voices, original music, audible thinking pauses"
    })
    decoded=AudioSegment.from_mp3(target)
    duration=len(decoded)/1000
    if not 120<=duration<=MAX_SECONDS:
        raise RuntimeError(f"STRICT 5 MINUTE CAP FAILED: {name}: {duration:.3f}s; rewrite the script, do not speed up voices")
    if abs(len(decoded)-len(result))>400:
        raise RuntimeError("MP3 sound duration mismatch")
    if target.stat().st_size<200000:
        raise RuntimeError("MP3 too small or invalid")
    edition=content["edition"]
    meta={
        "episode_id":content["id"],
        "original_episode_id":content["source_episode"],
        "edition":edition,"series":content["series"],"title":content["title"],
        "filename":filename,
        "seconds":round(duration),"duration_label":f"{int(duration)//60}分{round(duration)%60:02d}秒",
        "duration_exact_seconds":round(duration,3),
        "maximum_seconds":300,
        "build_id":datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "chapters":chapters,"vocabulary":vocab,
        "thinking_pauses_ms":pauses,"spoken_chunks":count
    }
    (OUTPUT/name).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print("VERIFIED SHORT EDITION",filename,round(duration,3),"seconds",target.stat().st_size,"bytes",flush=True)
    return meta

def main():
    requested=sys.argv[1:] or ["episode01_short.json","episode02_short.json"]
    voices=audio.get_speakers()
    bed=audio.music(4,background=True)
    for name in requested:
        build(name,voices,bed)

if __name__=="__main__":
    main()
