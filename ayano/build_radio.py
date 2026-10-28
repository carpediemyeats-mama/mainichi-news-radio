#!/usr/bin/env python3
"""Daily short morning show. Reuses proven mainichi-news-radio synthesis functions.
Only original procedural music and freshly synthesized VOICEVOX audio.
"""
import datetime as dt
import hashlib
import json
import random
import re
import tempfile
import time
from pathlib import Path

import requests
from pydub import AudioSegment

import importlib.util
# Load the proven news synthesizer by its absolute path. Do not import this
# file as build_radio again (the filenames intentionally match).
_core=Path(__file__).resolve().parents[1]/"build_radio.py"
_spec=importlib.util.spec_from_file_location("mainichi_voice_core",_core)
radio=importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(radio)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "site" / "ayano"
OUT.mkdir(parents=True, exist_ok=True)
VOICE_ID = 29  # VOICEVOX No.7 normal, verified by /speakers at runtime
radio.VOICE_ID = VOICE_ID
radio.RATE = 1.0
TZ = dt.timezone(dt.timedelta(hours=9))
WEEK = "月火水木金土日"
CODES = {
    0: "晴れ", 1: "おおむね晴れ", 2: "晴れ時々曇り", 3: "曇り",
    45: "霧", 48: "霧", 51: "小雨", 53: "小雨", 55: "雨",
    61: "雨", 63: "雨", 65: "強い雨", 71: "雪", 73: "雪",
    75: "雪", 80: "にわか雨", 81: "にわか雨", 82: "強いにわか雨",
    95: "雷雨", 96: "雷雨", 99: "雷雨"
}

