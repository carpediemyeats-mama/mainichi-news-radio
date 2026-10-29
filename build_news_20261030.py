#!/usr/bin/env python3
from pathlib import Path
import build_radio as radio
base=Path(__file__).resolve().parent
radio.ROOT=base/'editions'/'2026-10-30'
radio.SITE=base/'site'/'2026-10-30'
radio.RATE=0.93
radio.SITE.mkdir(parents=True,exist_ok=True)
radio.build()
