"""
script_generator.py
Claude APIを使って完全オリジナルの台本を自動生成する
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
- 完全オリジナルの台本のみを生成する（他コンテンツの模倣・引用は一切しない）
- 視聴者の心に深く刺さる言葉を選ぶ
- TikTok/YouTube Shortsでバズりやすい構成にする
- 冒頭3秒で視聴者を引き込む「フック」を必ず入れる
- 必ずJSON形式のみで返答する（前置きや説明文は不要）"""

def generate_script(content_type: str, performance_data: dict = None) -> dict:
    today = datetime.now()
    perf_hint = ""
    if performance_data and performance_data.get("top_theme"):
        perf_hint = f"\n参考：先週の高パフォーマンス要素「{performance_data['top_theme']}」"

    prompts = {
        "horoscope": f"""今日（{today.strftime('%m月%d日')}）の{random.choice(ZODIAC_SIGNS)}の運勢動画台本を作成。{perf_hint}

60秒縦型動画（TikTok/Shorts）。以下のJSON形式のみで返答：
{{"hook":"冒頭3秒の強い引き（例：今日あなたに起きること、知っておいて）",
"narration":"ナレーション全文150文字程度",
"captions":["字幕フレーズ1","字幕フレーズ2","字幕フレーズ3","字幕フレーズ4"],
"tiktok_caption":"TikTokキャプション＋ハッシュタグ（#占い #星座 等）",
"youtube_title":"YouTubeタイトル（30文字以内）",
"thumbnail_text":"サムネイルの大きな文字（10文字以内）"}}""",

        "tarot": f"""今日のタロット占い動画台本を作成。{perf_hint}

30秒縦型動画、「選んでね→結果」2部構成。以下のJSON形式のみで返答：
{{"hook":"カード選択を促す冒頭（例：3枚の中からピンときたカードを選んで）",
"card_reveal":"カード公開の演出テキスト（ワクワク感を出す）",
"message":"選ばれたカードのメッセージ（80文字）",
"call_to_action":"コメント欄への問いかけ（例：あなたは何番を選んだ？）",
"tiktok_caption":"TikTokキャプション＋ハッシュタグ",
"youtube_title":"YouTubeタイトル（30文字以内）",
"thumbnail_text":"サムネイルテキスト（10文字以内）"}}""",

        "spiritual_message": f"""今日のスピリチュアルメッセージ動画台本を作成。{perf_hint}

45秒縦型動画、保存・シェア率が高い普遍的なメッセージ。以下のJSON形式のみで返答：
{{"hook":"最初の一言（例：今これを見たのは偶然じゃない）",
"narration":"メインメッセージ120文字。宇宙・魂・引き寄せのテーマ",
"captions":["字幕1","字幕2","字幕3"],
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
    # JSONブロックの場合は中身だけ抽出
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)
