"""
uploader.py
TikTok Content Posting API と YouTube Data API v3 への自動投稿モジュール
"""

import os
import time
import logging
import requests
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

log = logging.getLogger(__name__)


# ── YouTube 投稿 ──────────────────────────────────────────────────────────

def _get_youtube_client():
    """YouTube API クライアントを OAuth2 認証で取得する"""
    creds = Credentials(
        token=os.environ["YOUTUBE_ACCESS_TOKEN"],
        refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
        client_id=os.environ["YOUTUBE_CLIENT_ID"],
        client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    # トークンが期限切れなら自動リフレッシュ
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        log.info("YouTube アクセストークンをリフレッシュしました")

    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload_youtube_short(
    video_path: str,
    title: str,
    tags: list[str],
    description: str = "毎日更新中✨ チャンネル登録でラッキーが届く🔮",
) -> str:
    """
    YouTube Shorts（縦型60秒以内）として動画を投稿する。

    #Shorts タグを title に付与することで Shorts フィードに表示される。
    返り値: YouTube video ID
    """
    youtube = _get_youtube_client()

    # Shorts として認識されるために #Shorts を title に付与
    full_title = f"{title} #Shorts"[:100]  # タイトル上限100文字

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": full_title,
                "description": description,
                "tags": tags + ["Shorts", "占い", "スピリチュアル", "タロット"],
                "categoryId": "22",          # People & Blogs
                "defaultLanguage": "ja",
                "defaultAudioLanguage": "ja",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024 * 1024 * 5,  # 5MB チャンク
        ),
    )

    log.info(f"YouTube アップロード開始: {Path(video_path).name}")
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            log.info(f"  YouTube アップロード: {pct}%")

    video_id = response["id"]
    log.info(f"YouTube 投稿完了: https://youtube.com/shorts/{video_id}")
    return video_id


def upload_youtube_long(
    video_path: str,
    title: str,
    tags: list[str],
    description: str = "チャンネル登録お願いします🔔",
) -> str:
    """
    YouTube 通常動画（長尺）として投稿する。
    タロット占いの「選んでね→結果」2部構成など長尺コンテンツ用。
    """
    youtube = _get_youtube_client()

    request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title[:100],
                "description": description,
                "tags": tags + ["占い", "スピリチュアル", "タロット占い", "星座"],
                "categoryId": "22",
                "defaultLanguage": "ja",
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        },
        media_body=MediaFileUpload(
            video_path, mimetype="video/mp4", resumable=True
        ),
    )

    log.info(f"YouTube 長尺アップロード開始: {Path(video_path).name}")
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    log.info(f"YouTube 長尺投稿完了: https://youtube.com/watch?v={video_id}")
    return video_id


# ── TikTok 投稿 ───────────────────────────────────────────────────────────

TIKTOK_BASE = "https://open.tiktokapis.com/v2"


def upload_tiktok(video_path: str, caption: str) -> dict:
    """
    TikTok Content Posting API（v2）で動画を投稿する。

    フロー:
      1. /post/publish/video/init/  → upload_url, publish_id を取得
      2. PUT upload_url             → 動画バイナリをアップロード
      3. /post/publish/status/fetch/ → 公開完了を確認（ポーリング）

    返り値: {"publish_id": str, "status": str}
    """
    token      = os.environ["TIKTOK_ACCESS_TOKEN"]
    video_size = Path(video_path).stat().st_size
    headers    = {
        "Authorization": f"Bearer {token}",
        "Content-Type":  "application/json; charset=UTF-8",
    }

    # Step 1: 初期化
    log.info("TikTok: 投稿初期化...")
    init_resp = requests.post(
        f"{TIKTOK_BASE}/post/publish/video/init/",
        headers=headers,
        json={
            "post_info": {
                "title":                caption[:2200],   # TikTok上限
                "privacy_level":        "PUBLIC_TO_EVERYONE",
                "disable_duet":         False,
                "disable_comment":      False,
                "disable_stitch":       False,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source":             "FILE_UPLOAD",
                "video_size":         video_size,
                "chunk_size":         video_size,        # 1チャンクで送信
                "total_chunk_count":  1,
            },
        },
        timeout=30,
    )
    init_resp.raise_for_status()
    data       = init_resp.json()["data"]
    upload_url = data["upload_url"]
    publish_id = data["publish_id"]
    log.info(f"TikTok: publish_id={publish_id}")

    # Step 2: 動画アップロード
    log.info(f"TikTok: 動画バイナリをアップロード中 ({video_size // 1024} KB)...")
    with open(video_path, "rb") as f:
        up_resp = requests.put(
            upload_url,
            data=f.read(),
            headers={
                "Content-Type":   "video/mp4",
                "Content-Range":  f"bytes 0-{video_size - 1}/{video_size}",
            },
            timeout=120,
        )
    up_resp.raise_for_status()

    # Step 3: 公開完了まで待機（最大60秒）
    log.info("TikTok: 公開処理を待機中...")
    for _ in range(12):
        time.sleep(5)
        status_resp = requests.post(
            f"{TIKTOK_BASE}/post/publish/status/fetch/",
            headers=headers,
            json={"publish_id": publish_id},
            timeout=15,
        )
        status_data = status_resp.json().get("data", {})
        status      = status_data.get("status", "PROCESSING")
        log.info(f"  TikTok ステータス: {status}")
        if status == "PUBLISH_COMPLETE":
            log.info("TikTok 投稿完了 ✅")
            break
        if status in ("FAILED", "SPAM_RISK_TOO_MANY_POSTS"):
            raise RuntimeError(f"TikTok 投稿失敗: {status_data}")

    return {"publish_id": publish_id, "status": status}
