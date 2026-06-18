"""
spiritual-content-bot / pipeline.py
毎日自動でスピリチュアルコンテンツを生成・投稿するメインパイプライン
GitHub Actions の cron から呼び出される
"""

import os
import random
import logging
import tempfile
from datetime import datetime
from pathlib import Path

# 各モジュールをインポート（後述のファイルを同ディレクトリに配置）
from script_generator import generate_script, CONTENT_TYPES
from audio_generator  import generate_audio, compose_video
from uploader         import upload_tiktok, upload_youtube_short
from analytics        import (save_performance, fetch_and_update_stats,
                               get_performance_insights)

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 設定
# ──────────────────────────────────────────────
BG_VIDEOS_DIR = Path("assets/bg_videos")   # Runway/Pixabay から事前DLした背景映像
OUTPUT_DIR    = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# 1日に生成するコンテンツ数（予算・API上限に応じて調整）
DAILY_CONTENT_COUNT = 3


def select_content_type(insights: dict) -> str:
    """
    分析データがあれば高パフォーマンスなタイプを優先しつつ、
    ランダム性も保ってマンネリを防ぐ
    """
    if insights.get("best_content_type") and random.random() < 0.6:
        return insights["best_content_type"]
    return random.choice(CONTENT_TYPES)


def pick_bg_video(content_type: str) -> str:
    """コンテンツタイプに合った背景映像を選ぶ"""
    pattern = {
        "horoscope":         "star*.mp4",
        "tarot":             "mystic*.mp4",
        "spiritual_message": "nature*.mp4",
    }.get(content_type, "*.mp4")

    videos = list(BG_VIDEOS_DIR.glob(pattern))
    if not videos:
        videos = list(BG_VIDEOS_DIR.glob("*.mp4"))
    if not videos:
        raise FileNotFoundError(
            f"背景映像が見つかりません: {BG_VIDEOS_DIR}\n"
            "assets/bg_videos/ に mp4 ファイルを配置してください。"
        )
    return str(random.choice(videos))


def run_pipeline():
    log.info("=== 毎日コンテンツパイプライン開始 ===")
    today = datetime.now().strftime("%Y%m%d")

    # Step 0: 前日の分析データを取得して台本生成にフィードバック
    log.info("前日のパフォーマンスデータを更新中...")
    fetch_and_update_stats()
    insights = get_performance_insights()
    if insights:
        log.info(f"インサイト: {insights['top_theme']}")

    results = []

    for i in range(DAILY_CONTENT_COUNT):
        log.info(f"--- コンテンツ {i+1}/{DAILY_CONTENT_COUNT} 生成開始 ---")

        try:
            # Step 1: コンテンツタイプを決定
            content_type = select_content_type(insights)
            log.info(f"タイプ: {content_type}")

            # Step 2: Claude API で台本生成
            log.info("Claude API で台本を生成中...")
            script = generate_script(content_type, performance_data=insights)
            log.info(f"台本フック: {script.get('hook', '')[:30]}...")

            # Step 3: ElevenLabs で音声生成
            log.info("ElevenLabs で音声を合成中...")
            narration_text = script.get("narration") or script.get("message", "")
            audio_path = str(OUTPUT_DIR / f"{today}_{i}_{content_type}_audio.mp3")
            generate_audio(narration_text, audio_path)

            # Step 4: FFmpeg で動画合成
            log.info("FFmpeg で動画を合成中...")
            bg_video   = pick_bg_video(content_type)
            video_path = str(OUTPUT_DIR / f"{today}_{i}_{content_type}.mp4")
            captions   = script.get("captions", [script.get("hook", ""), narration_text])
            compose_video(audio_path, bg_video, captions, video_path)

            # Step 5: TikTok に投稿
            log.info("TikTok にアップロード中...")
            tiktok_caption = script.get("tiktok_caption", narration_text[:150])
            tt_result = upload_tiktok(video_path, tiktok_caption)
            log.info(f"TikTok 投稿完了: publish_id={tt_result.get('publish_id')}")

            # Step 6: YouTube Shorts に投稿
            log.info("YouTube Shorts にアップロード中...")
            yt_title = script.get("youtube_title", f"今日の{content_type} {today}")
            yt_tags  = ["占い", "スピリチュアル", "タロット", "星座運勢", "癒し"]
            yt_id    = upload_youtube_short(video_path, yt_title, yt_tags)
            log.info(f"YouTube 投稿完了: video_id={yt_id}")

            # Step 7: パフォーマンスデータを記録
            save_performance(yt_id, "youtube", content_type, script)
            save_performance(tt_result.get("publish_id", ""), "tiktok", content_type, script)

            results.append({
                "content_type": content_type,
                "tiktok": tt_result,
                "youtube_id": yt_id,
                "title": yt_title,
            })

        except Exception as e:
            log.error(f"コンテンツ {i+1} の生成中にエラー: {e}", exc_info=True)
            # 1本失敗しても続行
            continue

    log.info("=== パイプライン完了 ===")
    log.info(f"成功: {len(results)}/{DAILY_CONTENT_COUNT} 本")
    for r in results:
        log.info(f"  [{r['content_type']}] {r['title']}")

    return results


if __name__ == "__main__":
    run_pipeline()
