#!/usr/bin/env python3
"""One-page original after-listening worksheet for Science Sun Special Episode 02."""
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.colors import HexColor
P=Path(__file__).resolve().parent.parent/'site'/'science'/'episode02_sun-worksheet.pdf'
P.parent.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
W,H=A4
c=canvas.Canvas(str(P),pagesize=A4)
ink=HexColor('#183a53');gold=HexColor('#b57b25');pale=HexColor('#eff5f9');gray=HexColor('#627684')
def t(x,y,s,size=10,col=ink):
    c.setFont('HeiseiKakuGo-W5',size);c.setFillColor(col);c.drawString(x,y,s)
def line(x1,y1,x2,y2,col=HexColor('#afc2d0'),width=.8):
    c.setStrokeColor(col);c.setLineWidth(width);c.line(x1,y1,x2,y2)
def rectangle(x,y,w,h,color=pale):
    c.setFillColor(color);c.rect(x,y,w,h,stroke=0,fill=1)
rectangle(0,H-22,W,22,ink)
t(40,H-54,'理科のふしぎラジオ　第02回',11,gold)
t(40,H-88,'春分・夏至・秋分・冬至　太陽の四季事件簿',17,ink)
t(40,H-111,'ラジオは聴くだけで完結。これは聴いた後の復習用です。',9,gray)
t(40,H-135,'名前：　　　　　　　　　　　　　日付：',9,gray)
rectangle(40,645,515,33)
t(52,657,'捜査資料A　四つの節目を調べよう',12,ink)
# Summary recall table with room for filling
xcols=[40,121,221,340,440,555]
head=['節目','だいたい何月？','南中高度','昼の長さ','南中時の影']
for i,h in enumerate(head): t(xcols[i]+5,624,h,9,ink)
line(40,615,555,615)
seasons=['春分','夏至','秋分','冬至']
for i,s in enumerate(seasons):
    y=584-40*i
    if i%2==0:rectangle(40,y-14,515,37,HexColor('#f5f9fb'))
    t(48,y,s,11,ink)
    for j in range(1,5):
        line(xcols[j]+9,y-6,xcols[j+1]-12,y-6)
line(40,448,555,448)
t(40,424,'捜査資料B　高さ1メートルの棒を同じ場所の南中時に観察',10,ink)
t(40,409,'影の長さは A＝20cm、B＝70cm、C＝160cm。季節を当てよう。',9,gray)
# Three visual shadow bars with unit labels
labels=[('A',20,100),('B',70,215),('C',160,330)]
for lab,cm,x in labels:
    base=355
    c.setStrokeColor(ink);c.setLineWidth(3);c.line(x,base,x,base+42)
    c.setStrokeColor(gold);c.setLineWidth(5);c.line(x,base,x+cm*.85,base)
    t(x,base+48,lab,11,ink)
    t(x,base-20,str(cm)+' cm',9,gray)
t(40,318,'夏至＝（　　　）　春分・秋分＝（　　　）　冬至＝（　　　）',10,ink)
rectangle(40,269,515,29)
t(52,278,'捜査資料C　北緯35度の町。南中高度を計算せよ',11,ink)
t(47,242,'春分・秋分：90－35＝（　　　　　）度',10,ink)
t(47,221,'夏至：55＋23.4＝（　　　　　）度',10,ink)
t(47,200,'冬至：55－23.4＝（　　　　　）度',10,ink)
line(40,186,555,186)
t(40,165,'入試型　なぜ冬至の南中時には、夏至より影が長くなるのか。',10,ink)
line(48,140,547,140)
line(48,117,547,117)
t(40,91,'合言葉：夏至＝高い・長い・影は短い',10,gold)
t(40,73,'　　　　冬至＝低い・短い・影は長い',10,gold)
t(40,48,'参考：2026年 春分3/20　夏至6/21　秋分9/23　冬至12/22',8.5,gray)
t(40,34,'日付の出典：国立天文台・令和8年（2026）暦要項',8,gray)
c.showPage();c.save()
assert P.read_bytes().startswith(b'%PDF-')
print('SUN WORKSHEET CREATED',P,P.stat().st_size)
