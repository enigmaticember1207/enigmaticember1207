"""
audio_generator.py
ElevenLabs で音声を生成し、FFmpeg で背景映像・字幕・BGM と合成する
"""

import os
import subprocess
import random
import requests
import logging
from pathlib import Path

log = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# ── 日本語ボイス設定（ランダムで切り替え）──────────────────────────────
VOICE_IDS = [
    "RBnMinrYKeccY3vaUxlZ",  # Sakura
    "lhTvHflPVOqgSWyuWQry",  # Hana
]

BGM_DIR = Path("assets/bgm")


# ── 音声生成 ─────────────────────────────────────────────────────────────

def generate_audio(text: str, output_path: str) -> str:
    voice_id = random.choice(VOICE_IDS)
    log.info(f"使用ボイス: {'Sakura' if voice_id == VOICE_IDS[0] else 'Hana'}")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.80,
            "style": 0.30,
            "use_speaker_boost": True,
        },
    }

    log.info(f"ElevenLabs: テキスト {len(text)} 文字 → {output_path}")
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    log.info(f"音声生成完了: {Path(output_path).stat().st_size // 1024} KB")
    return output_path


# ── 字幕ファイル生成 ──────────────────────────────────────────────────────

def generate_srt(captions: list[str], seconds_per_caption: float = 4.0) -> str:
    srt = ""
    for i, caption in enumerate(captions, 1):
        start_sec = (i - 1) * seconds_per_caption
        end_sec   = i * seconds_per_caption
        start = _fmt_time(start_sec)
        end   = _fmt_time(end_sec)
        srt += f"{i}\n{start} --> {end}\n{caption}\n\n"
    return srt


def _fmt_time(seconds: float) -> str:
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ── BGM 選択 ─────────────────────────────────────────────────────────────

def pick_bgm(content_type: str) -> str | None:
    patterns = {
        "horoscope":         "star*.mp3",
        "tarot":             "tarot*.mp3",
        "spiritual_message": "mystic*.mp3",
    }
    pattern    = patterns.get(content_type, "mystic*.mp3")
    candidates = list(BGM_DIR.glob(pattern))
    if not candidates:
        candidates = list(BGM_DIR.glob("*.mp3"))
    if not candidates:
        log.warning("BGM ファイルが見つかりません（BGMなしで合成します）")
        return None
    return str(random.choice(candidates))


# ── FFmpeg 動画合成 ───────────────────────────────────────────────────────

def compose_video(
    audio_path: str,
    bg_video_path: str,
    captions: list[str],
    output_path: str,
    content_type: str = "spiritual_message",
) -> str:
    # 字幕 SRT を一時ファイルに保存
    srt_content = generate_srt(captions)
    srt_path = output_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    bgm_path = pick_bgm(content_type)

    # 日本語フォントパス（GitHub Actions Ubuntu環境）
    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        # フォールバック
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    subtitle_style = (
        f"FontName=Noto Sans CJK JP,"
        "FontSize=24,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=3,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=100"
    )

    inputs = ["-i", bg_video_path, "-i", audio_path]
    if bgm_path:
        inputs += ["-i", bgm_path]

    # SRTパスのエスケープ（FFmpeg用）
    srt_escaped = srt_path.replace("'", "\\'").replace(":", "\\:")

    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles='{srt_escaped}':force_style='{subtitle_style}'"
    )

    if bgm_path:
        audio_filter = "[1:a]volume=1.0[narr];[2:a]volume=0.25[bgm];[narr][bgm]amix=inputs=2:duration=shortest[aout]"
        audio_args = ["-filter_complex", audio_filter, "-map", "0:v", "-map", "[aout]"]
    else:
        audio_args = ["-map", "0:v", "-map", "1:a"]

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + ["-vf", video_filter]
        + audio_args
        + [
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            "-movflags", "+faststart",
            output_path,
        ]
    )

    log.info(f"FFmpeg 動画合成開始: {output_path}")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error(f"FFmpeg エラー:\n{result.stderr}")
        raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")

    size_mb = Path(output_path).stat().st_size / 1_048_576
    log.info(f"動画合成完了: {size_mb:.1f} MB → {output_path}")

    Path(srt_path).unlink(missing_ok=True)
    return output_path
