"""
script_generator.py
Claude APIを使って完全オリジナルの台本を自動生成する

3本構成：
  horoscope  - 今日の運勢（12星座ローテーション）
  love       - 今日の恋愛運
  encourage  - 静かに寄り添う勇気づけ
"""

import anthropic
import json
import random
from datetime import datetime

client = anthropic.Anthropic()

CONTENT_TYPES = ["horoscope", "love", "encourage"]

ZODIAC_SIGNS = [
    "牡羊座","牡牛座","双子座","蟹座","獅子座","乙女座",
    "天秤座","蠍座","射手座","山羊座","水瓶座","魚座"
]

# 毎日違う星座を使うため、今日の日付から決定論的に選ぶ
def today_zodiac() -> str:
    day_of_year = datetime.now().timetuple().tm_yday
    return ZODIAC_SIGNS[day_of_year % 12]

SYSTEM_PROMPT = """あなたは心に寄り添う動画コンテンツのナレーター兼脚本家です。

【視聴者像】
- 人間関係に傷ついている人
- やる気が出ない・疲れている人
- 恋愛や人間関係に悩んでいる人
- 自分を責めてしまいがちな人

【ナレーションのスタイル】
- ゆっくり、静かに語りかける独り語り形式
- 「あなた」に直接話しかける温かいトーン
- スピリチュアル用語（宇宙・引き寄せ・魂・波動など）は絶対に使わない
- 難しい言葉を使わない、日常的な言葉で
- 共感してから、そっと背中を押す流れ
- 読み上げると約65秒になる300〜320文字
- 句読点（。、）を適切に入れてゆっくり読めるリズムにする

【禁止事項】
- スピリチュアル・オカルト・宇宙・魂・引き寄せ・波動・カードなどの表現
- 根拠のない断言（「必ずうまくいく」など）
- 説教くさい言い回し
- タイトルと内容がズレること

必ずJSON形式のみで返答する（前置きや説明文は不要）"""


def generate_script(content_type: str, performance_data: dict = None) -> dict:
    today = datetime.now()
    date_str = today.strftime("%m月%d日")
    zodiac = today_zodiac()

    perf_hint = ""
    if performance_data and performance_data.get("top_theme"):
        perf_hint = f"\n参考：先週の高パフォーマンス要素「{performance_data['top_theme']}」"

    prompts = {

        # ── 今日の運勢（星座ごと）────────────────────────────────────────
        "horoscope": f"""{date_str}の{zodiac}の運勢動画台本を作成。{perf_hint}

タイトル：「{zodiac}｜{date_str}の運勢」
内容：今日の{zodiac}の運勢・気をつけること・ラッキーアクション。
占い的な内容でOKだが、スピリチュアル用語は使わない。
narrationは読み上げ約65秒・300〜320文字。ゆっくり語りかける独り語り形式。

以下のJSON形式のみで返答：
{{"hook":"冒頭の一言（{zodiac}に向けた共感フレーズ、20文字以内）",
"narration":"ナレーション全文300〜320文字。今日の運勢・恋愛・仕事・ラッキーアクションを含む。温かく語りかける口調。",
"captions":["字幕1（15文字以内）","字幕2","字幕3","字幕4","字幕5","字幕6"],
"tiktok_caption":"TikTokキャプション＋ハッシュタグ（#占い #{zodiac} #運勢 等）",
"youtube_title":"{zodiac}｜{date_str}の運勢",
"thumbnail_text":"{zodiac}の運勢"}}""",

        # ── 今日の恋愛運 ──────────────────────────────────────────────────
        "love": f"""{date_str}の恋愛運動画台本を作成。{perf_hint}

タイトル：「{date_str}の恋愛運｜今日のあなたへ」
内容：今日の恋愛傾向・恋愛でのアドバイス・片思い中や恋人がいる人への言葉。
全星座共通の内容でOK。
narrationは読み上げ約65秒・300〜320文字。ゆっくり語りかける独り語り形式。

以下のJSON形式のみで返答：
{{"hook":"冒頭の一言（恋愛に関する共感フレーズ、20文字以内）",
"narration":"ナレーション全文300〜320文字。今日の恋愛傾向・片思い中の人・パートナーがいる人・恋愛に疲れた人それぞれへの言葉を含む。温かく語りかける口調。スピリチュアル用語禁止。",
"captions":["字幕1（15文字以内）","字幕2","字幕3","字幕4","字幕5","字幕6"],
"tiktok_caption":"TikTokキャプション＋ハッシュタグ（#恋愛 #恋愛運 #片思い 等）",
"youtube_title":"{date_str}の恋愛運｜今日のあなたへ",
"thumbnail_text":"今日の恋愛運"}}""",

        # ── 勇気づけ（静かに寄り添う）────────────────────────────────────
        "encourage": f"""今日の勇気づけメッセージ動画台本を作成。{perf_hint}

テーマ候補からランダムに1つ選んで台本を作ること：
- 人間関係で傷ついているあなたへ
- 自分を責めてばかりのあなたへ
- やる気が出ない日のあなたへ
- 頑張りすぎて疲れたあなたへ
- 誰にも言えない悩みを抱えているあなたへ
- もう少しだけ、自分を信じてみて
- 比べることをやめたら楽になった

タイトルは選んだテーマそのまま使うこと。
narrationは読み上げ約65秒・300〜320文字。ゆっくり静かに語りかける独り語り形式。

以下のJSON形式のみで返答：
{{"hook":"冒頭の一言（選んだテーマに沿った共感フレーズ、20文字以内）",
"narration":"ナレーション全文300〜320文字。選んだテーマに完全に沿った内容。共感→寄り添い→そっと背中を押す流れ。スピリチュアル用語絶対禁止。保存・シェアされやすい普遍的なメッセージ。",
"captions":["字幕1（テーマに沿った短いフレーズ・15文字以内）","字幕2","字幕3","字幕4","字幕5","字幕6"],
"closing":"締めの言葉（保存を促す一言、20文字以内）",
"tiktok_caption":"TikTokキャプション＋ハッシュタグ（#メンタル #自分を大切に 等）",
"youtube_title":"選んだテーマ（30文字以内）",
"thumbnail_text":"サムネイルテキスト（10文字以内）"}}"""
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
    return json.loads(raw)
