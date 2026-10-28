#!/usr/bin/env python3
"""Astronomy radio: three self-contained VOICEVOX dramas; original music and actual thinking time.
The proven audio primitives in build_kotowaza_radio.py are reused without editing existing shows.
"""
import datetime,hashlib,json,sys,tempfile
from pathlib import Path
from pydub import AudioSegment
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import build_kotowaza_radio as audio
audio.CAST={
 "host":("No.7","アナウンス",1.06),
 "side":("ずんだもん","ノーマル",1.03),
 "expert":("四国めたん","ノーマル",1.05),
}
INPUT=Path(__file__).with_name("episodes.json")
DEST=ROOT/"site"/"science"/"tentai04"
DEST.mkdir(parents=True,exist_ok=True)
def star_theme(bars=2):
 """Original sparkling starfield motif, unrelated to the vocabulary theme."""
 step=300
 arr=audio.silence(bars*8*step+460)
 progression=[(48,[72,76,79,84]),(45,[69,72,76,81]),(41,[65,69,72,77]),(43,[67,71,74,79])]
 for n in range(bars):
  bass,chord=progression[n%4]
  for beat in range(8):
   at=(n*8+beat)*step
   if beat%2==0:arr=arr.overlay(audio.note(bass,380,-33),position=at)
   if beat in (0,4):
    for note in chord[:3]:arr=arr.overlay(audio.note(note,510,-40),position=at)
   if beat in (1,3,4,6):arr=arr.overlay(audio.note(chord[(beat+n)%4]+12,220,-26),position=at+35)
 return arr.fade_in(130).fade_out(330)
def wait_music(milliseconds):
 block=audio.silence(milliseconds)
 for k in range(milliseconds//1000):
  block=block.overlay(audio.note(79,75,-39),position=k*1000+100)
 return block
def build_episode(info,voices,background,original):
 stem=info["id"]
 if stem not in ("pre","review","deep"):raise ValueError("unknown episode")
 scenes=info["chapters"]
 if len(scenes)<3:raise ValueError("Need several meaningful chapters")
 whole=star_theme(2)+audio.silence(130)
 markers=[]
 sample_count=0; pause_count=0
 with tempfile.TemporaryDirectory() as folder:
  for chapter_no,scene in enumerate(scenes):
   if chapter_no>0:whole+=star_theme(1)-11+audio.silence(130)
   markers.append({"title":scene["title"],"start_seconds":round(len(whole)/1000,2)})
   for line in scene["lines"]:
    role,content=line
    if role=="pause":
     if not isinstance(content,int) or content<2000 or content>9000:raise ValueError("bad pause")
     whole+=wait_music(content);pause_count+=1
    else:
     if role not in voices or not content.strip():raise ValueError("unrecognized or empty dialogue")
     for part in audio.word_chunks(content,maximum=95):
      sample_count+=1
      clip=audio.speak(part,role,voices,Path(folder)/f"{stem}_{sample_count:04d}.wav")
      speech=audio.silence(45)+clip+audio.silence(95)
      whole+=audio.with_background(speech,background)
   print("CHAPTER",stem,scene["title"],len(whole)//1000,"s",flush=True)
 whole+=star_theme(1)
 whole=whole.fade_in(90).fade_out(750)
 path=DEST/f"{stem}.mp3"
 whole.export(path,format="mp3",bitrate="128k",tags={"title":info["title"]+"・"+info["subtitle"],"album":original["series"],"artist":"星空探偵ラジオ・VOICEVOX","comment":"Original educational dialogue and procedural BGM"})
 decoded=AudioSegment.from_mp3(path)
 secs=len(decoded)/1000
 if path.stat().st_size<220000 or not 180<secs<1000 or abs(len(decoded)-len(whole))>450:
  raise RuntimeError(f"invalid real MP3: {stem}, {secs}s")
 if pause_count<3:raise RuntimeError("quiz waiting periods missing")
 source_digest=hashlib.sha256(INPUT.read_bytes()).hexdigest()
 meta={
 "edition":"第4回 天体の観測","episode_id":"tentai04-"+stem,
 "series":original["series"],"title":info["title"],"subtitle":info["subtitle"],
 "filename":path.name,"audience":info["audience"],"seconds":round(secs),
 "build_id":datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
 "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
 "source_sha256":source_digest,"chapters":markers,
 "thinking_pauses":pause_count,"source_note":original["source"]
 }
 (DEST/f"{stem}.json").write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding="utf-8")
 print("VERIFIED",stem,round(secs),path.stat().st_size,pause_count,"pauses",flush=True)
 return meta
def main():
 original=json.loads(INPUT.read_text(encoding="utf-8"))
 episodes=original["episodes"]
 if [e["id"] for e in episodes]!=["pre","review","deep"]:raise ValueError("must build pre-review-deep")
 voices=audio.get_speakers()
 background=audio.music(3,background=True)
 results=[build_episode(ep,voices,background,original) for ep in episodes]
 (DEST/"manifest.json").write_text(json.dumps({"series":original["series"],"order":["pre","review","deep"],"episodes":[{"id":ep["episode_id"],"filename":ep["filename"],"title":ep["title"],"seconds":ep["seconds"],"sha256":ep["sha256"]} for ep in results]},ensure_ascii=False,indent=2),encoding="utf-8")
 print("SUCCESS all three complete and independent")
if __name__=="__main__":main()
