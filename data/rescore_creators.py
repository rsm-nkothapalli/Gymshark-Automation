"""
rescore_creators.py
-------------------
Re-score the existing creators in data/creators.csv using LLM-based holistic
scoring (USE_LLM_SCORING=True). Fetches fresh YouTube data (titles, transcripts,
comments) per creator, runs the same LLM pipeline used in the main collector,
and updates all scoring fields in-place.

Identity fields (name, handle, tier, date_added, channel_id, URLs) are preserved.

Checkpointed — safe to interrupt and re-run; already-scored creators are skipped.

Usage:
    uv run python data/rescore_creators.py
"""

import csv
import json
import os
import sys
import time
import importlib.util
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# ── Import reusable functions from the main collection pipeline ───────────────
_spec = importlib.util.spec_from_file_location(
    "collector",
    Path(__file__).parent / "collect_creators_gemin_2i.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

get_channel_stats = _mod.get_channel_stats
fetch_comments = _mod.fetch_comments
fetch_transcript = _mod.fetch_transcript
score_comments = _mod.score_comments
score_creator = _mod.score_creator
YOUTUBE_API_KEY = _mod.YOUTUBE_API_KEY
VIDEOS_PER_CREATOR = _mod.VIDEOS_PER_CREATOR
MAX_COMMENTS = _mod.MAX_COMMENTS

try:
    from googleapiclient.discovery import build
except ImportError:
    os.system("pip install google-api-python-client -q")
    from googleapiclient.discovery import build

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent
CSV_PATH = DATA_DIR / "creators.csv"
CKPT_PATH = DATA_DIR / "rescore_checkpoint.json"

# ── Fields to preserve exactly as-is ─────────────────────────────────────────
PRESERVE = {
    "rank",
    "creator_id",
    "name",
    "youtube_handle",
    "tier",
    "suggested_deal_type",
    "date_added",
    "source",
    "channel_id",
    "youtube_channel_url",
    "youtube_icon_url",
    "youtube_banner_url",
}


def load_checkpoint():
    if CKPT_PATH.exists():
        return json.loads(CKPT_PATH.read_text())
    return {}


def save_checkpoint(done: dict):
    CKPT_PATH.write_text(json.dumps(done, indent=2))


def get_recent_videos(youtube, channel_id: str, max_results: int = 4):
    """Return [(title, video_id, video_url)] for the most recent uploads."""
    try:
        resp = (
            youtube.search()
            .list(
                channelId=channel_id,
                part="snippet",
                order="date",
                type="video",
                maxResults=max_results,
            )
            .execute()
        )
        out = []
        for item in resp.get("items", []):
            vid_id = item["id"]["videoId"]
            title = item["snippet"]["title"]
            out.append((title, vid_id, f"https://www.youtube.com/watch?v={vid_id}"))
        return out
    except Exception as e:
        print(f"    Warning: Could not fetch videos: {e}")
        return []


def rescore_creator(youtube, row: dict) -> dict | None:
    """
    Fetch fresh YouTube data for one creator and return updated score fields.
    Returns None if channel stats cannot be fetched.
    """
    cid = row["channel_id"]
    name = row["name"]

    # Channel stats
    stats_map = get_channel_stats(youtube, [cid])
    stats = stats_map.get(cid, {})
    if not stats:
        print(f"    ✗ Channel stats unavailable — skipping")
        return None

    channel_title = stats.get("channel_title", name)

    # Recent videos
    videos = get_recent_videos(youtube, cid, max_results=VIDEOS_PER_CREATOR + 2)
    titles = [v[0] for v in videos]
    time.sleep(0.5)

    # Transcripts
    transcripts = []
    for i, (_, _vid_id, vid_url) in enumerate(videos[:VIDEOS_PER_CREATOR]):
        print(f"    → Transcript {i + 1}...")
        t = fetch_transcript(vid_url)
        transcripts.append(t)
        words = len(t.split()) if t else 0
        print(f"      {'✓ ' + str(words) + ' words' if t else '✗ unavailable'}")
        time.sleep(0.5)

    # Comments
    all_comments = []
    for i, (_, vid_id, _) in enumerate(videos[:VIDEOS_PER_CREATOR]):
        print(f"    → Comments video {i + 1}...")
        c = fetch_comments(youtube, vid_id, MAX_COMMENTS)
        all_comments.extend(c)
        print(f"      ✓ {len(c)} comments")
        time.sleep(0.3)

    comment_scores = score_comments(all_comments)

    # LLM holistic scoring
    print(f"    → LLM scoring...")
    scores = score_creator(transcripts, titles, channel_title, stats, comment_scores)

    return {
        # Channel stats (refreshed)
        "subscribers": stats.get("subscribers", row["subscribers"]),
        "total_views": stats.get("total_views", row["total_views"]),
        "video_count": stats.get("video_count", row["video_count"]),
        "country": stats.get("country", row["country"]),
        "estimated_er_pct": scores["estimated_er_pct"],
        # LLM-assigned taxonomy
        "niche": scores.get("niche", row["niche"]),
        "content_style": scores.get("content_style", row["content_style"]),
        "audience_tone": scores.get("audience_tone", row["audience_tone"]),
        # Scores
        "gymshark_brand_fit": scores["gymshark_brand_fit"],
        "authenticity_score": scores["authenticity_score"],
        "niche_score": scores["niche_score"],
        "engagement_score": scores["engagement_score"],
        # Reasoning
        "brand_fit_reasoning": scores["brand_fit_reasoning"],
        "authenticity_reasoning": scores["authenticity_reasoning"],
        "signals_authentic_pos": str(scores["signals_authentic_pos"]),
        "signals_authentic_neg": str(scores["signals_authentic_neg"]),
        # Safety & risk
        "transcript_available": scores["transcript_available"],
        "audience_brand_risk": scores["audience_brand_risk"],
        "audience_brand_risk_reason": scores["audience_brand_risk_reason"],
        "brand_safety": scores["brand_safety"],
        "brand_safety_notes": scores["brand_safety_notes"],
        "clickbait_detected": scores["clickbait_detected"],
        "clickbait_examples": str(scores["clickbait_examples"]),
        "competitor_loyalty": scores["competitor_loyalty"],
        "competitor_brands": str(scores["competitor_brands"]),
        "existing_partner": scores["existing_partner"],
        "red_flags": scores["red_flags"],
        "controversy_details": scores["controversy_details"],
        "outreach_recommended": scores["outreach_recommended"],
        # Comment data
        "total_comments_analyzed": comment_scores.get("total_comments", 0),
        "positive_comment_pct": comment_scores.get("positive_comment_pct", 0.0),
        "negative_comment_pct": comment_scores.get("negative_comment_pct", 0.0),
        "purchase_intent_count": comment_scores.get("purchase_intent_count", 0),
        "comment_sentiment_score": scores["comment_sentiment_score"],
        "creator_trust_score": comment_scores.get("creator_trust_score", 5.0),
        "comment_reasoning": comment_scores.get("comment_reasoning", ""),
        "sample_positive_comment": comment_scores.get("sample_positive", "none"),
        "sample_negative_comment": comment_scores.get("sample_negative", "none"),
        "comments_available": comment_scores.get("comments_available", False),
        # Meta
        "scoring_method": scores["scoring_method"],
        "videos_analyzed": len([t for t in transcripts if t]),
    }


def main():
    print("=" * 60)
    print("Gymshark Creator Re-Scorer  —  LLM Holistic Mode")
    print("=" * 60)

    if "PASTE_YOUR" in YOUTUBE_API_KEY or not YOUTUBE_API_KEY:
        print("\n❌ YOUTUBE_API_KEY not set in .env")
        sys.exit(1)

    triton_key = os.getenv("TRITONAI_API_KEY", "")
    if not triton_key:
        print("\n❌ TRITONAI_API_KEY not set in .env")
        sys.exit(1)

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    rows = list(csv.DictReader(open(CSV_PATH, encoding="utf-8")))
    done = load_checkpoint()
    fieldnames = list(rows[0].keys())

    total = len(rows)
    remaining = [r for r in rows if r["channel_id"] not in done]
    print(f"\n{total} creators in CSV.  {len(done)} already done.  {len(remaining)} to score.\n")

    updated_rows = []

    for row in rows:
        cid = row["channel_id"]
        name = row["name"]

        if cid in done:
            print(f"  ↩  {name} — loaded from checkpoint")
            updated_rows.append({**row, **done[cid]})
            continue

        print(f"\n  [{rows.index(row) + 1}/{total}] {name}  ({row['youtube_handle']})")

        new_fields = rescore_creator(youtube, row)

        if new_fields is None:
            print(f"  ⚠  Keeping original row for {name}")
            updated_rows.append(row)
            continue

        done[cid] = new_fields
        save_checkpoint(done)

        gfs = new_fields["gymshark_brand_fit"]
        safety = new_fields["brand_safety"]
        method = new_fields["scoring_method"]
        print(f"  ✓  GFS={gfs}  safety={safety}  method={method}")

        updated_rows.append({**row, **new_fields})

    # Atomic write back to CSV
    tmp = CSV_PATH.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(updated_rows)
    tmp.replace(CSV_PATH)

    if CKPT_PATH.exists():
        CKPT_PATH.unlink()

    print(f"\n{'=' * 60}")
    print(f"✓ Done — {len(updated_rows)} creators written to creators.csv")
    print(f"  Restart the API server to pick up the new scores.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
