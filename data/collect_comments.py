"""
collect_comments.py
-------------------
Fetches REAL YouTube comments for each creator in creators.csv
via the YouTube Data API v3, runs VADER sentiment analysis,
and writes comment_sentiment.csv for Skill 02 risk assessment.

YouTube commentThreads.list is NOT blocked by cloud IPs
(only the transcript API is). Comments are fetched via the
uploads playlist (1 quota unit per creator) rather than search
(100 units) to stay well within the 10,000 unit/day quota.

Quota estimate for 14 creators:
  channels.list     14 × 1  =   14 units
  playlistItems.list 14 × 1  =   14 units
  commentThreads.list 14×3 × 1 =   42 units
  Total                        ~  70 units  (of 10,000/day)

Output: data/comment_sentiment.csv (same schema as previous version)
"""

import csv
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from googleapiclient.discovery import build
except ImportError:
    os.system("pip install google-api-python-client -q")
    from googleapiclient.discovery import build

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
except ImportError:
    os.system("pip install vaderSentiment -q")
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
MAX_COMMENTS_PER_VIDEO = 100  # YouTube API hard max per request
VIDEOS_PER_CREATOR = 15  # Try up to this many videos; stops early once MIN_COMMENTS_TARGET is reached
MIN_COMMENTS_TARGET = 50  # Skill 02 requires ≥50 to assign a risk level

# Data directory — script can be run from anywhere
_DATA_DIR = Path(__file__).resolve().parent
CREATORS_CSV = str(_DATA_DIR / "creators.csv")
OUTPUT_CSV = str(_DATA_DIR / "comment_sentiment.csv")

# ══════════════════════════════════════════════════════════════════════════════
# VADER CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════

_analyzer = SentimentIntensityAnalyzer()


def classify_with_vader(text: str) -> dict:
    scores = _analyzer.polarity_scores(text)
    compound = scores["compound"]
    label = "POSITIVE" if compound >= 0.05 else "NEGATIVE" if compound <= -0.05 else "NEUTRAL"
    confidence = round(max(scores["pos"], scores["neu"], scores["neg"]), 4)
    return {
        "sentiment_label": label,
        "compound_score": round(compound, 4),
        "confidence_score": confidence,
        "vader_pos": round(scores["pos"], 4),
        "vader_neu": round(scores["neu"], 4),
        "vader_neg": round(scores["neg"], 4),
    }


_INTENT_SIGNALS = [
    "just ordered",
    "just bought",
    "ordering",
    "in my cart",
    "adding to cart",
    "where did you get",
    "where is this from",
    "link?",
    "link please",
    "need this",
    "buying this",
    "convinced me",
    "what's your code",
    "do you have a code",
    "already ordered",
    "just purchased",
    "need it",
]

_TRUST_SIGNALS = [
    "sponsored",
    "sold out",
    "sellout",
    "not authentic",
    "staged",
    "not the same",
    "used to be",
    "feels fake",
    "don't trust",
    "misleading",
    "just promoting",
]


def detect_purchase_intent(text: str) -> bool:
    lower = text.lower()
    return any(s in lower for s in _INTENT_SIGNALS)


def detect_negative_creator_flag(text: str, compound: float) -> bool:
    lower = text.lower()
    return any(s in lower for s in _TRUST_SIGNALS) and compound <= 0.0


# ══════════════════════════════════════════════════════════════════════════════
# YOUTUBE API HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def get_channel_info(youtube, handle: str, name: str = "") -> tuple[str | None, str | None]:
    """
    Resolve a YouTube channel to (channel_id, uploads_playlist_id).

    Tries in order:
      1. forHandle lookup — fast, 1 quota unit (works when handle is exact)
      2. Channel-name search — 100 quota units (fallback for invalid handles)
    """
    # Try forHandle first (fails silently for invalid characters like |)
    clean_handle = handle.lstrip("@").strip()
    if clean_handle and "|" not in clean_handle:
        try:
            resp = youtube.channels().list(part="id,contentDetails", forHandle=clean_handle).execute()
            items = resp.get("items", [])
            if items:
                channel_id = items[0]["id"]
                uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
                return channel_id, uploads_id
        except Exception:
            pass

    # Fallback: search by creator name (costs 100 units but reliable)
    search_term = name or clean_handle
    if not search_term:
        return None, None
    try:
        resp = youtube.search().list(part="snippet", q=search_term, type="channel", maxResults=1).execute()
        items = resp.get("items", [])
        if not items:
            return None, None
        channel_id = items[0]["snippet"]["channelId"]
        # Now fetch contentDetails using the channel_id
        ch_resp = youtube.channels().list(part="contentDetails", id=channel_id).execute()
        ch_items = ch_resp.get("items", [])
        if not ch_items:
            return None, None
        uploads_id = ch_items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        return channel_id, uploads_id
    except Exception as e:
        print(f"    Warning: Name search failed for '{search_term}': {e}")
        return None, None


