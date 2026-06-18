"""
script_generator.py
Claude APIを使って完全オリジナルの台本を自動生成する
65秒動画（約300文字のナレーション）に対応
"""

import anthropic
import json
import random
from datetime import datetime

client = anthropic.Anthropic()

CONTENT_TYPES = ["horoscope", "tarot", "spiritual_message"]

ZODIAC_SIGNS = [
    "牡羊座","牡牛座","双子座","蟹座","獅子座","乙女座",
    "天秤座","蠍座","射手座","山羊座","水瓶座","魚座"
]

SYSTEM_PROMPT = """あなたは占い・スピリチュアルコンテンツの専門クリエイターです。
以下のルールを厳守してください：
- 完全オリジナルの台本のみを生成する
- 視聴者の心に深く刺さる言葉を選ぶ
- TikTok/YouTube Shortsでバズりやすい構成にする
- 冒頭3秒で視聴者を引き込む「フック」を必ず入れる
- narrationは読み上げると約65秒になる300〜320文字で書く
- 句読点（。、）を適切に入れて自然な読み上げにする
- 必ずJSON形式のみで返答する（前置きや説明文は不要）"""


def generate_script(content_type: str, performance_data: dict = None) -> dict:
    today = datetime.now()
    perf_hint = ""
    if performance_data and performance_data.get("top_theme"):
        perf_hint = f"\n参考：先週の高パフォーマンス要素「{performance_data['top_theme']}」"

    prompts = {
        "horoscope": f"""今日（{today.strftime('%m月%d日')}）の{random.choice(ZODIAC_SIGNS)}の運勢動画台本を作成。{perf_hint}

65秒縦型動画（TikTok/Shorts）。narrationは読み上げ約65秒・300〜320文字で書くこと。
以下のJSON形式のみで返答：
{{"hook":"冒頭3秒の強い引き（例：今日あなたに起きること、知っておいて）",
"narration":"ナレーション全文300〜320文字。今日の運勢・ラッキーアクション・メッセージを含む。句読点を適切に入れて自然な読み上げにする",
"captions":["字幕フレーズ1（15文字以内）","字幕フレーズ2","字幕フレーズ3","字幕フレーズ4","字幕フレーズ5","字幕フレーズ6"],
"tiktok_caption":"TikTokキャプション＋ハッシュタグ（#占い #星座 等）",
"youtube_title":"YouTubeタイトル（30文字以内）",
"thumbnail_text":"サムネイルの大きな文字（10文字以内）"}}""",

        "tarot": f"""今日のタロット占い動画台本を作成。{perf_hint}

65秒縦型動画、「カード選択→結果発表」構成。narrationは読み上げ約65秒・300〜320文字で書くこと。
以下のJSON形式のみで返答：
{{"hook":"カード選択を促す冒頭（例：3枚の中からピンときたカードを選んで）",
"narration":"ナレーション全文300〜320文字。カード選択の誘導・カード公開の演出・メッセージを含む。句読点を適切に入れて自然な読み上げにする",
"captions":["字幕1（15文字以内）","字幕2","字幕3","字幕4","字幕5","字幕6"],
"call_to_action":"コメント欄への問いかけ（例：あなたは何番を選んだ？）",
"tiktok_caption":"TikTokキャプション＋ハッシュタグ",
"youtube_title":"YouTubeタイトル（30文字以内）",
"thumbnail_text":"サムネイルテキスト（10文字以内）"}}""",

        "spiritual_message": f"""今日のスピリチュアルメッセージ動画台本を作成。{perf_hint}

65秒縦型動画、保存・シェア率が高い普遍的なメッセージ。narrationは読み上げ約65秒・300〜320文字で書くこと。
以下のJSON形式のみで返答：
{{"hook":"最初の一言（例：今これを見たのは偶然じゃない）",
"narration":"ナレーション全文300〜320文字。宇宙・魂・引き寄せのテーマ。保存したくなるメッセージ。句読点を適切に入れて自然な読み上げにする",
"captions":["字幕1（15文字以内）","字幕2","字幕3","字幕4","字幕5","字幕6"],
"closing":"締めの言葉（保存を促す一言）",
"tiktok_caption":"TikTokキャプション＋ハッシュタグ",
"youtube_title":"YouTubeタイトル（30文字以内）",
"thumbnail_text":"サムネイルテキスト（10文字以内）"}}"""
    }

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompts[content_type]}]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
