#!/usr/bin/env python3
"""Standalone episode of Science Mystery Radio. Reuses verified VOICEVOX functions."""
import sys, re, json, hashlib, tempfile
from pathlib import Path
from pydub import AudioSegment
BASE=Path(__file__).resolve().parent.parent
ROOT=Path(__file__).resolve().parent
OUT=BASE/'site'/'science'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(BASE))
import build_kotowaza_radio_v2 as radio

radio.CAST={
 'host':('No.7','アナウンス',1.03),
 'guest':('青山龍星','ノーマル',1.04)
}

def load():
    source=(ROOT/'episode01.txt').read_text(encoding='utf8')
    chapters=[]; current=None
    for raw in source.splitlines():
        s=raw.strip()
        if not s: continue
        if s.startswith('◆ '):
            current={'title':s[2:],'lines':[]}
            chapters.append(current)
        elif s.startswith('【解答待ち：'):
            if not current: raise ValueError('Pause outside chapter')
            m=re.fullmatch(r'【解答待ち：([0-9.]+)秒】',s)
            if not m: raise ValueError('Unrecognized pause')
            current['lines'].append({'pause_ms':round(float(m.group(1))*1000)})
        elif s.startswith('ナナ：') or s.startswith('リュウ：'):
            if not current: raise ValueError('Speech outside chapter')
            who='host' if s.startswith('ナナ：') else 'guest'
            current['lines'].append({'speaker':who,'text':s.split('：',1)[1]})
    if len(chapters)!=6: raise RuntimeError('Unexpected episode structure')
    if sum('pause_ms' in v for ch in chapters for v in ch['lines'])<14:
        raise RuntimeError('Missing spoken quiz pauses')
    return chapters

def main():
    chapters=load()
    speakers=radio.get_speakers()
    bed=radio.music(4,background=True)
    whole=radio.music(3)+radio.silence(350)
    timestamps=[]
    with tempfile.TemporaryDirectory() as folder:
        count=0
        for idx,ch in enumerate(chapters):
            if idx: whole+=radio.music(1).apply_gain(-8)+radio.silence(180)
            timestamps.append({'title':ch['title'],'start_seconds':round(len(whole)/1000,1)})
            for line in ch['lines']:
                if 'pause_ms' in line:
                    ms=line['pause_ms']
                    if not 1200<=ms<=10000:raise ValueError('Invalid answer pause')
                    gap=radio.silence(ms)
                    gap=gap.overlay(radio.note(79,150,-34),position=60)
                    whole+=gap
                else:
                    combined=radio.silence(90)
                    for phrase in radio.word_chunks(line['text'],maximum=105):
                        count+=1
                        combined+=radio.speak(phrase,line['speaker'],speakers,Path(folder)/f'{count:04d}.wav')
                        combined+=radio.silence(155)
                    whole+=radio.with_background(combined,bed)
            print('SCIENCE CHAPTER',ch['title'],round(len(whole)/1000),'sec',flush=True)
    whole+=radio.music(2)
    whole=whole.fade_in(80).fade_out(800)
    audio_path=OUT/'episode01.mp3'
    whole.export(audio_path,format='mp3',bitrate='128k',
                 tags={'title':'第01回 さなぎは、いる？いない？','album':'理科のふしぎラジオ',
                       'artist':'VOICEVOX:No.7 / 青山龍星','comment':'Original music, 2 speakers and audio-only quiz'})
    check=AudioSegment.from_mp3(audio_path)
    if len(check)<180000 or audio_path.stat().st_size<180000 or abs(len(check)-len(whole))>500:
        raise RuntimeError('Audio verification failed')
    result={'episode_id':'science-episode01','title':'さなぎは、いる？ いない？ 昆虫変身ミステリー',
            'audio_file':'episode01.mp3','seconds':round(len(check)/1000),
            'sha256':hashlib.sha256(audio_path.read_bytes()).hexdigest(),
            'chapters':timestamps,'worksheet':'episode01-worksheet.pdf',
            'voices':['No.7:アナウンス','青山龍星:ノーマル']}
    (OUT/'episode01.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print('SUCCESS',result['seconds'],'sec',audio_path.stat().st_size,'bytes',flush=True)

if __name__=='__main__':main()
