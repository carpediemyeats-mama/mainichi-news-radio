#!/usr/bin/env python3
"""Generate one real MP3 from VOICEVOX voice and original procedural music.
No placeholder/test audio is ever published by this program.
"""
import json
import math
import random
import re
import subprocess
import tempfile
import time
from pathlib import Path
import requests
from pydub import AudioSegment
from pydub.generators import Sine

ROOT=Path(__file__).resolve().parent
SITE=ROOT/"site"
SITE.mkdir(exist_ok=True)
API="http://127.0.0.1:50021"
VOICE_ID=30
RATE=1.03

def tone(midi, millis, gain=-22):
    hz=440.0 * 2.0**((midi-69)/12.0)
    part=Sine(hz).to_audio_segment(duration=millis).apply_gain(gain)
    return part.fade_in(min(16,millis//4)).fade_out(min(140,millis//2))

def theme(bars=4, background=False):
    """Entirely original simple chord motif; generated during Actions, no stock audio."""
    step=520 if not background else 610
    total=bars*4*step+460
    base=AudioSegment.silent(duration=total,frame_rate=44100)
    chords=[(50,[62,65,69,72]),(43,[59,62,65,69]),(48,[60,64,67,71]),(45,[57,60,64,69])]
    for b in range(bars):
        root,notes=chords[b%4]
        for k in range(4):
            t=(b*4+k)*step
            base=base.overlay(tone(root-12,int(step*.8),-31 if background else -23),position=t)
            if k%2==0:
                for note in notes:
                    base=base.overlay(tone(note,int(step*1.25),-41 if background else -36),position=t)
            if not background:
                lead=notes[(b+k)%4]+12
                base=base.overlay(tone(lead,round(step*.62),-25),position=t+45)
    return base.fade_in(250).fade_out(450).set_frame_rate(44100).set_channels(2)

def sentence_chunks(text,maximum=115):
    parts=re.findall(r"[^。！？!?]+[。！？!?]?",text)
    result=[]
    for part in parts:
        part=part.strip()
        while len(part)>maximum:
            cut=max(part.rfind("、",0,maximum),part.rfind("，",0,maximum))
            if cut<45:cut=maximum
            else:cut+=1
            result.append(part[:cut]);part=part[cut:]
        if part:result.append(part)
    return result

def synth(text, temp_path):
    for attempt in range(3):
        try:
            query=requests.post(API+"/audio_query",params={"text":text,"speaker":VOICE_ID},timeout=90)
            query.raise_for_status()
            data=query.json()
            data["speedScale"]=RATE
            data["volumeScale"]=1.0
            response=requests.post(API+"/synthesis",params={"speaker":VOICE_ID},json=data,timeout=240)
            response.raise_for_status()
            if not response.content.startswith(b"RIFF") or len(response.content)<3000:
                raise RuntimeError("VOICEVOX did not return nonempty WAV")
            temp_path.write_bytes(response.content)
            segment=AudioSegment.from_wav(temp_path).set_frame_rate(44100).set_channels(2)
            return segment
        except Exception as error:
            print(f"VOICEVOX attempt {attempt+1} failed: {error}",flush=True)
            if attempt==2:raise
            time.sleep(4*(attempt+1))

def verify_voice():
    response=requests.get(API+"/speakers",timeout=40)
    response.raise_for_status()
    voices=response.json()
    for voice in voices:
        if voice.get("name")=="No.7":
            for style in voice.get("styles",[]):
                if style.get("id")==VOICE_ID:
                    print("VOICEVOX selected:",voice["name"],style.get("name"),VOICE_ID,flush=True)
                    return
    raise RuntimeError("No.7 announcement voice (style 30) not available in engine")

def build():
    episode=json.loads((ROOT/"episode.json").read_text(encoding="utf-8"))
    chapters=episode["chapters"]
    assert len(chapters)>=10,"Not enough chapters"
    verify_voice()
    opening=theme(4)
    ending=theme(3)
    jingle=theme(1)-8
    bed=theme(4,background=True)-6
    whole=opening+AudioSegment.silent(duration=350)
    index=[]
    with tempfile.TemporaryDirectory() as d:
        folder=Path(d)
        for n,chapter in enumerate(chapters):
            if n>0 and n<len(chapters)-1:
                whole+=jingle.fade_in(90).fade_out(220)+AudioSegment.silent(duration=190)
            index.append({"title":chapter["title"],"start_seconds":round(len(whole)/1000.0,1)})
            clips=[]
            for i,piece in enumerate(sentence_chunks(chapter["text"])):
                print(f"Synth {n+1}/{len(chapters)}, part {i+1}: {piece[:25]}",flush=True)
                clips.append(synth(piece,folder/f"{n}_{i}.wav"))
            if not clips:raise RuntimeError("Empty speech chapter")
            speech=AudioSegment.silent(duration=135,frame_rate=44100).set_channels(2)
            for i,clip in enumerate(clips):
                speech+=clip
                if i!=len(clips)-1:speech+=AudioSegment.silent(duration=175)
            # Music is deliberately low under speech.
            music=(bed*((len(speech)//len(bed))+1))[:len(speech)].apply_gain(-16)
            mixed=music.overlay(speech)
            whole+=mixed+AudioSegment.silent(duration=240)
            print(chapter["title"],round(len(speech)/1000,2),"s",flush=True)
    whole+=ending
    whole=whole.fade_in(60).fade_out(750)
    out=SITE/"episode.mp3"
    whole.export(out,format="mp3",bitrate="128k",tags={"title":episode["edition"]+" まいにちニュース","artist":"まいにちニュース","comment":"VOICEVOX:No.7"})
    check=AudioSegment.from_mp3(out)
    if out.stat().st_size<150000 or len(check)<120000:
        raise RuntimeError("Audio file missing or unexpectedly short")
    if abs(len(whole)-len(check))>450:raise RuntimeError("MP3 integrity/duration mismatch")
    seconds=round(len(check)/1000)
    result={"edition":episode["edition"],"title":episode["title"],
            "seconds":seconds,"duration_label":f"{seconds//60}分{seconds%60}秒","chapters":index}
    (SITE/"episode.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUCCESS:",out,out.stat().st_size,"bytes",seconds,"sec",flush=True)
    if seconds<840 or seconds>960:print("NOTE: episode does not yet match 14-16 min target.",flush=True)

if __name__=="__main__":
    build()
