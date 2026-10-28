#!/usr/bin/env python3
"""Change ONLY the opening music of published pharmacist radio episode 1.

Source audio and metadata remain untouched. The new MP3 is independently tagged,
verified against a source SHA256, and published under a different release tag.
All narration, quizzes, mid-program cues and closing are preserved.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine

ROOT=Path(__file__).resolve().parent.parent
DIR=ROOT/"site"/"kanri"
ORIGINAL=DIR/"episode01.mp3"
ORIGINAL_META=DIR/"episode01.json"
OUTPUT=DIR/"episode01_softintro.mp3"
OUTPUT_META=DIR/"episode01_softintro.json"
SAMPLE_RATE=44100
OLD_CUT_MS=6740   # Exact original build: music(3) 3*8*260+230, then 270 ms silence.
# This quiet 4.3-second intro is intentionally unlike the fast, arcade-style intro.
INTRO_MS=4300
CROSSFADE_MS=160

def quiet_piano(freq:float, duration_ms:int, gain_db:float=-22.0)->AudioSegment:
    n=int(SAMPLE_RATE*duration_ms/1000)
    t=np.arange(n,dtype=np.float64)/SAMPLE_RATE
    # Rounded piano-like overtones, short hammer attack, natural decay, no rhythmic percussion.
    onset=1-np.exp(-45*t)
    body=(np.sin(2*np.pi*freq*t)
         +0.29*np.sin(2*np.pi*2*freq*t)
         +0.12*np.sin(2*np.pi*3*freq*t)
         +0.045*np.sin(2*np.pi*4*freq*t))
    envelope=onset*np.exp(-2.3*t)
    tail=np.minimum(1.0,(duration_ms/1000-t)/0.22)
    output=body*envelope*np.maximum(0,tail)
    output*=10**(gain_db/20)*25000
    pcm=np.clip(output,-32760,32760).astype("<i2").tobytes()
    return AudioSegment(data=pcm,sample_width=2,frame_rate=SAMPLE_RATE,channels=1).set_channels(2)

def create_intro()->AudioSegment:
    # Warm late-evening radio / documentary motif: airy C-major-9 harmony, no drums or bleeps.
    bed=AudioSegment.silent(duration=INTRO_MS,frame_rate=SAMPLE_RATE).set_channels(2)
    for hz,gain in [(130.81,-41),(164.81,-44),(196.00,-44)]:
        pad=Sine(hz).to_audio_segment(duration=INTRO_MS).set_frame_rate(SAMPLE_RATE).set_channels(2)
        bed=bed.overlay(pad.apply_gain(gain).fade_in(850).fade_out(1300))
    for at,hz,gain in [(330,329.63,-19),(1270,392.00,-21),(2250,493.88,-22)]:
        note=quiet_piano(hz,1650,gain_db=gain)
        # subtle tail acts as a room reflection, not an electronic arcade echo
        bed=bed.overlay(note,position=at)
        bed=bed.overlay(note.apply_gain(-17),position=min(at+150,INTRO_MS-100))
    return bed.fade_in(280).fade_out(900)

def build()->None:
    metadata=json.loads(ORIGINAL_META.read_text(encoding="utf-8"))
    if metadata["episode_id"]!="kanri-episode-001":
        raise RuntimeError("Wrong source episode")
    assert abs(metadata["chapters"][0]["start_seconds"]*1000-OLD_CUT_MS)<100
    original_sha=hashlib.sha256(ORIGINAL.read_bytes()).hexdigest()
    if original_sha!=metadata["sha256"]:
        raise RuntimeError("Source MP3 does not match original episode metadata")
    original=AudioSegment.from_mp3(ORIGINAL).set_frame_rate(SAMPLE_RATE).set_channels(2)
    original_first=original[:OLD_CUT_MS]
    if not 6000<=len(original_first)<=8000 or len(original)<300000:
        raise RuntimeError("Wrong original opening / missing voice audio")
    intro=create_intro()
    # Retain the entire episode after the existing opening's 6.74-second boundary.
    # A tiny crossfade prevents clicks but does not cut any spoken line.
    edited=intro.append(original[OLD_CUT_MS-CROSSFADE_MS:],crossfade=CROSSFADE_MS)
    edited=edited.fade_out(700)
    edited.export(OUTPUT,format="mp3",bitrate="128k",
                  tags={"title":metadata["title"]+"（静かなオープニング版）",
                        "album":metadata["series"],
                        "artist":metadata["voice_attribution"],
                        "comment":"Opening music replaced only; voice and lesson unchanged"})
    verified=AudioSegment.from_mp3(OUTPUT)
    if OUTPUT.stat().st_size<1000000 or abs(len(verified)-len(edited))>600:
        raise RuntimeError("MP3 validation failed")
    shift=(INTRO_MS-OLD_CUT_MS)/1000
    updated=dict(metadata)
    updated["edition"]="soft-opening-v2"
    updated["filename"]=OUTPUT.name
    updated["sha256"]=hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    updated["original_sha256"]=original_sha
    updated["seconds"]=round(len(verified)/1000)
    updated["duration_label"]=f'{updated["seconds"]//60}分{updated["seconds"]%60}秒'
    updated["opening_style"]="控えめなピアノ風3音と柔らかな和音。効果音・ゲーム調の音楽なし。"
    updated["original_content_preserved"]=True
    updated["chapters"]=[
        dict(ch,start_seconds=round(ch["start_seconds"]+shift,2))
        for ch in metadata["chapters"]
    ]
    if abs(updated["chapters"][0]["start_seconds"]-4.3)>0.1:
        raise RuntimeError("New chapter offset incorrect")
    OUTPUT_META.write_text(json.dumps(updated,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SOFTINTRO_SUCCESS",OUTPUT,OUTPUT.stat().st_size,"bytes",updated["seconds"],"seconds",flush=True)

if __name__=="__main__":
    build()
