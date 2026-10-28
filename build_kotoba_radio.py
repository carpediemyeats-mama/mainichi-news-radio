#!/usr/bin/env python3
"""Vocabulary radio with verified VOICEVOX MP3 and original music.
This is independent of the news and proverb outputs and reuses the
proven VOICEVOX/pydub functions already in build_kotowaza_radio.py.
"""
import datetime
import hashlib
import json
import tempfile
from pathlib import Path
from pydub import AudioSegment
import build_kotowaza_radio as audio

ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"kotoba"/"episode01.json"
OUTPUT=ROOT/"site"/"kotoba"
OUTPUT.mkdir(parents=True,exist_ok=True)
audio.CAST={
    "narrator":("No.7","アナウンス",1.08),
    "poko":("ずんだもん","ノーマル",1.03),
    "luna":("四国めたん","ノーマル",1.07),
    "mina":("春日部つむぎ","ノーマル",1.05),
}

def fairy_theme(bars=2):
    """Fresh fantasy-style four-measure bell melody (procedural and original)."""
    step=300
    total=bars*8*step+380
    out=audio.silence(total)
    chords=[(48,[60,64,67,72]),(45,[57,60,64,69]),
            (41,[57,60,65,69]),(43,[59,62,67,71])]
    for b in range(bars):
        root, chord=chords[b%4]
        for k in range(8):
            pos=(b*8+k)*step
            if k%2==0:
                out=out.overlay(audio.note(root,330,-32),position=pos)
            if k in (0,4):
                for tone in chord[1:4]:
                    out=out.overlay(audio.note(tone,520,-43),position=pos)
            if k in (0,1,3,4,6):
                pitch=chord[(b+k)%len(chord)]+12
                out=out.overlay(audio.note(pitch,210,-25),position=pos+20)
    return out.fade_in(120).fade_out(300)

def effect(name):
    if name=="intro":return fairy_theme(4)+audio.silence(200)
    if name in ("outro","ending"):return fairy_theme(2)+audio.silence(150)
    if name=="quiz":return fairy_theme(1)-7
    if name=="arcade":return fairy_theme(1)-3
    return audio.sfx(name)

def build():
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    terms=source["vocabulary"];scenes=source["scenes"]
    if source["id"]!="kotoba-episode-001" or len(terms)!=10 or len(scenes)<5:
        raise ValueError("Unexpected source identity or vocabulary count")
    text=" ".join(line.get("text","") for s in scenes for line in s["lines"])
    for word in terms:
        if text.count(word["term"])<2:
            raise ValueError("Missing contextual repetition: "+word["term"])
    voices=audio.get_speakers()
    bed=audio.music(4,background=True)
    whole=audio.silence(65)
    chapters=[]
    generated=0
    with tempfile.TemporaryDirectory() as folder:
        for idx,scene in enumerate(scenes):
            if idx:
                whole+=fairy_theme(1).apply_gain(-9)+audio.silence(170)
            chapters.append({"title":scene["title"],"start_seconds":round(len(whole)/1000,1)})
            for line in scene["lines"]:
                if "sfx" in line:
                    whole+=effect(line["sfx"])+audio.silence(155)
                elif "quiz_pause_ms" in line:
                    pause=line["quiz_pause_ms"]
                    if not 2500<=pause<=12000:raise ValueError("Invalid quiz pause")
                    space=audio.silence(pause)
                    for p in range(pause//1000):
                        space=space.overlay(audio.note(75,75,-36),position=p*1000+70)
                    whole+=space
                else:
                    who=line["who"]
                    if who not in voices:raise ValueError("Invalid voice: "+who)
                    combined=audio.silence(70)
                    for part in audio.word_chunks(line["text"],maximum=90):
                        generated+=1
                        clip=audio.speak(part,who,voices,Path(folder)/f"{generated:04d}.wav")
                        combined+=clip+audio.silence(125)
                    whole+=audio.with_background(combined,bed)
            print("CHAPTER",scene["title"],len(whole)//1000,flush=True)
    whole=whole.fade_in(100).fade_out(800)
    outfile=OUTPUT/"episode01.mp3"
    whole.export(outfile,format="mp3",bitrate="128k",
        tags={"album":source["series"],"title":source["edition"]+" "+source["title"],
              "artist":"ことば幻獣ラジオ / VOICEVOX",
              "comment":"Original story, music and sound effects"})
    decoded=AudioSegment.from_mp3(outfile)
    if outfile.stat().st_size<300000 or len(decoded)<360000:
        raise RuntimeError("MP3 missing or shorter than six minutes")
    if abs(len(whole)-len(decoded))>450:
        raise RuntimeError("MP3 failed duration integrity check")
    duration=round(len(decoded)/1000)
    build_id=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    metadata={"episode_id":source["id"],"series":source["series"],
        "edition":source["edition"],"title":source["title"],
        "seconds":duration,"duration_label":f"{duration//60}分{duration%60}秒",
        "filename":"episode01.mp3","build_id":build_id,
        "sha256":hashlib.sha256(outfile.read_bytes()).hexdigest(),
        "chapters":chapters,"vocabulary":terms}
    (OUTPUT/"episode01.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUCCESS",outfile,outfile.stat().st_size,duration,flush=True)
    if not 480<=duration<=780:
        print("NOTE: target is approximately 10-12 minutes; actual seconds",duration,flush=True)

if __name__=="__main__":build()
