"""
analyze_top_performers.py
--------------------------
Analyzes existing Gymshark partner campaign performance to identify
which content characteristics predict high conversion.

For each top-performing partner it:
  1. Fetches their YouTube channel and recent videos via the API
  2. Categorizes each video: sponsored | haul | workout | tutorial | review | other
  3. Compares average view counts by content type (sponsored vs organic gap)
  4. Fetches transcripts from their best-performing organic videos
  5. Runs LLM analysis to extract niche, content style, and audience signals
  6. Aggregates findings into niche/content-style bonus weights

Output: data/top_performer_profile.json
Consumed by: data/collect_creators_gemin_2i.py at scoring time

Requirements:
    YOUTUBE_API_KEY in .env  — YouTube Data API v3
    TRITONAI_API_KEY in .env — LLM analysis
"""

import csv
import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from googleapiclient.discovery import build
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
except ImportError:
    os.system("pip install google-api-python-client youtube-transcript-api -q")
    from googleapiclient.discovery import build
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "Paste API key here")
MODEL = "api-llama-4-scout"
VIDEOS_PER_CREATOR = 15
MAX_TRANSCRIPT_WORDS = 800
TOP_N_CREATORS = 5

# ── Video classification signals ─────────────────────────────────────────────

SPONSORED_SIGNALS = [
    "ad ", "#ad", "sponsored", "gifted", "in collab", "collaboration",
    "thank you gymshark", "gymshark sent", "pr ", "partnership",
    "use code", "use my code", "discount code", "affiliate",
]

HAUL_SIGNALS = [
    "haul", "try on", "try-on", "unboxing", "fit check", "outfit",
    "what i bought", "shopping", "new gymshark",
]

WORKOUT_SIGNALS = [
    "workout", "vlog", "leg day", "push day", "pull day", "upper body",
    "lower body", "full body", "gym session", "training day", "gym day",
    "day in my life", "grwm gym", "gym routine",
]

TUTORIAL_SIGNALS = [
    "how to", "tutorial", "guide", "tips", "form", "technique",
    "beginners", "learn", "explained", "science",
]

REVIEW_SIGNALS = [
    "review", "honest review", "worth it", "is it good", "thoughts on",
    "opinion", "rating", "vs ",
]


# ══════════════════════════════════════════════════════════════════════════════
# CAMPAIGN METRICS
# ══════════════════════════════════════════════════════════════════════════════


