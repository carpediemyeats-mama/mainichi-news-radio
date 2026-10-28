#!/usr/bin/env python3
"""Time-neutral revisions of the two existing Mind Exploration episodes.
Creates new uniquely identified MP3s, never overwrites the earlier originals.
Uses the already successful VOICEVOX + pydub synthesis helpers.
"""
import hashlib
import json
import tempfile
from pathlib import Path

from pydub import AudioSegment
from build_radio import silence,resolve_speaker,speak,distribute_silence,soft_original_opening

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/"site"/"mind_exploration"
OUTPUT.mkdir(parents=True,exist_ok=True)

EPISODES=(
    (1,"episode01_anytime.json","mind-exploration-episode-001-anytime","mind-exploration-ep001-anytime"),
    (2,"episode02_anytime.json","mind-exploration-episode-002-anytime","mind-exploration-ep002-anytime"),
)

def build(number,source_file,expected_id,stem,voices):
    source=ROOT/"mind_exploration"/source_file
    obj=json.loads(source.read_text(encoding="utf-8"))
    if obj["id"]!=expected_id or obj["episode_number"]!=number:
        raise RuntimeError("Source identity mismatch")
    sections=obj["sections"]
    if len(sections)!=3 or [s["target_seconds"] for s in sections]!=[40,110,30]:
        raise RuntimeError("Invalid three-minute structure")
    words=" ".join(s["title"]+" "+ " ".join(line["text"] for line in s["lines"]) for s in sections)
    if any(word in words for word in ("朝", "昼", "夜", "就寝", "寝る前", "起床", "ことわざ")):
        raise RuntimeError("Time-restricted or unrelated narration detected")
    if number==1 and "頭の中のおしゃべり" not in obj["title"]:
        raise RuntimeError("Wrong episode 1 script")
    if number==2 and "脳の中のタイムマシン" not in obj["title"]:
        raise RuntimeError("Wrong episode 2 script")

    voice=obj["voice"]
    speaker=voices[(voice["speaker"],voice["style"])]
    rate=float(voice.get("speed",0.96))
    if not .87<=rate<=1.0:
        raise RuntimeError("Bad VOICEVOX speed")
    whole=silence(0)
    chapters=[]
    with tempfile.TemporaryDirectory() as folder:
        utterance=0
        for s in sections:
            chapters.append({"title":s["title"],"start_seconds":round(len(whole)/1000,3)})
            clips=[]
            for line in s["lines"]:
                utterance+=1
                clips.append(speak(line["text"],speaker,rate,Path(folder)/f"ep{number}_{utterance:03d}.wav"))
            chapter,pauses=distribute_silence(clips,s["lines"],s["target_seconds"]*1000)
            print("EP",number,"CHAPTER",s["id"],"spoken_ms",sum(len(c) for c in clips),
                  "silence_ms",sum(pauses),flush=True)
            whole+=chapter
    if abs(len(whole)-180000)>120:raise RuntimeError("Episode duration wrong")
    whole=whole.overlay(soft_original_opening(),position=0).fade_in(80).fade_out(520)
    dest=OUTPUT/(stem+".mp3")
    whole.export(dest,format="mp3",bitrate="128k",tags={
        "title":f"心の探検ラジオ 第{number}回 {obj['title']}（いつでも聴ける版）",
        "album":"心の探検ラジオ",
        "artist":"VOICEVOX:青山龍星",
        "comment":expected_id+" time-neutral revision; no behavioral correction or forced recall"
    })
    decoded=AudioSegment.from_mp3(dest)
    duration=len(decoded)/1000.0
    if not 178.5<=duration<=181.5 or abs(len(decoded)-len(whole))>600:
        raise RuntimeError("Unexpected duration or audio corruption")
    if dest.stat().st_size<260000:raise RuntimeError("File too small")

    previous=(OUTPUT/("mind-exploration-ep001-3min.mp3" if number==1 else "mind-exploration-ep002-time-machine.mp3"))
    if previous.is_file() and hashlib.sha256(previous.read_bytes()).digest()==hashlib.sha256(dest.read_bytes()).digest():
        raise RuntimeError("Old recording reused: time-neutral revision was not synthesized")

    meta={
        "episode_id":expected_id,
        "episode_number":number,
        "title":obj["title"],
        "series":obj["series"],
        "revision":"時間帯に依存しない改訂版",
        "filename":dest.name,
        "duration_seconds":round(duration,3),
        "duration_label":"3分00秒",
        "sha256":hashlib.sha256(dest.read_bytes()).hexdigest(),
        "script_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
        "chapters":chapters,
        "voice_attribution":"VOICEVOX:青山龍星（ノーマル）",
        "notice":obj.get("notice",obj.get("disclaimer","")),
    }
    (OUTPUT/(stem+".json")).write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("VERIFIED_ANYTIME_RADIO",dest.name,round(duration,3),dest.stat().st_size,meta["sha256"],flush=True)

def main():
    ids=set()
    for _,filename,_,_ in EPISODES:
        obj=json.loads((ROOT/"mind_exploration"/filename).read_text(encoding="utf-8"))
        ids.add((obj["voice"]["speaker"],obj["voice"]["style"]))
    voices={key:resolve_speaker(*key) for key in ids}
    for args in EPISODES:build(*args,voices)

if __name__=="__main__":
    main()