def forecast(today):
    """Fetch today's current forecast; on failure speak uncertainty, not fabricated data."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = dict(latitude=34.815, longitude=134.685, timezone="Asia/Tokyo",
                  daily="weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
                  forecast_days=2)
    try:
        response = requests.get(url, params=params, timeout=25)
        response.raise_for_status()
        data = response.json()["daily"]
        i = data["time"].index(today.isoformat())
        hi = round(float(data["temperature_2m_max"][i]))
        lo = round(float(data["temperature_2m_min"][i]))
        rain = int(data["precipitation_probability_max"][i])
        label = CODES.get(int(data["weather_code"][i]), "変わりやすい空模様")
        advice = ("傘をバッグに入れておくと安心ですね。" if rain >= 45 else
                  "急な天気の変化には、出かける前に空を確認してくださいね。")
        if hi - lo >= 8:
            advice += "朝と日中の気温差にも気をつけて、脱ぎ着しやすい服が便利です。"
        if hi <= 15: advice += "温かい羽織ものがあると心強いですね。"
        if hi >= 27: advice += "暑さ対策と水分補給も忘れずに。"
        spoken = (f"まずは今日の姫路市のお天気です。予報は{label}。"
                  f"予想最高気温は{hi}度、最低気温は{lo}度。"
                  f"雨の降る確率は、一日の中で最大{rain}パーセントの予報です。"
                  + advice + "天気予報は変わることがあるので、最新情報も確認してくださいね。")
        return spoken, {"source":"Open-Meteo","date":today.isoformat(),"label":label,
                        "high_c":hi,"low_c":lo,"rain_probability_max":rain}
    except Exception as error:
        print("FORECAST_UNAVAILABLE", repr(error), flush=True)
        return ("まずは姫路市のお天気です。今朝は最新の予報を取得できませんでした。"
                "お出かけの前に、姫路の天気と気温、雨雲の様子を確認してくださいね。"
                "晴れでも曇りでも、自分が心地よい服を選んでみましょう。"), {"source":"unavailable","date":today.isoformat()}

WAKE = [
    "さあ、まずはお布団の中で足首をゆっくり回してみましょう。右にくるくる、左にくるくる。今度は両手を上に伸ばして、ぐーっと背伸び。眠っていた身体が少しずつ起きていくのを感じます。いきなり頑張らなくて大丈夫。まずは上半身を起こして、肩の力を抜いてみましょう。",
    "最初に、ゆっくり目を開けて、窓から入る光を感じてみませんか。できそうなら腕を左右に広げ、背中をすうっと伸ばします。足を床につけたら、肩を前に三回、後ろに三回。深呼吸をひとつ。今日の朝は、ここから始まります。",
    "起きたばかりの身体には、優しい動きから。手をぎゅっと握って、ぱっと開いて。もう一度。次は首を無理に回さず、肩をすくめて、すとんと落としましょう。お水をひと口飲んだら、カーテンを開ける準備です。完璧な朝より、気持ちのいい朝を選びましょう。"
]
BEAUTY = [
    "私が今日楽しみにしているのは、朝のスキンケア。洗顔したら、保湿を丁寧に。そして日焼け止め。たったそれだけでも、鏡の中の自分に少し優しくなれる気がするんです。時間があれば、リップに明るい色をひと塗り。家にいる日にも、自分の好きな色を使っていいんですよね。",
    "今日の小さな美容テーマは、髪。ブラシで毛先から優しく整えて、今日は低めのひとつ結びにしてみようかな。顔まわりを少し残すと、ただまとめただけでも柔らかい印象に。髪型が決まると、いつもの服もちょっと新鮮に見えるから不思議です。",
    "今日の美容テーマは姿勢です。背筋を無理に反らすのではなく、頭のてっぺんを軽く引き上げる気持ちで。肩は力を抜いて。昨日と同じニットでも、姿勢と表情が変わると気分まで違う気がします。今の自分の身体で、おしゃれを楽しみたいですね。",
    "今日は洋服を一着、いつもと違う組み合わせにしてみたい気分。明るい色を主役にしても、黒をきりっと着ても、どちらも素敵。診断のルールより、今朝の自分が『着たい』と思う気持ちを大切に。アクセサリーをひとつ選ぶ時間も、朝の楽しみになります。",
    "朝のメイクは、たくさん重ねなくても大丈夫。保湿をした肌に日焼け止めを塗って、眉を整えて、頬に少し血色を。笑ったときの自分の顔が好きになれたら、それだけで今日はいいスタート。今日はどんな服を着ようかな、という気持ちが湧いてきます。"
]
LIFE = [
    "朝の手帳は、ぎっしり予定を書かなくてもいいんです。私は『今日、ひとつだけ楽しみにしたいこと』を小さく書く日があります。新しい紅茶を飲む。夕飯をいつもより丁寧に盛る。帰り道に空を見る。そんな小さな約束があるだけで、一日がちょっと違って見えます。",
    "今日は部屋を全部片付けようとしないことにしました。代わりに、テーブルの上のものを三つだけ元の場所へ。好きな花瓶がよく見えるようになったら、それだけで嬉しい。片付けは自分を責めるためじゃなくて、好きな場所をもっと心地よくするためのものなんですよね。",
    "最近、スマホを見ているうちに時間が過ぎてしまうことがあります。そんなときは、読みかけの本のページを一枚だけめくってみるんです。物語が面白いと、気づけば続きを読んでいることも。今日はどんな世界に出会えるかな。そんな楽しみを持っていたいです。",
    "子どもが何度も話しかけてくる日は、つい『あとでね』と言いたくなります。でも、ふと顔を上げてみると、すごく面白い話をしてくれていたりして。もちろん忙しいときは待ってもらってもいい。あとで目を見て話を聞く数分が、家族にとって素敵な時間になることもあります。",
    "今日は筋トレを長くするより、家の中で気持ちよく身体を動かすことを選びたい気分。音楽を一曲流して、肩をほぐして、足を動かして。疲れている日は休むのも大切です。おしゃれも運動も、自分の暮らしを楽しくするためのものですから。",
    "最近、紅茶の香りにちょっと夢中です。すっきりしたダージリン、コクのあるアッサム、ベルガモットが華やかなアールグレイ。同じティーカップでも、茶葉を変えるだけで違う時間になる。今日の一杯を楽しみに、ゆっくり朝を始めたいですね。",
    "今日は帰り道、いつもと違う棚をのぞいてみようかな。本屋さんの料理本のコーナー、花屋さんの小さな鉢植え、文房具屋さんのきれいなノート。新しいものを買わなくても、知らなかったものに出会うだけで心が弾みます。",
    "今日は忙しい日になりそう。そんな朝は、やりたいことを全部詰め込むより、優先するものをひとつだけ決めます。食事をおいしく食べること。家族にひと言優しく話しかけること。夜、早めに眠ること。どれかひとつできれば十分、と思って出かけます。"
]
FOOD = [
    "朝ごはんは、好きな器をひとつ使ってみませんか。トーストなら焼けた香りを感じて、卵なら黄身の柔らかさを味わって。お味噌汁なら、湯気の向こうの香りまで。私は食べることが大好きだから、急いで終わらせるのがもったいなく感じるんです。ちゃんとお腹がすいている日は、必要な分をおいしく食べましょう。",
    "食卓に座ったら、まず温かい飲み物を一口。パンの表面がさくっとする音や、炊きたてのごはんの香り。今日はそんな小さなことに気づきながら食べたいな。子どもたちのために買ったお菓子が気になる日もあるけれど、食べたいならお皿に出して楽しめばいい。何となくつまむより、味わう時間が好きです。",
    "お弁当作りの朝は、つい自分の朝食が後回しになりがち。でも、温かいお茶を淹れて、椅子に座って食べる時間を取りたい。ごはんをひと口、卵焼きをひと口。いつもの味なのに、落ち着いて食べるとおいしさが増すような気がします。忙しい日こそ、自分も大切にしてあげたいですね。"
]
# The daily personal story is fiction. Movie release information has been
# checked against Japanese cinema schedules before being included.
STORIES = [
"""最近、朝の支度を少し楽しくしたくて、ヘアクリップを一つ買ったんです。べっ甲風の、小さくて軽いもの。髪をブラシで丁寧にとかして、低い位置に集めてくるっと留めるだけ。五分もかからないのに、いつもの服がちょっと違って見えるんです。この前、次男がそれを見て、お母さん、その髪型いいね、と言ってくれました。本人は何気なく言っただけでしょうけれど、何だかすごく嬉しくて。今日は少し明るい色のチークをつけようかな。そうそう、昨日は夕飯の準備の途中で、子どもたちのお菓子の袋を見つけてしまって。好きな味のポテトチップスって、目に入ると急に食べたくなるんですよね。昨日は夕食が楽しみだったので、袋を閉じて、あとでおいしく食べようと思いました。でも今日は食べるかもしれません。おいしいものを、急いでなんとなくつまむより、ゆっくり楽しみたいんです。夜には、気になっている小説の続きを読みたいな。スマホを見ているといつの間にか時間がたつけれど、面白い本を開けば、今度はページをめくる手が止まらなくなる。そういう時間も大好きです。""",
"""この前、会社の帰り道にいつもと違う道を歩いてみたら、小さな花屋さんを見つけたんです。お店の前に、明るい黄色のお花が並んでいて、思わず足を止めました。名前を聞くと、知らなかった種類で。たった一輪だけ買って帰ったのに、キッチンに飾ったら、部屋がぱっと明るくなったんです。最近、こんな小さな出会いが楽しい。今日も帰り道にちょっとだけ寄り道してみようかな。服は黒のニットに、明るい色のピアスを合わせたい気分。私はビビッドスプリングだけれど、黒い服も大好きなんです。鏡を見て嬉しくなれる服が、一番素敵だと思う。そういえば昨日、家の本棚を一段だけ片付けたら、読みかけの本が出てきました。最初の数ページを読んで、そのまま忘れていた小説です。開いてみたら、意外なところで笑ってしまって。今日は続きを読むのが楽しみ。全部を頑張ろうと思うと疲れてしまうけど、好きなことをひとつ見つけるだけで、少し楽しい一日になりますよね。朝ごはんも、好きなお皿を取り出して、座ってゆっくり味わいたいな。""",
"""先週、休日に家族で公園へ出かけたとき、久しぶりにスニーカーとデニムを合わせたんです。上には短めのカーディガン。動きやすい服なのに、自分らしくおしゃれができて嬉しくなりました。公園では子どもたちが走り回っていて、私はベンチで温かい紅茶をひと口。いつものアッサムなのに、お外で飲むとまた違う香りがする気がします。帰り道、古本が並ぶ小さな催しを見つけて、つい立ち寄りました。そこで見つけたのは、料理の写真が美しい古い本。買って帰って、夕飯の盛りつけを少し真似してみたら、いつもの焼き魚まで特別な料理に見えるから不思議。子どもたちも、お店みたいだねって喜んでくれました。もちろん、毎日そんなふうに丁寧にはできません。帰りが遅い日は、あったかいお味噌汁があるだけで嬉しい。何もできない日には、そのまま休んでしまうこともあります。でも、ときどき気分が上がる工夫をしてみると、毎日がちょっと楽しくなりますね。今日は何を食べよう、何を着よう、そう考える時間が好きです。"""
]
SPECIAL = {
"2026-10-29": """今日は木曜日で、会社はお休み。家で過ごす子どもたちと、少し賑やかな一日になりそうです。朝から息子たちは何をして遊ぼうか相談していて、私はようやく温かい紅茶を淹れたところ。食器棚の奥から出てきた、小さな花柄のカップを使ってみたら、ちょっとした喫茶店みたいな気分なんです。今日はいつもより丁寧に朝ごはんを食べたいな。トーストが焼ける香りと、卵の温かさと、カフェオレのやさしい味。あわただしいと、つい立ったまま何かを食べてしまうこともあるけれど、今日は椅子に座って味わおうと思います。そうそう、昨日は長男が読んでいた本を見せに来てくれて、思いがけず大笑いしたんです。子どもたちが家にいると、何度も話しかけられて、つい後にしてって言いたくなることも。でも、あの笑い声を思い出したら、今日は少し話を聞いてみようかなって思いました。夕方は引き出しを一段だけ片付けて、読みかけの小説を開きたい。服は柔らかな黒のニットに、鮮やかな色の小さなピアス。髪は低めに結ぼうと思います。できないことがあっても、今日一日を楽しめたら嬉しいな。""",
"2026-10-30": """今週末、気になっている映画があるんです。十月三十日から、映画、耳をすませば、の、よんケー、デジタルリマスター版が上映されると知りました。昔の作品を、新しい映像で大きなスクリーンで見られるのって、嬉しいですよね。私は映画を見ると、登場人物の表情だけじゃなくて、部屋の小物や街の風景まで眺めたくなるんです。今週末は子どもたちと、好きな映画の話をしてみたいな。そういえば昨日、子どもの本棚を整理していたら、読んだことのない古い本が出てきました。長男が嬉しそうに説明を始めて、私は途中から聞き役。こんな時間も面白いですよね。帰り道には本屋さんにも寄って、気になる小説を探したい。今日は少し鮮やかな色のカーディガンに、ベージュのスカートを合わせるつもりです。髪は低めのポニーテールにして、頬にはコーラルのチークを少し。自分らしくおしゃれをすると、いつもの仕事の日も少し楽しみになります。朝ごはんは焼きたてのトーストと卵。何より、ゆっくりおいしく食べる時間が好きなんです。"""
}
def personal_story(date):
    return SPECIAL.get(date.isoformat(), STORIES[date.toordinal()%len(STORIES)])

CLOSE = ("そろそろ、私もキッチンへ行って朝の支度を始めます。"
         "今日は全部うまくいかなくても大丈夫。"
         "一口おいしく食べられたり、着たい服を選べたり、好きな本のページを開けたり。"
         "そんな小さな楽しみを見つけられたら、いい一日です。"
         "さあ、カーテンを開けてみましょう。"
         "あなたの今日にも、素敵な発見がありますように。"
         "あやの毎日、おはようラジオでした。いってらっしゃい。")

def verify_speaker():
    result=requests.get(radio.API+"/speakers",timeout=40)
    result.raise_for_status()
    for person in result.json():
        for style in person.get("styles",[]):
            if person.get("name")=="No.7" and style.get("id")==VOICE_ID:
                print("VOICE_CONFIRMED", person["name"], style["name"], VOICE_ID,flush=True)
                return
    raise RuntimeError("No.7 normal voice id 29 was not found: do not substitute a different voice")

def music(bars=3, soft=False):
    """Separate original morning melody, not the news theme."""
    beat=720
    total=bars*4*beat+500
    sound=AudioSegment.silent(duration=total,frame_rate=44100).set_channels(2)
    chords=[(60, [64,67,72]),(57,[60,64,69]),(65,[69,72,76]),(67,[71,74,79])]
    for b in range(bars):
        root, notes=chords[b%4]
        for k in range(4):
            pos=(b*4+k)*beat
            sound=sound.overlay(radio.tone(root-12,950,-38 if soft else -27).set_channels(2), position=pos)
            if k in (0,2):
                sound=sound.overlay(radio.tone(notes[(b+k)%3]+12,390,-42 if soft else -31).set_channels(2),position=pos+100)
    return sound.fade_in(300).fade_out(650)

def build():
    now=dt.datetime.now(TZ)
    date=now.date()
    rng=random.Random(date.toordinal())
    weather, source=forecast(date)
    greetings=f"おはようございます。あやのです。今日は、{date.year}年{date.month}月{date.day}日、{WEEK[date.weekday()]}曜日。おはようラジオへようこそ。今朝も一緒に、気持ちのいい一日を始めましょう。"
    sections=[
        ("おはようございます", greetings),
        ("姫路の今日のお天気", weather),
        ("身体を目覚めさせよう", rng.choice(WAKE)),
        ("もう少し、ゆっくり", "目を覚ますのに、誰かと競う必要はありません。肩の力を抜いて、呼吸をひとつ。今日の自分の調子はどうかな、と確かめるだけで十分。眠たい日は眠たいままでいいんです。座ることができたら、ここから気持ちよく一日を始めましょう。"),
        ("今日の小さな美容", rng.choice(BEAUTY)),
        ("暮らしに小さな楽しみを", rng.choice(LIFE)),
        ("あやのの最近のこと", personal_story(date)),
        ("食事をおいしく味わう", rng.choice(FOOD)),
        ("今日も、いい一日を", CLOSE)
    ]
    intro=music(2)
    inter=music(1,soft=True)-9
    whole=intro+AudioSegment.silent(duration=250)
    indexes=[]
    with tempfile.TemporaryDirectory() as temp:
        folder=Path(temp)
        for n,(title,content) in enumerate(sections):
            indexes.append({"title":title,"start_seconds":round(len(whole)/1000,1)})
            speech=AudioSegment.silent(duration=130,frame_rate=44100).set_channels(2)
            for j,part in enumerate(radio.sentence_chunks(content,maximum=100)):
                speech+=radio.synth(part,folder/f"part-{n}-{j}.wav")
                speech+=AudioSegment.silent(duration=210)
            # Music is intentionally very low and clear underneath the narrator.
            bed=(inter*((len(speech)//len(inter))+1))[:len(speech)].apply_gain(-17)
            whole+=bed.overlay(speech)+AudioSegment.silent(duration=220)
        whole+=music(2)
    whole=whole.fade_in(120).fade_out(600)
    path=OUT/"ayano-radio.mp3"
    whole.export(path,format="mp3",bitrate="128k",
                 tags={"title":f"あやの毎日 おはようラジオ {date.isoformat()}",
                       "artist":"あやの毎日 / VOICEVOX No.7","comment":"original music"})
    decoded=AudioSegment.from_mp3(path)
    duration=round(len(decoded)/1000)
    if not (210 <= duration <= 420) or path.stat().st_size < 320000:
        raise RuntimeError(f"Morning MP3 wrong duration or size: {duration}s {path.stat().st_size} bytes")
    metadata={"date":date.isoformat(),"title":"あやの毎日・おはようラジオ",
              "duration_seconds":duration,"filename":path.name,
              "sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
              "weather":source,"voice":"VOICEVOX No.7 normal (29)",
              "chapters":indexes}
    (OUT/"ayano-radio.json").write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding="utf-8")
    print("VALIDATED",metadata["date"],duration,path.stat().st_size,metadata["sha256"],flush=True)

if __name__=="__main__":
    build()
