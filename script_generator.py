"""
script_generator.py
3本構成：
  horoscope  - 今日の星座運勢（12星座ローテーション）
  love       - 今日の恋愛運
  encourage  - 静かに寄り添う勇気づけ
"""

import anthropic
import json
import random
import re
from datetime import datetime

client = anthropic.Anthropic()

CONTENT_TYPES = ["horoscope", "love", "encourage"]

ZODIAC_SIGNS = [
    "おひつじざ","おうしざ","ふたござ","かにざ","ししざ","おとめざ",
    "てんびんざ","さそりざ","いてざ","やぎざ","みずがめざ","うおざ"
]

ZODIAC_KANJI = [
    "牡羊座","牡牛座","双子座","蟹座","獅子座","乙女座",
    "天秤座","蠍座","射手座","山羊座","水瓶座","魚座"
]

def today_zodiac_index() -> int:
    return datetime.now().timetuple().tm_yday % 12

SYSTEM_PROMPT = """あなたは動画のナレーション脚本を書く専門家です。

【フィールドごとのルール】
narrationフィールド：
- ひらがなとカタカナのみ（漢字は一切使わない）
- 話し言葉で書く。書き言葉は禁止
- 一文を短くする（20文字以内）
- 句読点（。、）を多めに入れてゆっくり読めるリズムにする
- 読み上げると約70秒になる340〜360文字で書く

captionsフィールド：
- 漢字・ひらがな・カタカナ何でもOK
- 画面に表示する字幕なので読みやすい表記にする
- 1フレーズ15文字以内

【共通ルール】
- テーマを1つに絞る。色々詰め込まない
- スピリチュアル用語（宇宙・引き寄せ・魂・波動）は絶対に使わない

【ナレーションの流れ】
①共感（あなたもこんな気持ちでは？）
②寄り添い（それでいいんだよ）
③そっと背中を押す（一歩だけ踏み出してみて）

必ずJSON形式のみで返答する"""


def generate_script(content_type: str, performance_data: dict = None) -> dict:
    today = datetime.now()
    date_str = today.strftime("%m月%d日")
    idx = today_zodiac_index()
    zodiac_hira = ZODIAC_SIGNS[idx]
    zodiac_kanji = ZODIAC_KANJI[idx]

    prompts = {

        "horoscope": f"""今日（{date_str}）の{zodiac_kanji}の運勢ナレーションを作成。

テーマ：{zodiac_kanji}の今日の運勢を、{zodiac_kanji}の人だけに語りかける。
対象：{zodiac_kanji}生まれのひと、今日の運気が気になっているひと。

narrationのルール：
- ひらがなとカタカナのみ（漢字禁止）
- 「{zodiac_hira}のひとへ」から始める
- 今日の運気・気をつけること・ラッキーアクションの3つだけを話す
- 340〜360文字

以下のJSON形式のみで返答：
{{"hook":"{zodiac_kanji}への呼びかけ（ひらがなカタカナのみ・15文字以内）",
"narration":"ひらがなとカタカナのみ・340〜360文字・話し言葉",
"captions":["{zodiac_kanji}の運勢","今日の運気","きをつけること","ラッキーアクション","あなたへ","今日も大切に"],
"tiktok_caption":"今日の{zodiac_kanji}の運勢🔮 #{zodiac_kanji} #占い #運勢 #今日の運勢",
"youtube_title":"{zodiac_kanji}｜{date_str}の運勢",
"thumbnail_text":"{zodiac_kanji}の運勢"}}""",

        "love": f"""今日（{date_str}）の恋愛運ナレーションを作成。

テーマ：片思い中のひとへ、好きなひとにどう接すればいいか迷っているひとへ。
対象：片思いで悩んでいるひと1人だけに語りかける。恋人がいるひとは対象外。

narrationのルール：
- ひらがなとカタカナのみ（漢字禁止）
- 「すきなひとがいるんだね」など共感から始める
- 片思いの気持ち・勇気の出し方・自分を大切にすることの3つだけを話す
- 340〜360文字

以下のJSON形式のみで返答：
{{"hook":"片思い中のひとへの呼びかけ（ひらがなカタカナのみ・15文字以内）",
"narration":"ひらがなとカタカナのみ・340〜360文字・話し言葉",
"captions":["すきなひとがいるんだね","おもいきって","じぶんをすきに","ゆっくりでいい","あなたならできる","今日も笑顔で"],
"tiktok_caption":"片思い中のあなたへ💌 #恋愛 #片思い #恋愛運 #恋愛相談",
"youtube_title":"{date_str}｜片思い中のあなたへ",
"thumbnail_text":"片思いのあなたへ"}}""",

        "encourage": f"""今日の勇気づけナレーションを作成。

テーマ候補から今日の1つだけ選んで台本を作ること（複数テーマ混ぜ禁止）：
- 人間関係でつかれたひとへ
- じぶんを責めてばかりのひとへ
- やるきがでないひとへ
- がんばりすぎてつかれたひとへ
- くらべてばかりで苦しいひとへ

対象：選んだテーマの状況にいるひと1人だけに語りかける。

narrationのルール：
- ひらがなとカタカナのみ（漢字禁止）
- 「～なんだね、つかれたね」など深い共感から始める
- そのテーマ1つだけを丁寧に話す。他のテーマは混ぜない
- 340〜360文字

以下のJSON形式のみで返答：
{{"hook":"選んだテーマへの共感フレーズ（ひらがなカタカナのみ・15文字以内）",
"narration":"ひらがなとカタカナのみ・340〜360文字・話し言葉",
"captions":["つかれたね","それでいい","じぶんをせめないで","ゆっくりでいい","あなたはひとりじゃない","今日もよくがんばった"],
"tiktok_caption":"#メンタル #自分を大切に #生きづらい #共感",
"youtube_title":"選んだテーマ（30文字以内・漢字OK）",
"thumbnail_text":"サムネ文字（10文字以内・漢字OK）"}}"""
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1200,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompts[content_type]}]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    script = json.loads(raw)

    # 念のためnarrationから漢字が混入していたら除去ログ
    narration = script.get("narration", "")
    kanji_found = re.findall(r'[\u4e00-\u9fff]', narration)
    if kanji_found:
        import logging
        logging.getLogger(__name__).warning(
            f"narrationに漢字が混入: {''.join(set(kanji_found))}"
        )

    return script
