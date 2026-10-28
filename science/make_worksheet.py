#!/usr/bin/env python3
"""Produce a single Japanese A4 review worksheet after the audio is complete."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
OUT=Path(__file__).resolve().parent.parent/'site'/'science'/'episode01-worksheet.pdf'
OUT.parent.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
w,h=A4
c=canvas.Canvas(str(OUT),pagesize=A4)
navy=HexColor('#173d47'); green=HexColor('#0c8171')
c.setFillColor(green);c.rect(0,h-18,w,18,fill=1,stroke=0)
c.setFont('HeiseiKakuGo-W5',19);c.setFillColor(navy)
c.drawString(42,h-65,'理科のふしぎラジオ　第01回')
c.setFont('HeiseiKakuGo-W5',12)
c.drawString(42,h-92,'さなぎは、いる？ いない？　昆虫変身ミステリー')
c.setFont('HeiseiKakuGo-W5',10)
c.drawString(42,h-119,'放送は耳だけで楽しめます。聴き終えたら、思い出せることを書こう。')
c.drawString(42,h-140,'名前：　　　　　　　　　　　　　　　　日にち：')
questions=[
 ('1','モンシロチョウ：たまご → 幼虫 →（　　　　　　　）→ 成虫'),
 ('2','さなぎの時期がある育ち方を何という？（　　　　　　　　　）'),
 ('3','成虫になるときの最後の変身を何という？（　　　　　　　）'),
 ('4','モンシロチョウは幼虫のとき何を食べる？（　　　　　　　　）'),
 (' ','成虫のとき主に何を吸う？（　　　　　　　　　　　　　　）'),
 ('5','カブトムシは完全変態・不完全変態のどちら？（　　　　　　　）'),
 ('6','セミの育ち方は？（　　　　　　　　　　　　　　　　）'),
 ('7','セミの幼虫は木の（　　　　　　）から汁を吸う。'),
 (' ','成長するときに古い皮をぬぐことは？（　　　　　　　）'),
 ('8','トンボの幼虫「ヤゴ」の育ち方は？（　　　　　　　　　）'),
]
y=h-185
c.setStrokeColor(HexColor('#d5e5e5'))
for n,q in questions:
 if n.strip():
  c.setFillColor(green);c.circle(49,y+3,12,stroke=0,fill=1)
  c.setFillColor(HexColor('#ffffff'));c.setFont('HeiseiKakuGo-W5',10);c.drawCentredString(49,y,n)
 c.setFillColor(navy);c.setFont('HeiseiKakuGo-W5',10.6);c.drawString(72,y,q)
 c.line(42,y-17,w-42,y-17);y-=49
c.setFillColor(green);c.setFont('HeiseiKakuGo-W5',11)
c.drawString(42,135,'今日いちばんおどろいた発見')
c.setStrokeColor(HexColor('#8fc9bf'));c.rect(42,60,w-84,62,stroke=1,fill=0)
c.setFillColor(HexColor('#53747c'));c.setFont('HeiseiKakuGo-W5',8.6)
c.drawString(42,38,'復習：完全変態＝さなぎあり ／ 不完全変態＝さなぎなし')
c.showPage();c.save()
assert OUT.read_bytes().startswith(b'%PDF-')
print('WORKSHEET PDF:',OUT.stat().st_size,'bytes')
