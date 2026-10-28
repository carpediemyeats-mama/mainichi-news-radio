#!/usr/bin/env python3
"""Build the independent original history radio series.

Reuses the tested VOICEVOX + pydub + ffmpeg strategy from ../build_radio.py.
Never publishes placeholder MP3s; output goes to site/history only.
"""
import hashlib
import json
import math
import re
import tempfile
import time
from pathlib import Path

import requests
from pydub import AudioSegment
from pydub.generators import Sine

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site" / "history" / "chronology"
SITE.mkdir(parents=True, exist_ok=True)
API = "http://127.0.0.1:50021"
VOICES = {
    "host": ("No.7", "アナウンス", 30, 1.04),
    "detective": ("ずんだもん", "ノーマル", 3, 1.08),
}
SILENCE = AudioSegment.silent(duration=150, frame_rate=44100).set_channels(2)


def note(midi, duration, volume=-28):
    frequency = 440 * 2 ** ((midi - 69) / 12)
    return (Sine(frequency).to_audio_segment(duration=duration)
            .apply_gain(volume).fade_in(18).fade_out(min(130, duration // 3))
            .set_channels(2).set_frame_rate(44100))


def original_theme(bars=2, soft=False):
    """A new, original curious/adventurous motif; no stock/copyrighted music."""
    beat = 390 if not soft else 550
    length = bars * 4 * beat + 410
    track = AudioSegment.silent(duration=length, frame_rate=44100).set_channels(2)
    chords = [(50, [62, 65, 69]), (48, [60, 64, 67]),
              (46, [58, 62, 65]), (45, [57, 60, 64])]
    motif = [69, 72, 74, 77, 74, 72, 69, 65]
    for b in range(bars):
        root, chord = chords[b % len(chords)]
        for k in range(4):
            pos = (b * 4 + k) * beat
            track = track.overlay(note(root-12, int(beat * .8),
                                       -41 if soft else -29), position=pos)
            if k == 0:
                for n in chord:
                    track = track.overlay(note(n, int(beat * 2.2),
                                               -47 if soft else -37), position=pos)
            if not soft:
                track = track.overlay(note(motif[(b * 4 + k) % len(motif)],
                                           int(beat * .7), -24), position=pos+45)
    return track.fade_in(180).fade_out(280)


def validate_voices():
    response = requests.get(API + "/speakers", timeout=45)
    response.raise_for_status()
    speakers = response.json()
    for key, (name, style, speaker_id, speed) in VOICES.items():
        if not any(v.get("name") == name and
                   any(s.get("id") == speaker_id and s.get("name") == style
                       for s in v.get("styles", []))
                   for v in speakers):
            raise RuntimeError(f"Missing VOICEVOX voice {key}: {name}/{style}/{speaker_id}")
        print(f"Verified voice {key}: {name}/{style}/{speaker_id}", flush=True)


def split_sentences(text, maximum=105):
    parts = re.findall(r"[^。！？!?]+[。！？!?]?", text)
    out = []
    for part in parts:
        part = part.strip()
        while len(part) > maximum:
            cut = max(part.rfind("、", 0, maximum), part.rfind("，", 0, maximum))
            cut = cut+1 if cut > 36 else maximum
            out.append(part[:cut])
            part = part[cut:]
        if part:
            out.append(part)
    return out


def voice_segment(text, speaker, path):
    _, _, voice_id, speed = VOICES[speaker]
    for attempt in range(3):
        try:
            query = requests.post(API + "/audio_query",
                                  params={"speaker": voice_id, "text": text},
                                  timeout=90)
            query.raise_for_status()
            payload = query.json()
            payload["speedScale"] = speed
            payload["volumeScale"] = 1.0 if speaker == "host" else .90
            wav = requests.post(API + "/synthesis",
                                params={"speaker": voice_id},
                                json=payload, timeout=240)
            wav.raise_for_status()
            if not wav.content.startswith(b"RIFF") or len(wav.content) < 3000:
                raise RuntimeError("Invalid or empty VOICEVOX WAV")
            path.write_bytes(wav.content)
            return AudioSegment.from_wav(path).set_frame_rate(44100).set_channels(2)
        except Exception as error:
            print(f"TTS retry {attempt+1}/3: {error}", flush=True)
            if attempt == 2:
                raise
            time.sleep(3 * (attempt+1))


def build():
    episode = json.loads((ROOT/"history"/"chronology"/"episode.json").read_text(encoding="utf-8"))
    chapters = episode["chapters"]
    ep_id = episode["id"]
    if not re.fullmatch(r"chronology-\d{3}(?:-[a-z0-9]+)?", ep_id):
        raise ValueError("Episode identifier must be chronology-NNN")
    if len(chapters) < 2 or len(chapters) > 12:
        raise ValueError("History radio expects between 2 and 12 chapters")
    if not all(c.get("title") and c.get("segments") for c in chapters):
        raise ValueError("Missing chapter or script")
    validate_voices()
    opening = original_theme(4)
    transition = original_theme(1)-5
    bed = original_theme(4, soft=True)-7
    full = opening + AudioSegment.silent(duration=380, frame_rate=44100).set_channels(2)
    indices = []
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        for ci, chapter in enumerate(chapters):
            if ci:
                full += transition + AudioSegment.silent(duration=180, frame_rate=44100).set_channels(2)
            indices.append({"title": chapter["title"],
                            "start_seconds": round(len(full)/1000, 1)})
            speech = AudioSegment.silent(duration=140, frame_rate=44100).set_channels(2)
            for si, seg in enumerate(chapter["segments"]):
                who = seg["speaker"]
                if who not in VOICES:
                    raise ValueError(f"Unknown speaker: {who}")
                pieces = split_sentences(seg["text"])
                if not pieces:
                    raise ValueError("Empty spoken segment")
                for pi, piece in enumerate(pieces):
                    print(f"Chapter {ci+1}/{len(chapters)} dialogue {si+1} part {pi+1}: {piece[:26]}", flush=True)
                    speech += voice_segment(piece, who, temp/f"{ci}-{si}-{pi}.wav")
                    speech += AudioSegment.silent(duration=130 if pi < len(pieces)-1 else 230,
                                                  frame_rate=44100).set_channels(2)
                if seg.get("pause_ms"):
                    speech += AudioSegment.silent(duration=min(int(seg["pause_ms"]), 8000),
                                                  frame_rate=44100).set_channels(2)
            ambience = (bed * (len(speech)//len(bed)+1))[:len(speech)].apply_gain(-18)
            full += ambience.overlay(speech)
            print(f"Finished chapter {ci+1}: {len(speech)/1000:.1f}s", flush=True)
    full += original_theme(3).fade_out(1000)
    full = full.fade_in(70).fade_out(750)
    audio_name = ep_id + ".mp3"
    output = SITE/audio_name
    full.export(output, format="mp3", bitrate="128k",
                tags={"title": episode["title"], "artist": "歴史の謎を追え・年代順タイムトラベル",
                      "comment": "VOICEVOX:No.7 / VOICEVOX:ずんだもん"})
    checked = AudioSegment.from_mp3(output)
    seconds = round(len(checked)/1000)
    if not 180 <= seconds <= 900 or output.stat().st_size < 250_000:
        raise RuntimeError(f"Generated audio too short/large: {seconds}s {output.stat().st_size} bytes")
    if abs(len(full)-len(checked)) > 500:
        raise RuntimeError("MP3 length integrity check failed")
    sha = hashlib.sha256(output.read_bytes()).hexdigest()
    public_data = {
        "id": ep_id,
        "title": episode["title"],
        "subtitle": episode["subtitle"],
        "episode_number": episode["episode_number"],
        "audio_file": audio_name,
        "duration_seconds": seconds,
        "duration_label": f"{seconds//60}分{seconds%60}秒",
        "sha256": sha,
        "chapters": indices,
    }
    (SITE/"episode.json").write_text(json.dumps(public_data, ensure_ascii=False, indent=2), encoding="utf-8")
    # Keep immutable episode metadata and a chronological listening catalog.
    (SITE/(ep_id+".json")).write_text(json.dumps(public_data, ensure_ascii=False, indent=2), encoding="utf-8")
    catalog_path = SITE/"catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else []
    catalog = [x for x in catalog if x["id"] != ep_id]
    catalog.append({k: public_data[k] for k in
                    ("id", "episode_number", "title", "subtitle", "audio_file", "duration_label", "duration_seconds", "sha256")})
    catalog.sort(key=lambda x: (x["episode_number"], x["id"]))
    catalog_path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"SUCCESS {output} {output.stat().st_size} bytes {seconds} seconds SHA256 {sha}", flush=True)


if __name__ == "__main__":
    build()
