"""
audio_generator.py
ElevenLabs で音声を生成し、FFmpeg で背景映像・字幕・BGM と合成する
"""

import os
import subprocess
import tempfile
import requests
import logging
from pathlib import Path

log = logging.getLogger(__name__)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

# ── ElevenLabs ボイス設定 ──────────────────────────────────────────────────
# 占い・スピリチュアル向けに落ち着きと温かみのある女性ボイスを推奨
# 日本語対応ボイスID（ElevenLabsの "Multilingual v2" モデルで動作）
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # → ElevenLabsダッシュボードで日本語ボイスに変更推奨

BGM_DIR = Path("assets/bgm")   # 神秘的なBGM素材を配置するフォルダ


# ── 音声生成 ─────────────────────────────────────────────────────────────

def generate_audio(text: str, output_path: str) -> str:
    """
    ElevenLabs Text-to-Speech API でナレーション音声を生成する。

    Args:
        text:        ナレーション本文
        output_path: 保存先パス（.mp3）
    Returns:
        output_path
    """
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",   # 日本語対応モデル
        "voice_settings": {
            "stability": 0.50,          # 0=感情豊か / 1=安定
            "similarity_boost": 0.80,   # 元のボイスへの忠実度
            "style": 0.30,              # スタイル誇張（0=オフ）
            "use_speaker_boost": True,  # 音質向上
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
    """
    字幕リストから SRT 形式テキストを生成する。

    各キャプションを均等な時間で表示。
    """
    srt = ""
    for i, caption in enumerate(captions, 1):
        start_sec = (i - 1) * seconds_per_caption
        end_sec   = i * seconds_per_caption
        start = _fmt_time(start_sec)
        end   = _fmt_time(end_sec)
        srt += f"{i}\n{start} --> {end}\n{caption}\n\n"
    return srt


def _fmt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


# ── BGM 選択 ─────────────────────────────────────────────────────────────

def pick_bgm(content_type: str) -> str | None:
    """
    コンテンツタイプに合った BGM ファイルを返す。
    assets/bgm/ に以下の素材を配置しておくこと（著作権フリー素材推奨）:
      mystic_01.mp3, mystic_02.mp3  … 神秘的・瞑想系
      star_01.mp3                   … 宇宙・星座系
      tarot_01.mp3                  … タロット系
    """
    patterns = {
        "horoscope":         "star*.mp3",
        "tarot":             "tarot*.mp3",
        "spiritual_message": "mystic*.mp3",
    }
    pattern = patterns.get(content_type, "mystic*.mp3")
    candidates = list(BGM_DIR.glob(pattern))
    if not candidates:
        candidates = list(BGM_DIR.glob("*.mp3"))
    if not candidates:
        log.warning("BGM ファイルが見つかりません（BGMなしで合成します）")
        return None

    import random
    return str(random.choice(candidates))


# ── FFmpeg 動画合成 ───────────────────────────────────────────────────────

def compose_video(
    audio_path: str,
    bg_video_path: str,
    captions: list[str],
    output_path: str,
    content_type: str = "spiritual_message",
) -> str:
    """
    背景映像 + ナレーション音声 + BGM + 字幕 を FFmpeg で合成し、
    縦型（1080×1920）の TikTok/Shorts 対応動画を出力する。

    Args:
        audio_path:    ElevenLabs 生成音声（.mp3）
        bg_video_path: 背景映像（.mp4）
        captions:      字幕リスト
        output_path:   出力先（.mp4）
        content_type:  BGM 選択に使用
    Returns:
        output_path
    """
    # 字幕 SRT を一時ファイルに保存
    srt_content = generate_srt(captions)
    srt_path = output_path.replace(".mp4", ".srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    bgm_path = pick_bgm(content_type)

    # ── FFmpeg コマンド構築 ───────────────────────────────────────────
    # 入力: 背景映像 → ナレーション音声 → BGM（任意）
    # 映像: 縦型クロップ → 字幕焼き込み
    # 音声: ナレーション + BGM をミックス（BGMは -12dB 下げる）

    subtitle_style = (
        "FontName=Noto Sans CJK JP,"    # 日本語フォント（Ubuntu に要インストール）
        "FontSize=22,"
        "Bold=1,"
        "PrimaryColour=&H00FFFFFF,"     # 白文字
        "OutlineColour=&H00000000,"     # 黒縁取り
        "Outline=2,"
        "Alignment=2,"                  # 下部中央
        "MarginV=80"                    # 画面下端から 80px
    )

    inputs = [
        "-i", bg_video_path,
        "-i", audio_path,
    ]
    if bgm_path:
        inputs += ["-i", bgm_path]

    video_filter = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        f"subtitles='{srt_path}':force_style='{subtitle_style}'"
    )

    if bgm_path:
        # ナレーション + BGM（-12dB）をミックス
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
            "-crf", "23",           # 品質 (18=高品質, 28=低品質)
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",            # 最短ストリームで終了
            "-movflags", "+faststart",  # Web再生最適化
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

    # 一時 SRT ファイルを削除
    Path(srt_path).unlink(missing_ok=True)

    return output_path