def load_campaign_metrics(
    campaigns_path: str = "data/campaign_performance.csv",
    partners_path: str = "data/existing_partners.csv",
) -> dict:
    """
    Load and aggregate campaign metrics per creator.
    Returns {creator_id: {name, youtube_handle, tier, niche, roi_x, conversion_rate,
                          cpa_gbp, campaign_count, deal_type}}

    Conversion rate and CPA are only meaningful for affiliate/brand_ambassador deals.
    For paid_creative_partnership, only roi_x is included.
    """
    partners = {}
    with open(partners_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            partners[row["creator_id"]] = row

    creator_stats: dict = {}

    with open(campaigns_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cid = row["creator_id"]
            deal = row.get("deal_type", "")
            try:
                roi = float(row.get("roi_x") or 0)
                budget = float(row.get("budget_gbp") or 0)
                clicks = int(row.get("utm_clicks") or 0)
                redemptions = int(row.get("promo_redemptions") or 0)
            except (ValueError, TypeError):
                continue

            if cid not in creator_stats:
                partner = partners.get(cid, {})
                creator_stats[cid] = {
                    "name": row.get("creator_name", partner.get("name", cid)),
                    "youtube_handle": partner.get("youtube_handle", ""),
                    "tier": row.get("tier", partner.get("tier", "")),
                    "niche": partner.get("niche", ""),
                    "deal_type": deal,
                    "roi_sum": 0.0,
                    "budget_sum": 0.0,
                    "redemptions_sum": 0,
                    "clicks_sum": 0,
                    "campaign_count": 0,
                }

            s = creator_stats[cid]
            s["roi_sum"] += roi
            s["budget_sum"] += budget
            s["redemptions_sum"] += redemptions
            s["clicks_sum"] += clicks
            s["campaign_count"] += 1

    result = {}
    for cid, s in creator_stats.items():
        n = s["campaign_count"]
        avg_roi = round(s["roi_sum"] / n, 2) if n else 0.0
        conversion_rate = (
            round(s["redemptions_sum"] / s["clicks_sum"], 3)
            if s["clicks_sum"] > 0
            else None
        )
        cpa = (
            round(s["budget_sum"] / s["redemptions_sum"], 2)
            if s["redemptions_sum"] > 0
            else None
        )
        result[cid] = {
            "name": s["name"],
            "youtube_handle": s["youtube_handle"],
            "tier": s["tier"],
            "niche": s["niche"],
            "deal_type": s["deal_type"],
            "avg_roi_x": avg_roi,
            "conversion_rate": conversion_rate,
            "cpa_gbp": cpa,
            "campaign_count": n,
        }

    return result


def rank_creators(metrics: dict, top_n: int = TOP_N_CREATORS) -> list:
    """
    Rank creators by avg_roi_x descending.
    Prefers UTM-tracked deals (affiliate/brand_ambassador) since their
    conversion_rate is meaningful. Falls back to roi_x for others.
    Returns top_n as list of {creator_id, ...metrics} dicts.
    """
    ranked = sorted(
        [{"creator_id": cid, **data} for cid, data in metrics.items()],
        key=lambda x: x["avg_roi_x"],
        reverse=True,
    )
    return ranked[:top_n]


# ══════════════════════════════════════════════════════════════════════════════
# VIDEO CATEGORIZATION
# ══════════════════════════════════════════════════════════════════════════════


def categorize_video(title: str, transcript: str = "") -> str:
    """
    Classify a video as: sponsored | haul | workout | tutorial | review | other

    Title is the primary signal. Transcript is used as a tiebreaker when
    the title is ambiguous. Sponsored check runs first — a sponsored haul
    is classified as sponsored.
    """
    text = (title + " " + transcript[:300]).lower()
    title_lower = title.lower()

    if any(s in text for s in SPONSORED_SIGNALS):
        return "sponsored"
    if any(s in title_lower for s in HAUL_SIGNALS):
        return "haul"
    if any(s in title_lower for s in TUTORIAL_SIGNALS):
        return "tutorial"
    if any(s in title_lower for s in REVIEW_SIGNALS):
        return "review"
    if any(s in title_lower for s in WORKOUT_SIGNALS):
        return "workout"
    return "other"


def calculate_view_patterns(videos: list) -> dict:
    """
    Given list of {title, views, category} dicts, calculate:
    - avg_views_by_category: avg view count per category
    - sponsored_organic_gap_pct: % by which sponsored underperforms organic
      (negative = sponsored gets fewer views)
    - best_organic_category: which non-sponsored category gets most views

    Returns empty dict if no videos provided.
    """
    if not videos:
        return {}

    by_category: dict = {}
    for v in videos:
        cat = v.get("category", "other")
        views = v.get("views", 0)
        by_category.setdefault(cat, []).append(views)

    avg_by_category = {
        cat: round(sum(vs) / len(vs)) for cat, vs in by_category.items()
    }

    organic_avgs = {
        cat: avg for cat, avg in avg_by_category.items() if cat != "sponsored"
    }
    best_organic = max(organic_avgs, key=organic_avgs.get) if organic_avgs else "other"

    sponsored_avg = avg_by_category.get("sponsored")
    overall_organic_avg = (
        round(sum(organic_avgs.values()) / len(organic_avgs)) if organic_avgs else None
    )

    if sponsored_avg is not None and overall_organic_avg and overall_organic_avg > 0:
        gap_pct = round((sponsored_avg - overall_organic_avg) / overall_organic_avg * 100, 1)
    else:
        gap_pct = None

    return {
        "avg_views_by_category": avg_by_category,
        "sponsored_organic_gap_pct": gap_pct,
        "best_organic_category": best_organic,
        "total_videos_analyzed": len(videos),
    }


# ══════════════════════════════════════════════════════════════════════════════
# YOUTUBE HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def find_channel(youtube, creator_name: str) -> dict | None:
    """
    Search YouTube for a creator's channel by name.
    Returns {channel_id, title} or None if not found.
    """
    try:
        resp = (
            youtube.search()
            .list(q=creator_name, part="snippet", type="channel", maxResults=1)
            .execute()
        )
        items = resp.get("items", [])
        if not items:
            return None
        item = items[0]
        return {
            "channel_id": item["snippet"]["channelId"],
            "title": item["snippet"]["title"],
        }
    except Exception as e:
        print(f"    Warning: channel search failed for '{creator_name}': {e}")
        return None


def fetch_recent_videos(youtube, channel_id: str, max_results: int = VIDEOS_PER_CREATOR) -> list:
    """
    Fetch recent videos for a channel with view counts.
    Returns list of {video_id, title, views}.
    """
    try:
        search_resp = (
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
        video_ids = [item["id"]["videoId"] for item in search_resp.get("items", [])]
        titles = {
            item["id"]["videoId"]: item["snippet"]["title"]
            for item in search_resp.get("items", [])
        }
        if not video_ids:
            return []

        stats_resp = (
            youtube.videos()
            .list(part="statistics", id=",".join(video_ids))
            .execute()
        )

        videos = []
        for item in stats_resp.get("items", []):
            vid = item["id"]
            views = int(item["statistics"].get("viewCount", 0))
            videos.append({
                "video_id": vid,
                "title": titles.get(vid, ""),
                "views": views,
            })
        return videos

    except Exception as e:
        print(f"    Warning: video fetch failed for channel {channel_id}: {e}")
        return []


def fetch_transcript(video_id: str, max_words: int = MAX_TRANSCRIPT_WORDS) -> str | None:
    """Fetch video transcript, truncated to max_words. Returns None if unavailable."""
    try:
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id, languages=["en", "en-US", "en-GB"])
        text = " ".join(s.text for s in fetched)
        words = text.split()
        return " ".join(words[:max_words]).lower() if words else None
    except (NoTranscriptFound, TranscriptsDisabled):
        return None
    except Exception as e:
        print(f"    Warning: transcript error for {video_id}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# LLM ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════


def analyze_creator_content_llm(
    creator_name: str,
    campaign_metrics: dict,
    videos: list,
    view_patterns: dict,
    model: str = MODEL,
) -> dict:
    """
    LLM analyzes a top-performing creator's content to extract the
    characteristics that make them convert well for Gymshark.
    Returns a structured dict with niche, content style, and key signals.
    """
    from pydantic import BaseModel
    from utils.connect import ask_json

    class CreatorAnalysis(BaseModel):
        niche: str
        sub_niche: str
        primary_content_style: str
        product_mention_style: str
        audience_buying_signals: list[str]
        key_characteristics: list[str]
        why_they_convert: str

    titles = [v["title"] for v in videos[:15]]
    titles_str = "\n".join(f"  {i+1}. {t}" for i, t in enumerate(titles))

    organic_videos = [v for v in videos if v.get("category") not in ("sponsored", None)]
    transcript_text = ""
    for v in organic_videos[:3]:
        t = v.get("transcript")
        if t:
            transcript_text += f"\n[{v['title']}]\n{t[:400]}\n"

    best_cat = view_patterns.get("best_organic_category", "unknown")
    gap = view_patterns.get("sponsored_organic_gap_pct")
    gap_str = f"{gap:+.1f}%" if gap is not None else "unknown"

    prompt = f"""You are analyzing a top-performing Gymshark brand partner to understand what makes them convert well.

CREATOR: {creator_name}
TIER: {campaign_metrics.get('tier', 'unknown')}
NICHE (as labelled): {campaign_metrics.get('niche', 'unknown')}
AVG ROI: {campaign_metrics.get('avg_roi_x', 'unknown')}x
CONVERSION RATE: {campaign_metrics.get('conversion_rate', 'unknown')}
DEAL TYPE: {campaign_metrics.get('deal_type', 'unknown')}

RECENT VIDEO TITLES:
{titles_str}

VIEW PATTERNS:
  Best performing content type: {best_cat}
  Sponsored vs organic view gap: {gap_str}
  Avg views by category: {view_patterns.get('avg_views_by_category', {})}

SAMPLE TRANSCRIPT (organic videos):
{transcript_text if transcript_text else 'No transcripts available'}

Based on this, identify:

niche — be specific (e.g. "Women's Strength Training" not just "fitness")
sub_niche — even more specific topic they focus on
primary_content_style — what type of content gets them the most views (workout vlog, tutorial, review, haul, etc.)
product_mention_style — how they reference products: "authentic review" | "casual workout integration" | "dedicated haul" | "educational comparison"
audience_buying_signals — list of 3-5 specific signals that show their audience is likely to buy (e.g. "comments asking where to buy", "high purchase intent language", "audience trusts their product recommendations")
key_characteristics — list of 3-5 content characteristics that Gymshark should look for in new prospects to predict similar performance
why_they_convert — one sentence explaining specifically why this creator drives purchases for Gymshark"""

    try:
        result = ask_json(prompt, schema=CreatorAnalysis, model=model)
        return {
            "creator_id": campaign_metrics.get("creator_id", ""),
            "name": creator_name,
            "niche": result.niche,
            "sub_niche": result.sub_niche,
            "primary_content_style": result.primary_content_style,
            "product_mention_style": result.product_mention_style,
            "audience_buying_signals": result.audience_buying_signals,
            "key_characteristics": result.key_characteristics,
            "why_they_convert": result.why_they_convert,
            "avg_roi_x": campaign_metrics.get("avg_roi_x"),
            "conversion_rate": campaign_metrics.get("conversion_rate"),
            "view_patterns": view_patterns,
        }
    except Exception as e:
        print(f"    Warning: LLM analysis failed for {creator_name}: {e}")
        return {
            "creator_id": campaign_metrics.get("creator_id", ""),
            "name": creator_name,
            "niche": campaign_metrics.get("niche", "General Fitness"),
            "sub_niche": "",
            "primary_content_style": view_patterns.get("best_organic_category", "workout"),
            "product_mention_style": "unknown",
            "audience_buying_signals": [],
            "key_characteristics": [],
            "why_they_convert": "LLM analysis unavailable",
            "avg_roi_x": campaign_metrics.get("avg_roi_x"),
            "conversion_rate": campaign_metrics.get("conversion_rate"),
            "view_patterns": view_patterns,
        }


# ══════════════════════════════════════════════════════════════════════════════
# PROFILE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

# All known niches — unlisted ones get 0.0 bonus
KNOWN_NICHES = [
    "Women's Fitness", "Bodybuilding", "Weightlifting", "Powerlifting",
    "HIIT", "CrossFit", "Calisthenics", "Gym Lifestyle", "General Fitness",
]

KNOWN_STYLES = [
    "Workout Vlog", "Tutorial", "Review", "Try-On Haul",
    "Transformation", "Day-in-Life", "Educational",
]


def _composite_weight(creator: dict, max_roi: float, max_cr: float, min_cpa: float) -> float:
    """
    Combine ROI, conversion rate, and CPA into a single creator weight.

    ROI (50%) — revenue efficiency, available for all deal types
    Conversion rate (30%) — how persuasive the creator is; None for non-UTM deals
    CPA efficiency (20%) — lower CPA = higher score; None if no redemptions

    Components that are unavailable for a creator contribute 0 to that
    creator's weight so UTM-tracked creators aren't unfairly penalised.
    """
    roi = (creator.get("avg_roi_x") or 0) / max_roi if max_roi else 0.0

    cr = creator.get("conversion_rate")
    cr_score = (cr / max_cr) if (cr is not None and max_cr > 0) else 0.0

    cpa = creator.get("cpa_gbp")
    cpa_score = (min_cpa / cpa) if (cpa and min_cpa and cpa > 0) else 0.0

    return round(roi * 0.50 + cr_score * 0.30 + cpa_score * 0.20, 4)


def build_scoring_adjustments(creator_analyses: list) -> dict:
    """
    Aggregate LLM analyses from top performers into niche and content
    style bonus weights for the GFS formula.

    Weight = composite of ROI (50%), conversion rate (30%), CPA efficiency (20%).
    A niche or style that appears in high-performing creators gets a higher
    bonus than one appearing only in lower-performing ones.
    Bonuses are scaled to a max of 0.8.
    """
    if not creator_analyses:
        return {"niche_bonus": {}, "content_style_bonus": {}}

    max_roi = max((c.get("avg_roi_x") or 0) for c in creator_analyses) or 1.0
    crs = [c["conversion_rate"] for c in creator_analyses if c.get("conversion_rate") is not None]
    max_cr = max(crs) if crs else 1.0
    cpas = [c["cpa_gbp"] for c in creator_analyses if c.get("cpa_gbp") is not None]
    min_cpa = min(cpas) if cpas else 0.0

    niche_scores: dict = {}
    style_scores: dict = {}

    for c in creator_analyses:
        weight = _composite_weight(c, max_roi, max_cr, min_cpa)
        niche = c.get("niche", "")
        style = c.get("primary_content_style", "")

        if niche:
            niche_scores[niche] = niche_scores.get(niche, 0) + weight
        if style:
            style_scores[style] = style_scores.get(style, 0) + weight

    def normalize(scores: dict, scale: float = 0.8) -> dict:
        if not scores:
            return {}
        max_score = max(scores.values())
        if max_score == 0:
            return {k: 0.0 for k in scores}
        return {k: round(v / max_score * scale, 2) for k, v in scores.items()}

    niche_bonus = normalize(niche_scores)
    style_bonus = normalize(style_scores)

    # Fill in 0.0 for known niches/styles not represented in top performers
    for n in KNOWN_NICHES:
        niche_bonus.setdefault(n, 0.0)
    for s in KNOWN_STYLES:
        style_bonus.setdefault(s, 0.0)

    return {
        "niche_bonus": dict(sorted(niche_bonus.items(), key=lambda x: -x[1])),
        "content_style_bonus": dict(sorted(style_bonus.items(), key=lambda x: -x[1])),
    }


def build_profile(top_creators: list, creator_analyses: list) -> dict:
    """Assemble the full top_performer_profile.json."""
    adjustments = build_scoring_adjustments(creator_analyses)

    all_signals = []
    all_characteristics = []
    for c in creator_analyses:
        all_signals.extend(c.get("audience_buying_signals", []))
        all_characteristics.extend(c.get("key_characteristics", []))

    top_niche = (
        max(adjustments["niche_bonus"], key=adjustments["niche_bonus"].get)
        if adjustments["niche_bonus"]
        else "General Fitness"
    )
    top_style = (
        max(adjustments["content_style_bonus"], key=adjustments["content_style_bonus"].get)
        if adjustments["content_style_bonus"]
        else "Workout Vlog"
    )

    return {
        "generated_at": datetime.now().isoformat(),
        "top_performers": [
            {
                "creator_id": c.get("creator_id"),
                "name": c.get("name"),
                "niche": c.get("niche"),
                "avg_roi_x": c.get("avg_roi_x"),
                "conversion_rate": c.get("conversion_rate"),
                "cpa_gbp": c.get("cpa_gbp"),
                "primary_content_style": c.get("primary_content_style"),
                "why_they_convert": c.get("why_they_convert"),
            }
            for c in creator_analyses
        ],
        "top_niche": top_niche,
        "top_content_style": top_style,
        "common_buying_signals": list(dict.fromkeys(all_signals))[:8],
        "common_characteristics": list(dict.fromkeys(all_characteristics))[:8],
        "scoring_adjustments": adjustments,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 65)
    print("Gymshark Top Performer Analysis")
    print("Builds scoring weights from existing partner campaign data")
    print("=" * 65)

    if "Paste" in YOUTUBE_API_KEY:
        print("\n❌ YouTube API key not set in .env")
        return

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    print("\n[1/4] Loading campaign metrics...")
    metrics = load_campaign_metrics()
    top_creators = rank_creators(metrics)
    print(f"  Top {len(top_creators)} creators by ROI:")
    for c in top_creators:
        cr = f"{c['conversion_rate']:.1%}" if c["conversion_rate"] else "N/A"
        print(f"    {c['name']:<25} ROI: {c['avg_roi_x']}x  Conv: {cr}  Niche: {c['niche']}")

    print("\n[2/4] Fetching YouTube data...")
    creator_analyses = []

    for creator in top_creators:
        name = creator["name"]
        handle = creator.get("youtube_handle", "").lstrip("@")
        print(f"\n  → {name} ({handle})")

        channel = find_channel(youtube, name)
        if not channel:
            print(f"    ✗ Channel not found — skipping")
            continue
        print(f"    ✓ Found: {channel['title']} ({channel['channel_id']})")
        time.sleep(0.3)

        raw_videos = fetch_recent_videos(youtube, channel["channel_id"])
        print(f"    ✓ {len(raw_videos)} videos fetched")
        time.sleep(0.3)

        # Categorize and fetch transcripts for organic videos
        videos = []
        for v in raw_videos:
            cat = categorize_video(v["title"])
            v["category"] = cat
            if cat not in ("sponsored",) and len([x for x in videos if x.get("transcript")]) < 3:
                print(f"    → Transcript: {v['title'][:50]}...")
                v["transcript"] = fetch_transcript(v["video_id"])
                time.sleep(0.4)
            else:
                v["transcript"] = None
            videos.append(v)

        view_patterns = calculate_view_patterns(videos)
        gap = view_patterns.get("sponsored_organic_gap_pct")
        gap_str = f"{gap:+.1f}%" if gap is not None else "N/A"
        print(f"    View patterns: best={view_patterns.get('best_organic_category')}  sponsored gap={gap_str}")

        print(f"    → Running LLM analysis...")
        analysis = analyze_creator_content_llm(name, creator, videos, view_patterns)
        analysis["creator_id"] = creator["creator_id"]
        creator_analyses.append(analysis)
        print(f"    ✓ Niche: {analysis['niche']} | Style: {analysis['primary_content_style']}")
        time.sleep(0.5)

    if not creator_analyses:
        print("\n❌ No creator analyses completed.")
        return

    print("\n[3/4] Building scoring profile...")
    profile = build_profile(top_creators, creator_analyses)

    print(f"  Top niche:  {profile['top_niche']}")
    print(f"  Top style:  {profile['top_content_style']}")
    print(f"  Niche bonuses:")
    for niche, bonus in list(profile["scoring_adjustments"]["niche_bonus"].items())[:5]:
        if bonus > 0:
            print(f"    {niche:<25} +{bonus}")

    print("\n[4/4] Writing profile...")
    out_path = "data/top_performer_profile.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)
    print(f"  ✓ Saved → {out_path}")

    print(f"\n{'=' * 65}")
    print(f"✓ Profile built from {len(creator_analyses)} creators")
    print(f"  Rerun collect_creators_gemin_2i.py to apply new weights")
    print(f"{'=' * 65}\n")


if __name__ == "__main__":
    main()
