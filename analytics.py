"""
analytics.py
投稿パフォーマンスを JSON ファイルで管理し、
高再生数コンテンツの特徴を抽出して次の台本生成にフィードバックする
"""

import json
import os
import logging
import requests
from datetime import datetime, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

STATS_FILE = Path("performance_data.json")


# ── データの読み書き ──────────────────────────────────────────────────────

def load_stats() -> dict:
    if STATS_FILE.exists():
        return json.loads(STATS_FILE.read_text(encoding="utf-8"))
    return {"videos": [], "last_updated": None}


def save_stats(data: dict):
    data["last_updated"] = datetime.now().isoformat()
    STATS_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ── 投稿データを記録 ──────────────────────────────────────────────────────

def save_performance(
    video_id: str,
    platform: str,
    content_type: str,
    script: dict,
):
    """投稿した動画のメタデータを記録する"""
    data = load_stats()
    data["videos"].append({
        "video_id":       video_id,
        "platform":       platform,
        "content_type":   content_type,
        "hook":           script.get("hook", ""),
        "thumbnail_text": script.get("thumbnail_text", ""),
        "youtube_title":  script.get("youtube_title", ""),
        "posted_at":      datetime.now().isoformat(),
        "views":          0,
        "likes":          0,
        "shares":         0,
        "comments":       0,
        "engagement":     0.0,
    })
    save_stats(data)
    log.info(f"パフォーマンスデータ記録: {platform} / {video_id}")


# ── 再生数を API から取得して更新 ─────────────────────────────────────────

def fetch_and_update_stats():
    """
    前日以前に投稿した動画の再生数を各 API から取得して更新する。
    GitHub Actions から毎日 pipeline.py 実行前に呼び出す。
    """
    data      = load_stats()
    yesterday = datetime.now() - timedelta(days=1)

    for video in data["videos"]:
        # 前日以前かつ再生数が未取得の動画のみ更新
        posted = datetime.fromisoformat(video["posted_at"])
        if posted > yesterday or (video["views"] > 0):
            continue

        if video["platform"] == "tiktok":
            _update_tiktok_stats(video)
        elif video["platform"] == "youtube":
            _update_youtube_stats(video)

    save_stats(data)
    log.info("パフォーマンスデータ更新完了")


def _update_tiktok_stats(video: dict):
    token = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
    if not token:
        return
    try:
        resp = requests.post(
            "https://open.tiktokapis.com/v2/video/query/",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={
                "filters": {"video_ids": [video["video_id"]]},
                "fields":  ["view_count", "like_count",
                            "share_count", "comment_count"],
            },
            timeout=15,
        ).json()
        v = resp.get("data", {}).get("videos", [{}])[0]
        video["views"]      = v.get("view_count", 0)
        video["likes"]      = v.get("like_count", 0)
        video["shares"]     = v.get("share_count", 0)
        video["comments"]   = v.get("comment_count", 0)
        views = max(video["views"], 1)
        video["engagement"] = round(
            (video["likes"] + video["shares"] + video["comments"]) / views, 4
        )
    except Exception as e:
        log.warning(f"TikTok 統計取得エラー ({video['video_id']}): {e}")


def _update_youtube_stats(video: dict):
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        return
    try:
        resp = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part":  "statistics",
                "id":    video["video_id"],
                "key":   api_key,
            },
            timeout=15,
        ).json()
        stats = resp.get("items", [{}])[0].get("statistics", {})
        video["views"]    = int(stats.get("viewCount",    0))
        video["likes"]    = int(stats.get("likeCount",    0))
        video["comments"] = int(stats.get("commentCount", 0))
        views = max(video["views"], 1)
        video["engagement"] = round(
            (video["likes"] + video["comments"]) / views, 4
        )
    except Exception as e:
        log.warning(f"YouTube 統計取得エラー ({video['video_id']}): {e}")


# ── インサイト抽出 ────────────────────────────────────────────────────────

def get_performance_insights() -> dict:
    """
    直近30本の中から高パフォーマンスな動画の特徴を抽出し、
    次の台本生成プロンプトに渡す辞書を返す。
    """
    data   = load_stats()
    videos = [v for v in data["videos"] if v["views"] > 0]

    if len(videos) < 3:
        return {}   # データ不足

    # 再生数順にソート
    sorted_vids = sorted(videos, key=lambda x: x["views"], reverse=True)
    top          = sorted_vids[:5]
    all_avg      = sum(v["views"] for v in videos) / len(videos)

    # 上位コンテンツタイプの集計
    type_counts = {}
    for v in top:
        t = v["content_type"]
        type_counts[t] = type_counts.get(t, 0) + 1
    best_type = max(type_counts, key=type_counts.get)

    # エンゲージメント率の高いコンテンツタイプ
    type_eng = {}
    type_cnt = {}
    for v in videos:
        t = v["content_type"]
        type_eng[t] = type_eng.get(t, 0) + v["engagement"]
        type_cnt[t] = type_cnt.get(t, 0) + 1
    best_eng_type = max(type_eng, key=lambda t: type_eng[t] / type_cnt[t])

    top_views_avg = sum(v["views"] for v in top) // len(top)

    return {
        "top_theme": (
            f"{best_type}が好調（上位5本平均 {top_views_avg:,} 再生、"
            f"全体平均 {int(all_avg):,} 再生）"
        ),
        "best_content_type":     best_type,
        "best_engagement_type":  best_eng_type,
        "avg_top_views":         top_views_avg,
        "overall_avg_views":     int(all_avg),
        "total_videos":          len(videos),
    }
