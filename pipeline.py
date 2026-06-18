"""
pipeline.py
Daily automated English content pipeline
Generates 3 videos: horoscope / love / encourage
"""

import os
import logging
from datetime import datetime
from pathlib import Path

from script_generator import generate_script, CONTENT_TYPES
from audio_generator  import generate_audio, compose_video
from uploader         import upload_youtube_short
from analytics        import save_performance, fetch_and_update_stats, get_performance_insights

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

BG_VIDEOS_DIR = Path("assets/bg_videos")
OUTPUT_DIR    = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

TIKTOK_ENABLED = bool(os.environ.get("TIKTOK_ACCESS_TOKEN", "").strip())


def pick_bg_video(content_type: str) -> str:
    pattern = {
        "horoscope": "star*.mp4",
        "love":      "nature*.mp4",
        "encourage": "mystic*.mp4",
    }.get(content_type, "*.mp4")

    videos = list(BG_VIDEOS_DIR.glob(pattern))
    if not videos:
        videos = list(BG_VIDEOS_DIR.glob("*.mp4"))
    if not videos:
        raise FileNotFoundError(
            f"No background video found in {BG_VIDEOS_DIR}"
        )
    import random
    return str(random.choice(videos))


def run_pipeline():
    log.info("=== Daily English Content Pipeline START ===")
    today = datetime.now().strftime("%Y%m%d")

    fetch_and_update_stats()
    insights = get_performance_insights()
    if insights:
        log.info(f"Insights: {insights['top_theme']}")

    results = []

    # 毎回必ず horoscope → love → encourage の順で1本ずつ生成
    for i, content_type in enumerate(CONTENT_TYPES):
        log.info(f"--- [{i+1}/3] {content_type} ---")

        try:
            # Step 1: Generate script
            log.info("Generating script with Claude...")
            script = generate_script(content_type, performance_data=insights)
            log.info(f"Hook: {script.get('hook', '')[:50]}...")

            # Step 2: Generate audio
            log.info("Generating audio with ElevenLabs...")
            narration = script.get("narration", "")
            audio_path = str(OUTPUT_DIR / f"{today}_{i}_{content_type}_audio.mp3")
            generate_audio(narration, audio_path)

            # Step 3: Compose video
            log.info("Composing video with FFmpeg...")
            bg_video   = pick_bg_video(content_type)
            video_path = str(OUTPUT_DIR / f"{today}_{i}_{content_type}.mp4")
            captions   = script.get("captions", [script.get("hook", ""), narration])
            compose_video(audio_path, bg_video, captions, video_path, content_type)

            # Step 4: Upload to YouTube
            log.info("Uploading to YouTube Shorts...")
            yt_title = script.get("youtube_title", f"{content_type} {today}")
            yt_tags  = ["horoscope", "spirituality", "selflove", "mentalhealth", "shorts"]
            yt_id    = upload_youtube_short(video_path, yt_title, yt_tags)
            log.info(f"YouTube uploaded: https://youtube.com/shorts/{yt_id}")
            save_performance(yt_id, "youtube", content_type, script)

            # Step 5: TikTok (if enabled)
            if TIKTOK_ENABLED:
                from uploader import upload_tiktok
                caption = script.get("tiktok_caption", narration[:150])
                tt = upload_tiktok(video_path, caption)
                save_performance(tt.get("publish_id", ""), "tiktok", content_type, script)
                log.info(f"TikTok uploaded: {tt.get('publish_id')}")
            else:
                log.info("TikTok skipped (token not set)")

            results.append({"type": content_type, "title": yt_title, "yt_id": yt_id})

        except Exception as e:
            log.error(f"[{content_type}] Error: {e}", exc_info=True)
            continue

    log.info("=== Pipeline COMPLETE ===")
    log.info(f"Success: {len(results)}/3")
    for r in results:
        log.info(f"  [{r['type']}] {r['title']} → https://youtube.com/shorts/{r['yt_id']}")

    return results


if __name__ == "__main__":
    run_pipeline()
