#!/usr/bin/env python3
"""Create a separate relaxed star-review MP3 with proven VOICEVOX / pydub code.
No quiz waiting, no edits to the other three science audio files or earlier radio shows.
"""
import datetime,hashlib,json,sys,tempfile
from pathlib import Path
from pydub import AudioSegment
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE))
import build_radio as original
audio=original.audio
SOURCE=HERE/"review_listen.json"
DEST=ROOT/"site"/"science"/"tentai04"
DEST.mkdir(parents=True,exist_ok=True)

def main():
    show=json.loads(SOURCE.read_text(encoding="utf-8"))
    if show["id"]!="tentai04-review-listen-001" or len(show["chapters"])!=4:
        raise RuntimeError("Unrecognized source")
    script="".join(phrase for scene in show["chapters"] for role,phrase in scene["lines"])
    if not 2000<=len(script)<=3400:
        raise RuntimeError("Relaxed review needs a conversational script")
    if any(role not in ("host","side","expert") for scene in show["chapters"] for role,_ in scene["lines"]):
        raise RuntimeError("Invalid voice role")
    anchors=("ベガ","デネブ","アルタイル","ベテルギウス","シリウス","プロキオン","アンタレス","リゲル","自転","公転","星座早見","等級","青白い")
    if any(script.count(x)<2 for x in anchors):
        raise RuntimeError("At least one high-priority exam anchor lacks natural repetition")
    voices=audio.get_speakers()
    musicbed=audio.music(4,background=True)
    timeline=original.star_theme(2)+audio.silence(240)
    index=[]
    with tempfile.TemporaryDirectory() as temp:
        i=0
        for chap_no,chapter in enumerate(show["chapters"]):
            if chap_no:
                timeline+=original.star_theme(1).apply_gain(-11)+audio.silence(190)
            index.append({"title":chapter["title"],"start_seconds":round(len(timeline)/1000,2)})
            for role,phrase in chapter["lines"]:
                # A gentle conversational cadence, not an oral exam.
                for chunk in audio.word_chunks(phrase,maximum=95):
                    i+=1
                    spoken=audio.speak(chunk,role,voices,Path(temp)/f"listen_{i:04d}.wav")
                    phrase_audio=audio.silence(80)+spoken+audio.silence(230)
                    timeline+=audio.with_background(phrase_audio,musicbed)
            print("CHAPTER",chap_no+1,chapter["title"],round(len(timeline)/1000,1),flush=True)
    timeline+=original.star_theme(1)
    timeline=timeline.fade_in(100).fade_out(750)
    output=DEST/"review_listen.mp3"
    timeline.export(output,format="mp3",bitrate="128k",tags={
        "title":"星空探偵ラジオ ②復習・聞き流し編",
        "album":show["series"],
        "artist":"星空探偵ラジオ / VOICEVOX",
        "comment":"Original conversation and music with high-yield exam terms, no quiz questions"
    })
    decoded=AudioSegment.from_mp3(output)
    sec=len(decoded)/1000
    if not 210<sec<850 or abs(len(decoded)-len(timeline))>450 or output.stat().st_size<300000:
        raise RuntimeError(f"Expected real review MP3, got {sec:.2f}s")
    meta={
      "episode_id":show["id"],"series":show["series"],"title":show["title"],
      "subtitle":show["subtitle"],"filename":output.name,
      "edition":"第4回 天体の観測","seconds":round(sec),
      "sha256":hashlib.sha256(output.read_bytes()).hexdigest(),
      "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      "build_id":datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
      "chapters":index,"mode":"relaxed_listening","quiz_count":0,
      "notes":"高頻出事項を繰り返し、出題せず自然な対話で振り返る"
    }
    (DEST/"review_listen.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
    print("SUCCESS REVIEW LISTEN",output,round(sec,2),"seconds",output.stat().st_size,"bytes",flush=True)
if __name__=="__main__":
    main()
