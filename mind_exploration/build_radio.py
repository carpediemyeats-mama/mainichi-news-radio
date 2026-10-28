#!/usr/bin/env python3
"""Create a genuine three-minute Japanese mindfulness micro-radio.
Adapted from this repository's successful VOICEVOX, requests, pydub/ffmpeg pipeline.
No existing show is modified; source, MP3 and metadata use unique paths.
"""
import hashlib
import json
import tempfile
import time
from pathlib import Path

import requests
from pydub import AudioSegment
from pydub.generators import Sine

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/"mind_exploration"/"episode01.json"
OUT=ROOT/"site"/"mind_exploration"
OUT.mkdir(parents=True,exist_ok=True)
API="http://127.0.0.1:50021"


def silence(ms):
    return AudioSegment.silent(duration=int(ms),frame_rate=44100).set_channels(2)


def resolve_speaker(name,style):
    response=requests.get(API+"/speakers",timeout=60)
    response.raise_for_status()
    for speaker in response.json():
        if speaker.get("name")==name:
            for candidate in speaker.get("styles",[]):
                if candidate.get("name")==style:
                    print("CONFIRMED_SPEAKER",name,style,candidate["id"],flush=True)
                    return candidate["id"]
    raise RuntimeError("The requested speaker/style is unavailable: "+name+"/"+style)


def speak(text,speaker,rate,path):
    if not 2<=len(text)<=120:
        raise ValueError("Abnormally short or long narration: "+text)
    for attempt in range(3):
        try:
            r=requests.post(API+"/audio_query",params={"text":text,"speaker":speaker},timeout=90)
            r.raise_for_status()
            query=r.json()
            query["speedScale"]=rate
            query["intonationScale"]=0.92
            query["volumeScale"]=0.98
            query["prePhonemeLength"]=0.10
            query["postPhonemeLength"]=0.12
            r=requests.post(API+"/synthesis",params={"speaker":speaker},json=query,timeout=240)
            r.raise_for_status()
            if not r.content.startswith(b"RIFF") or len(r.content)<3000:
                raise RuntimeError("VOICEVOX returned invalid WAV")
            path.write_bytes(r.content)
            return AudioSegment.from_wav(path).set_frame_rate(44100).set_channels(2)
        except Exception as error:
            print("TTS retry",attempt+1,error,flush=True)
            if attempt==2:raise
            time.sleep(4*(attempt+1))


def distribute_silence(clips,lines,target_ms):
    """Fit the specified section time by changing natural silent gaps, never speeding speech."""
    spoken_ms=sum(len(c) for c in clips)
    free_ms=target_ms-spoken_ms
    min_each=240
    if free_ms < min_each*len(lines):
        raise RuntimeError(f"Spoken segment exceeds time budget: spoken={spoken_ms}, target={target_ms}. Edit script.")
    weights=[float(line["pause_ms"]) for line in lines]
    leftover=free_ms-min_each*len(lines)
    distributed=[min_each+int(leftover*w/sum(weights)) for w in weights]
    distributed[-1]+=free_ms-sum(distributed)
    if max(distributed)>8500:
        raise RuntimeError("An unnatural silence is required; revise script instead")
    result=silence(0)
    for audio,pause in zip(clips,distributed):
        result+=audio+silence(pause)
    difference=target_ms-len(result)
    if difference>0:result+=silence(difference)
    if difference<0:result=result[:target_ms]
    return result,distributed


def soft_original_opening(duration=1700):
    """Barely audible, gentle original chord; no music under guided noticing."""
    low=Sine(220).to_audio_segment(duration=duration).apply_gain(-40)
    high=Sine(329.63).to_audio_segment(duration=duration).apply_gain(-44)
    return low.overlay(high).fade_in(700).fade_out(750).set_frame_rate(44100).set_channels(2)


def build():
    e=json.loads(SOURCE.read_text(encoding="utf-8"))
    if e["id"]!="mind-exploration-episode-001" or len(e["sections"])!=3:
        raise RuntimeError("Wrong episode ID or structure")
    assert [s["target_seconds"] for s in e["sections"]]==[40,110,30]
    speaker=resolve_speaker(e["voice"]["speaker"],e["voice"]["style"])
    rate=float(e["voice"]["speed"])
    if not .86<=rate<=1.02:
        raise RuntimeError("Voice speed outside gentle range")
    full=silence(0)
    index=[]
    with tempfile.TemporaryDirectory() as d:
        k=0
        for sec in e["sections"]:
            index.append({"title":sec["title"],"start_seconds":round(len(full)/1000,3)})
            clips=[]
            for line in sec["lines"]:
                k+=1
                clips.append(speak(line["text"],speaker,rate,Path(d)/f"narration_{k:03d}.wav"))
            output,pauses=distribute_silence(clips,sec["lines"],sec["target_seconds"]*1000)
            print("SECTION",sec["id"],"spoken",sum(map(len,clips))/1000,"s","pauses",pauses,flush=True)
            full+=output
    if not 179900<=len(full)<=180100:
        raise RuntimeError("Not a 180-second episode")
    music=soft_original_opening()
    full=full.overlay(music,position=0).fade_in(100).fade_out(520)
    mp3=OUT/"episode01.mp3"
    full.export(mp3,format="mp3",bitrate="128k",tags={
       "title":"心の探検ラジオ 第1回 頭の中のおしゃべり",
       "album":"心の探検ラジオ",
       "artist":"VOICEVOX:青山龍星",
       "comment":"Original script; optional short mindfulness activity, not a clinical treatment."
    })
    decoded=AudioSegment.from_mp3(mp3)
    seconds=len(decoded)/1000
    if not 178.5<=seconds<=181.5 or abs(len(full)-len(decoded))>600:
        raise RuntimeError(f"MP3 timing failed: {seconds}")
    if mp3.stat().st_size < 250000:
        raise RuntimeError("MP3 too small; verify audio")
    result={
       "episode_id":e["id"],
       "series":e["series"],
       "title":e["title"],
       "filename":"episode01.mp3",
       "duration_seconds":round(seconds,3),
       "duration_label":"約3分",
       "sha256":hashlib.sha256(mp3.read_bytes()).hexdigest(),
       "chapters":index,
       "voice_attribution":"VOICEVOX:青山龍星（ノーマル）",
       "notice":e["disclaimer"]
    }
    (OUT/"episode01.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf8")
    print("MIND_EXPLORATION_3MIN_VERIFIED",seconds,mp3.stat().st_size,result["sha256"],flush=True)


if __name__=="__main__":
    build()