def get_recent_video_ids(
    youtube, channel_id: str, uploads_playlist_id: str, max_videos: int = VIDEOS_PER_CREATOR
) -> list[str]:
    """
    Get recent video IDs. Tries the uploads playlist first (1 quota unit);
    falls back to search.list if the playlist returns 404 (100 units).
    """
    try:
        resp = (
            youtube.playlistItems()
            .list(
                part="contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=max_videos,
            )
            .execute()
        )
        ids = [item["contentDetails"]["videoId"] for item in resp.get("items", [])]
        if ids:
            return ids
    except Exception:
        pass

    # Fallback: search within the channel
    try:
        resp = (
            youtube.search()
            .list(
                part="id",
                channelId=channel_id,
                type="video",
                order="date",
                maxResults=max_videos,
            )
            .execute()
        )
        return [item["id"]["videoId"] for item in resp.get("items", [])]
    except Exception as e:
        print(f"    Warning: Could not fetch video IDs: {e}")
        return []


def fetch_video_comments(youtube, video_id: str, max_results: int = MAX_COMMENTS_PER_VIDEO) -> list[dict]:
    """
    Fetch top-level comments for one video.
    Uses commentThreads.list — 1 quota unit. Returns [] if comments are disabled.
    """
    try:
        resp = (
            youtube.commentThreads()
            .list(
                part="snippet",
                videoId=video_id,
                maxResults=min(max_results, 100),
                order="relevance",
                textFormat="plainText",
            )
            .execute()
        )
        rows = []
        for item in resp.get("items", []):
            snip = item["snippet"]["topLevelComment"]["snippet"]
            rows.append(
                {
                    "text": snip["textDisplay"],
                    "video_id": video_id,
                    "post_date": snip.get("publishedAt", "")[:10],
                }
            )
        return rows
    except Exception as e:
        # Comments may be disabled — not a fatal error
        print(f"    Note: Comments unavailable for video {video_id} — {type(e).__name__}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

OUTPUT_FIELDS = [
    "comment_id",
    "creator_id",
    "creator_name",
    "youtube_handle",
    "video_id",
    "post_date",
    "platform",
    "comment_text",
    "comment_type",
    "sentiment_label",
    "compound_score",
    "confidence_score",
    "vader_pos",
    "vader_neu",
    "vader_neg",
    "purchase_intent",
    "negative_creator_flag",
    "creator_brand_fit",
    "creator_auth_score",
    "classified_at",
    "classification_method",
]


def main():
    print("=" * 65)
    print("Gymshark Comment Sentiment Collection")
    print("Real YouTube comments · YouTube Data API v3")
    print("=" * 65)

    if not YOUTUBE_API_KEY or "PASTE" in YOUTUBE_API_KEY.upper():
        print("\n❌ YOUTUBE_API_KEY not set in .env")
        return

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    with open(CREATORS_CSV, newline="", encoding="utf-8") as f:
        creators = list(csv.DictReader(f))
    print(f"\nLoaded {len(creators)} creators from creators.csv\n")

    all_rows: list[dict] = []
    classified_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for creator in creators:
        creator_id = creator["creator_id"]
        name = creator["name"]
        handle = creator.get("youtube_handle", "")
        brand_fit = float(creator.get("gymshark_brand_fit", 5.0))
        auth_score = float(creator.get("authenticity_score", 5.0))

        print(f"  {name} ({handle})")

        # Step 1 — resolve channel (forHandle first, name-search fallback)
        channel_id, uploads_id = get_channel_info(youtube, handle, name)
        if not channel_id:
            print(f"    ✗ Could not resolve channel — skipping")
            continue
        time.sleep(0.3)

        # Step 2 — get recent video IDs (playlist first, search fallback)
        video_ids = get_recent_video_ids(youtube, channel_id, uploads_id or "")
        if not video_ids:
            print(f"    ✗ No videos found — skipping")
            continue
        time.sleep(0.3)

        # Step 3 — fetch comments until we reach MIN_COMMENTS_TARGET
        raw_comments: list[dict] = []
        for vid_id in video_ids:
            batch = fetch_video_comments(youtube, vid_id)
            raw_comments.extend(batch)
            print(f"    → video {vid_id}: {len(batch)} comments")
            time.sleep(0.3)
            if len(raw_comments) >= MIN_COMMENTS_TARGET:
                break

        if not raw_comments:
            print(f"    ✗ No comments available — creator will show UNKNOWN risk in Skill 02")
            continue

        # Step 4 — VADER + signal detection on real comment text
        creator_rows = []
        for c in raw_comments:
            text = c["text"]
            vader = classify_with_vader(text)
            purchase_intent = detect_purchase_intent(text)
            neg_flag = detect_negative_creator_flag(text, vader["compound_score"])

            creator_rows.append(
                {
                    "comment_id": str(uuid.uuid4())[:8].upper(),
                    "creator_id": creator_id,
                    "creator_name": name,
                    "youtube_handle": handle,
                    "video_id": c["video_id"],
                    "post_date": c["post_date"],
                    "platform": "YouTube",
                    "comment_text": text,
                    "comment_type": "real",
                    "sentiment_label": vader["sentiment_label"],
                    "compound_score": vader["compound_score"],
                    "confidence_score": vader["confidence_score"],
                    "vader_pos": vader["vader_pos"],
                    "vader_neu": vader["vader_neu"],
                    "vader_neg": vader["vader_neg"],
                    "purchase_intent": "Yes" if purchase_intent else "No",
                    "negative_creator_flag": "Yes" if neg_flag else "No",
                    "creator_brand_fit": brand_fit,
                    "creator_auth_score": auth_score,
                    "classified_at": classified_at,
                    "classification_method": "VADER NLP (real comments)",
                }
            )

        all_rows.extend(creator_rows)

        n_flagged = sum(1 for r in creator_rows if r["negative_creator_flag"] == "Yes")
        n_intent = sum(1 for r in creator_rows if r["purchase_intent"] == "Yes")
        avg_compound = round(sum(float(r["compound_score"]) for r in creator_rows) / len(creator_rows), 3)
        skill02_status = (
            "✓ enough for Skill 02"
            if len(creator_rows) >= MIN_COMMENTS_TARGET
            else f"⚠ only {len(creator_rows)} (need {MIN_COMMENTS_TARGET} for risk score)"
        )
        print(
            f"    {len(creator_rows)} comments | avg compound: {avg_compound} | "
            f"flagged: {n_flagged} | intent: {n_intent} | {skill02_status}"
        )

    if not all_rows:
        print("\n❌ No comments collected. Check YOUTUBE_API_KEY and creator handles.")
        return

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)

    total = len(all_rows)
    n_pos = sum(1 for r in all_rows if r["sentiment_label"] == "POSITIVE")
    n_neg = sum(1 for r in all_rows if r["sentiment_label"] == "NEGATIVE")
    n_neu = sum(1 for r in all_rows if r["sentiment_label"] == "NEUTRAL")
    n_intent_total = sum(1 for r in all_rows if r["purchase_intent"] == "Yes")
    n_flag_total = sum(1 for r in all_rows if r["negative_creator_flag"] == "Yes")

    print(f"\n{'=' * 65}")
    print(f"✓  {total} real comments written to comment_sentiment.csv")
    print(f"   POSITIVE: {n_pos} ({100 * n_pos // total}%)")
    print(f"   NEGATIVE: {n_neg} ({100 * n_neg // total}%)")
    print(f"   NEUTRAL:  {n_neu} ({100 * n_neu // total}%)")
    print(f"   Purchase intent signals: {n_intent_total}")
    print(f"   Negative creator flags:  {n_flag_total}")
    print(f"\n   Per creator:")
    for creator in creators:
        cid = creator["creator_id"]
        c_rows = [r for r in all_rows if r["creator_id"] == cid]
        if not c_rows:
            print(f"   {creator['name']:30s} | NO COMMENTS — will show UNKNOWN risk")
            continue
        c_total = len(c_rows)
        c_pos = sum(1 for r in c_rows if r["sentiment_label"] == "POSITIVE")
        c_intent = sum(1 for r in c_rows if r["purchase_intent"] == "Yes")
        c_flag = sum(1 for r in c_rows if r["negative_creator_flag"] == "Yes")
        avg_c = round(sum(float(r["compound_score"]) for r in c_rows) / c_total, 3)
        print(
            f"   {creator['name']:30s} | {c_total:3d} comments | "
            f"{100 * c_pos // c_total}% pos | {c_intent} intent | "
            f"{c_flag} flagged | avg compound: {avg_c}"
        )


if __name__ == "__main__":
    main()
