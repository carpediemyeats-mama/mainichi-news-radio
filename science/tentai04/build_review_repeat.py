#!/usr/bin/env python3
"""Separate repeat-along edition of the existing enjoyable astronomy review radio.
Reuses working VOICEVOX, pydub, and original music code; does not overwrite older files.
"""
import datetime
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from pydub import AudioSegment

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import build_radio as original

audio=original.audio
SOURCE=HERE/"review_listen.json"
CUES=HERE/"repeat_cues.json"
OUT=ROOT/"site"/"science"/"tentai04"
OUT.mkdir(parents=True,exist_ok=True)

def merge_scenes():
    original_data=json.loads(SOURCE.read_text(encoding="utf-8"))
    cue_data=json.loads(CUES.read_text(encoding="utf-8"))
    if original_data["id"]!="tentai04-review-listen-001" or cue_data["id"]!="tentai04-review-repeat-001":
        raise RuntimeError("Wrong source/edition identity")
    scenes=original_data["chapters"]
    if len(scenes)!=4 or len(cue_data["cues"])!=7:
        raise RuntimeError("Expected 4 chapters and 7 gentle repetitions")
    by_chapter={i:[] for i in range(4)}
    for cue in cue_data["cues"]:
        k=cue["chapter"]
        if k not in by_chapter or not 3800<=cue["pause_ms"]<=7500:
            raise RuntimeError("Invalid repetition position")
        by_chapter[k].append(cue)
    compiled=[]
    for chapter_i,chapter in enumerate(scenes):
        lines=[]
        used=set()
        for role,words in chapter["lines"]:
            if role not in ("host","side","expert"):
                raise RuntimeError("Invalid speaker")
            lines.append((role,words))
            for n,cue in enumerate(by_chapter[chapter_i]):
                if cue["after"] in words:
                    if n in used:
                        raise RuntimeError("Repeated injection anchor")
                    used.add(n)
                    lines.extend([("host",cue["say"]),("repeat",cue["pause_ms"]),("side",cue["reply"])])
        if len(used)!=len(by_chapter[chapter_i]):
            raise RuntimeError("Missing repeat-along insertion: "+str(chapter_i))
        compiled.append({"title":chapter["title"],"lines":lines})
    return original_data,compiled

def main():
    source,chapters=merge_scenes()
    spoken=" ".join(phrase for chapter in chapters for role,phrase in chapter["lines"] if role!="repeat")
    anchors=("ベガ","デネブ","アルタイル","ベテルギウス","シリウス","プロキオン","リゲル","アンタレス","等級","自転","公転","星座早見")
    if any(spoken.count(word)<2 for word in anchors):
        raise RuntimeError("High-yield terms insufficiently repeated")
    cast=audio.get_speakers()
    bed=audio.music(4,background=True)
    whole=original.star_theme(2)+audio.silence(180)
    indexes=[]
    spoken_parts=0
    pauses=[]
    with tempfile.TemporaryDirectory() as folder:
        for ch_no,ch in enumerate(chapters):
            if ch_no:
                whole+=original.star_theme(1).apply_gain(-11)+audio.silence(150)
            indexes.append({"title":ch["title"],"start_seconds":round(len(whole)/1000,2)})
            for role,item in ch["lines"]:
                if role=="repeat":
                    # A quiet time to say the exact phrase aloud. No persistent countdown.
                    space=audio.silence(item)
                    space=space.overlay(audio.note(83,120,-34),position=110)
                    space=space.overlay(audio.note(79,110,-39),position=item-260)
                    whole+=space
                    pauses.append(item)
                    continue
                for part in audio.word_chunks(item,maximum=95):
                    spoken_parts+=1
                    clip=audio.speak(part,role,cast,Path(folder)/f"repeat_{spoken_parts:04d}.wav")
                    whole+=audio.with_background(audio.silence(85)+clip+audio.silence(170),bed)
            print("CHAPTER",ch_no+1,ch["title"],round(len(whole)/1000,1),flush=True)
    if len(pauses)!=7:
        raise RuntimeError("Incomplete repeat-along intervals")
    whole+=original.star_theme(1)
    whole=whole.fade_in(110).fade_out(800)
    target=OUT/"review_repeat.mp3"
    whole.export(target,format="mp3",bitrate="128k",tags={
        "title":"星空探偵ラジオ ②復習・聞き流し＆復唱",
        "album":source["series"],
        "artist":"星空探偵ラジオ / VOICEVOX",
        "comment":"Seven genuine repeat-along pauses, original conversational script and music",
    })
    check=AudioSegment.from_mp3(target)
    seconds=len(check)/1000
    if not 240<seconds<850 or target.stat().st_size<400000 or abs(len(check)-len(whole))>450:
        raise RuntimeError(f"MP3 integrity failure: {seconds}s, {target.stat().st_size} bytes")
    metadata={
        "episode_id":"tentai04-review-repeat-001",
        "edition":"第4回 天体の観測",
        "series":source["series"],
        "title":"復習・聞き流し＆いっしょに復唱編",
        "subtitle":"夜空の思い出アルバム・覚えどころだけ声に出そう",
        "filename":target.name,
        "seconds":round(seconds),
        "duration_label":f"{int(seconds)//60}分{int(seconds)%60:02d}秒",
        "sha256":hashlib.sha256(target.read_bytes()).hexdigest(),
        "source_sha256":hashlib.sha256(SOURCE.read_bytes()+CUES.read_bytes()).hexdigest(),
        "build_id":datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "chapters":indexes,
        "repeat_count":len(pauses),
        "repeat_pauses_ms":pauses,
        "mode":"relaxed_listening_with_repeat",
        "original_file_kept":"review_listen.mp3",
    }
    (OUT/"review_repeat.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUCCESS REPEAT-ALONG MP3",target,target.stat().st_size,"bytes",round(seconds),"seconds",flush=True)

if __name__=="__main__":
    main()
