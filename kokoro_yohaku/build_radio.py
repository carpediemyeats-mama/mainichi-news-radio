#!/usr/bin/env python3
"""Independent 心に余白を radio. Reuses proven VOICEVOX/pydub/ffmpeg pattern.
No stock music, placeholder speech or modifications to other shows.
"""
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path
import requests
from pydub import AudioSegment
from pydub.generators import Sine

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"kokoro_yohaku"/"episode01.json"
OUT=ROOT/"site"/"kokoro_yohaku"
OUT.mkdir(parents=True,exist_ok=True)
API="http://127.0.0.1:50021"
MP3="kokoro-yohaku-episode01.mp3"

def silence(ms):
    return AudioSegment.silent(duration=int(ms),frame_rate=44100).set_channels(2)

def soft_chime():
    """Original, delicate chord: only before/after voice, no distracting bed."""
    span=2200
    a=Sine(261.63).to_audio_segment(duration=span).apply_gain(-35)
    b=Sine(329.63).to_audio_segment(duration=span).apply_gain(-39)
    c=Sine(392.0).to_audio_segment(duration=span).apply_gain(-41)
    return a.overlay(b).overlay(c).fade_in(380).fade_out(980).set_frame_rate(44100).set_channels(2)

def resolve_voice(name,style):
    response=requests.get(API+"/speakers",timeout=45)
    response.raise_for_status()
    for v in response.json():
        if v.get("name")==name:
            for s in v.get("styles",[]):
                if s.get("name")==style:
                    print("VOICEVOX VERIFIED",name,style,s["id"],flush=True)
                    return int(s["id"])
    raise RuntimeError("Voice unavailable: "+name+" / "+style)

def chunks(text,maximum=108):
    output=[]
    parts=re.findall(r"[^。！？!?]+[。！？!?]?",text.replace("\n",""))
    for item in parts:
        item=item.strip()
        while len(item)>maximum:
            i=max(item.rfind("、",0,maximum),item.rfind("，",0,maximum))
            if i<30:i=maximum
            else:i+=1
            output.append(item[:i])
            item=item[i:]
        if item:output.append(item)
    return output

def synth(text,speaker,rate,path):
    for attempt in range(3):
        try:
            q=requests.post(API+"/audio_query",params={"text":text,"speaker":speaker},timeout=90)
            q.raise_for_status()
            dat=q.json()
            dat["speedScale"]=rate
            dat["intonationScale"]=0.95
            dat["volumeScale"]=0.98
            dat["prePhonemeLength"]=0.08
            dat["postPhonemeLength"]=0.10
            resp=requests.post(API+"/synthesis",params={"speaker":speaker},json=dat,timeout=240)
            resp.raise_for_status()
            if not resp.content.startswith(b"RIFF") or len(resp.content)<3500:
                raise RuntimeError("Invalid voice output")
            path.write_bytes(resp.content)
            return AudioSegment.from_wav(path).set_frame_rate(44100).set_channels(2)
        except Exception as e:
            print("Retry",attempt+1,str(e),flush=True)
            if attempt==2:raise
            time.sleep(3*(attempt+1))

def main():
    episode=json.loads(SOURCE.read_text(encoding="utf-8"))
    chapters=episode["chapters"]
    if not 1<=len(chapters)<=15:raise ValueError("Invalid chapter count")
    narrator=episode["narrator"]
    speaker=resolve_voice(narrator["name"],narrator["style"])
    rate=float(narrator["speed"])
    whole=soft_chime()+silence(550)
    marks=[]
    with tempfile.TemporaryDirectory() as temp:
        for ci,ch in enumerate(chapters):
            if ci>0:whole+=silence(600)
            marks.append({"title":ch["title"],"start_seconds":round(len(whole)/1000,2)})
            lines=chunks(ch["text"])
            if not lines:raise ValueError("Empty chapter")
            print("Chapter",ci+1,"pieces",len(lines),flush=True)
            for li,line in enumerate(lines):
                audio=synth(line,speaker,rate,Path(temp)/f"{ci}_{li}.wav")
                whole+=audio
                whole+=silence(190 if li<len(lines)-1 else 330)
    whole+=silence(350)+soft_chime()
    whole=whole.fade_in(60).fade_out(600)
    path=OUT/MP3
    whole.export(path,format="mp3",bitrate="128k",
        tags={"title":"心に余白を。第1回 注意すると激怒するのはなぜ？",
              "artist":"心に余白を。","comment":"VOICEVOX:No.7 ノーマル / original music"})
    dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","default=noprint_wrappers=1:nokey=1",str(path)],text=True).strip())
    if path.stat().st_size<350000 or dur<360 or dur>720:
        raise RuntimeError(f"MP3 outside acceptable safety range: {dur}s {path.stat().st_size}b")
    if abs(dur-len(whole)/1000)>0.6:raise RuntimeError("MP3 duration mismatch")
    meta={
        "episode_id":episode["id"],"program":episode["program"],
        "episode":episode["episode"],"title":episode["title"],"date":episode["date"],
        "filename":MP3,"duration_seconds":round(dur,2),
        "chapters":marks,"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "narrator":"VOICEVOX No.7 ノーマル",
        "disclaimer":episode["disclaimer"],"sources":episode["sources"]
    }
    (OUT/"episode01.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("PUBLISHED_ASSET_READY",path,path.stat().st_size,"bytes",dur,"seconds",
          "sha256",meta["sha256"],flush=True)
    if not 420<=dur<=600:
        print("DURATION_WARNING: requested 7-10 min; review and adjust if necessary",flush=True)

if __name__=="__main__":
    main()
