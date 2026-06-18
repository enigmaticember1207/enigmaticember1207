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

VOICE_IDS = [
    "GxhGYQesaQaYKePCZDEC",
    "T7yYq3WpB94yAuOXraRi",
]

BGM_DIR = Path("assets/bgm")


# ── 音声生成 ─────────────────────────────────────────────────────────────

def generate_audio(text: str, output_path: str) -> str:
    voice_id = random.choice(VOICE_IDS)
    log.info(f"使用ボイス: {voice_id}")

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {
            "stability": 0.75,          # 高め = 落ち着いた安定した声
            "similarity_boost": 0.80,
            "style": 0.10,              # 低め = 抑えた自然なトーン
            "use_speaker_boost": True,
            "speed": 1.0,               # 等速
        },
    }

    log.info(f"ElevenLabs: テキスト {len(text)} 文字 → {output_path}")
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(resp.content)

    log.info(f"音声生成完了: {Path(output_path).stat().st_size // 1024} KB")
    return output_path


# ── 音声の長さを取得 ──────────────────────────────────────────────────────

def get_audio_duration(audio_path: str) -> float:
    """ffprobe で音声ファイルの長さ（秒）を取得する"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        capture_output=True, text=True
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        log.warning("音声長の取得に失敗しました。65秒と仮定します。")
        return 65.0


# ── 字幕ファイル生成（音声長に合わせて均等割り）────────────────────────

def generate_srt(captions: list[str], total_duration: float) -> str:
    """
    音声の実際の長さに合わせて字幕を均等割りする。
    """
    n = len(captions)
    seconds_per_caption = total_duration / n
    srt = ""
    for i, caption in enumerate(captions, 1):
        start_sec = (i - 1) * seconds_per_caption
        end_sec   = i * seconds_per_caption
        srt += f"{i}\n{_fmt_time(start_sec)} --> {_fmt_time(end_sec)}\n{caption}\n\n"
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
        "horoscope": "star*.mp3",
        "love":      "mystic*.mp3",
        "encourage": "mystic*.mp3",
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
    # 音声の実際の長さを取得
    audio_duration = get_audio_duration(audio_path)
    log.info(f"音声長: {audio_duration:.1f} 秒")

    # 末尾に2秒の無音パディングを追加（AACエンコード遅延で末尾が切れるのを防ぐ）
    TAIL_PADDING = 3.0
    padded_audio_path = audio_path.replace(".mp3", "_padded.mp3")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", audio_path,
        "-af", f"apad=pad_dur={TAIL_PADDING}",
        "-c:a", "libmp3lame", "-q:a", "2",
        padded_audio_path,
    ], capture_output=True)
    total_duration = audio_duration + TAIL_PADDING

    # 音声長に合わせた字幕を生成（パディング前の実際の音声長で計算）
    srt_content = generate_srt(captions, audio_duration)
    srt_path = output_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    bgm_path = pick_bgm(content_type)

    # 日本語フォントパス
    font_path = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
    if not Path(font_path).exists():
        font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    subtitle_style = (
        "FontName=Noto Sans CJK JP,"
        "FontSize=24,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "Outline=3,"
        "Shadow=1,"
        "Alignment=2,"
        "MarginV=100"
    )

    srt_escaped = srt_path.replace("'", "\\'").replace(":", "\\:")

    # 背景映像をループ再生して音声長に合わせる
    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles='{srt_escaped}':force_style='{subtitle_style}'"
    )

    inputs = [
        "-stream_loop", "-1",   # 背景映像を無限ループ
        "-i", bg_video_path,
        "-i", padded_audio_path,  # パディング済み音声を使用
    ]
    if bgm_path:
        inputs += ["-i", bgm_path]

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
            "-t", str(total_duration),  # パディング込みの長さで動画を切る
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "28",           # 画質を少し下げてサイズ削減
            "-vb", "1000k",         # 映像ビットレート上限1Mbps
            "-c:a", "aac",
            "-b:a", "96k",          # 音声ビットレート削減
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
    Path(padded_audio_path).unlink(missing_ok=True)
    return output_path
