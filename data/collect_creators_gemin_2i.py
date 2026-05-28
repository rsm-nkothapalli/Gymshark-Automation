"""
collect_creators_gemini.py
--------------------------
Gymshark Creator Discovery Pipeline — LLM-Based Holistic Scoring

Scores creators using coherent LLM evaluation of:
- Real YouTube channel statistics (YouTube Data API)
- Real video transcripts (youtube-transcript-api — free, no key)
- Real video comments (YouTube Data API)
- Real video titles
- LLM-powered contextual NLP scoring

All scoring decisions go through the LLM for exhaustive analysis.

SCORING LAYERS:
    1. Transcript analysis — what the creator actually says
    2. Comment sentiment  — how the audience responds to the creator
    3. Channel stats      — engagement proxy from views/subscribers

BRAND FIT FORMULA:
    authenticity(40%) + comment_sentiment(30%) + niche(20%) + engagement(10%)
    - penalties for clickbait, safety risks, competitor loyalty

Requirements:
    pip install google-api-python-client youtube-transcript-api

API Keys needed:
    YouTube Data API v3 ONLY → https://console.cloud.google.com
    NO Gemini key needed
"""

import os
import re
import json
import time
import csv
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

try:
    from googleapiclient.discovery import build
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
except ImportError:
    print("Installing required packages...")
    os.system("pip install google-api-python-client youtube-transcript-api -q")
    from googleapiclient.discovery import build
    from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

# ══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "Paste API key here")

MIN_BRAND_FIT_SCORE = 5
MIN_AUTHENTICITY_SCORE = 5
RESULTS_PER_QUERY = 5
VIDEOS_PER_CREATOR = 2
TITLES_TO_SCAN = 20
MAX_TRANSCRIPT_WORDS = 1000
MAX_COMMENTS = 50

# Set to True to score transcripts with the LLM instead of keyword lists.
# LLM scoring is context-aware (eliminates false positives like "test" matching).
# Requires TRITONAI_API_KEY in .env. Set False to use fast rule-based scoring.
USE_LLM_SCORING = True
CHECKPOINT_FILE = "checkpoint.json"
TOP_PERFORMER_PROFILE = "data/top_performer_profile.json"


def _load_top_performer_profile() -> dict:
    """
    Load the performance profile built by analyze_top_performers.py.
    Returns empty dict if the file doesn't exist — scoring runs without
    campaign-based weights in that case.
    """
    if not os.path.exists(TOP_PERFORMER_PROFILE):
        return {}
    try:
        with open(TOP_PERFORMER_PROFILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_PERFORMER_PROFILE: dict = _load_top_performer_profile()

# ── Search queries ────────────────────────────────────────────────────────────
SEARCH_QUERIES = [
    "gymshark haul bought myself not sponsored",
    "gymshark honest review worth it",
    "gymshark try on first time",
    "gymshark leggings review real opinion",
    "gymshark unboxing honest thoughts",
    "is gymshark worth the money",
    "gymshark vs other brands honest",
    "gymshark workout not ad",
    "gymshark clothing review unsponsored",
    "bought gymshark for the first time",
]

# ══════════════════════════════════════════════════════════════════════════════
# SIGNAL DICTIONARIES
# ══════════════════════════════════════════════════════════════════════════════

# ── Authenticity POSITIVE — what genuine buyers/trainers say (+2 each) ────────
AUTHENTICITY_POSITIVE = [
    # Purchased themselves
    "i bought",
    "i purchased",
    "i ordered",
    "i got this from",
    "i picked up",
    "spent my own money",
    "paid for this myself",
    "bought this myself",
    "bought with my own money",
    "not gifted",
    "not a sponsor",
    "this is not sponsored",
    "not sponsored",
    "no one asked me",
    "my own opinion",
    "genuinely love",
    "i genuinely",
    "unsponsored",
    "no code",
    "no discount",
    "didn't get paid",
    # Real training talk
    "i actually wear this to the gym",
    "i train in this",
    "i actually train",
    "i train",
    "been lifting",
    "been going to the gym",
    "wore this today",
    "wore it for my workout",
    "actually wear",
    "wear to the gym",
    "works out in",
    "i work out in",
    "train in these",
    # Genuine product feedback
    "held up well",
    "washed it",
    "after washing",
    "after a few washes",
    "pilling",
    "no pilling",
    "see through",
    "not see through",
    "squat proof",
    "squat tested",
    "waistband",
    "fits true to size",
    "runs small",
    "runs large",
    "comfortable",
    "so comfortable",
    "quality is",
    "material feels",
    "fabric feels",
    "thick material",
    "thin material",
    "worth the money",
    "not worth",
    "overpriced",
    "good value",
    # Honest review language
    "my thoughts",
    "in my opinion",
    "personally i",
    "i find that",
    "for me",
    "works for me",
    "i would recommend",
    "i wouldn't recommend",
    "honest review",
    "honest opinion",
    "my honest",
    "pros and cons",
    "honest thoughts",
    "real talk",
    "being honest",
    "to be honest",
    "truthfully",
    # Progress and journey talk
    "my progress",
    "my journey",
    "working on",
    "trying to",
    "i struggle with",
    "getting better at",
    "consistency",
    "showing up",
    "hard work",
    "started my fitness",
    "started going to the gym",
    "been going for",
    "months of training",
    "years of training",
    "real progress",
    "not perfect",
    "struggled",
    "failed",
    "hard day",
    "bad workout",
    "bad session",
]

# ── Authenticity NEGATIVE — commercial/partnership language (-2 each) ─────────
AUTHENTICITY_NEGATIVE = [
    # Direct partnership signals
    "use my code",
    "use code",
    "my code",
    "link in bio",
    "gymshark sent me",
    "pr package",
    "gifted by",
    "gifted from",
    "sponsored by",
    "in collaboration with",
    "ad ",
    "#ad",
    "gymshark athlete",
    "gymshark ambassador",
    "gymshark partner",
    "gymshark family member",
    "collab",
    "collaboration",
    "working with gymshark",
    "gymshark reached out",
    "they sent me",
    "pr box",
    "unboxing my pr",
    "gifted these",
    "thank you gymshark",
    "grateful to gymshark",
    # Sales language
    "check the link",
    "swipe up",
    "tap the link",
    "code at checkout",
    "save with my code",
    "percentage off",
    "percent off",
    "discount link",
    "affiliate link",
    "affiliate code",
]

# ── Community POSITIVE — genuine audience connection (+1 each) ────────────────
COMMUNITY_POSITIVE = [
    "you guys",
    "you all",
    "my community",
    "thank you for watching",
    "comment below",
    "let me know",
    "what do you think",
    "i hope this helps",
    "for you",
    "your journey",
    "beginner",
    "just starting",
    "everyone can",
    "inclusive",
    "regardless of",
    "no matter your size",
    "all body types",
    "you asked",
    "been requested",
    "for my beginners",
    "don't be intimidated",
    "everyone starts somewhere",
]

# ── Clickbait signals (-3 each — hard disqualifier) ───────────────────────────
CLICKBAIT_SIGNALS = [
    "abs in",
    "lose weight in",
    "transformation in",
    "get fit in",
    "shred in",
    "burn fat in",
    "this one exercise",
    "secret workout",
    "guaranteed",
    "changed my body in",
    "overnight results",
    "instant results",
    "doctors don't want",
    "lose 10",
    "drop 10",
    "get abs fast",
    "quick fix",
    "magic",
    "trick to",
    "you won't believe",
    "insane results",
]

# ── Brand safety risks (-3 each) ──────────────────────────────────────────────
SAFETY_NEGATIVE = [
    "steroids",
    "gear ",
    "tren ",
    "sarms",
    "ped ",
    "eating disorder",
    "don't eat",
    "skip meals",
    "starving",
    "i hate",
    "disgusting",
    "racist",
    "sexist",
    "controversial",
    "drama",
    "cancel",
    "exposed",
    "offensive",
    "inappropriate",
    "problematic",
]

# ── Competitor brand signals (-2 each) ────────────────────────────────────────
COMPETITOR_SIGNALS = [
    "alphalete",
    "lululemon",
    "lulu lemon",
    "youngla",
    "young la",
    "aybl",
    "nvgtn",
    "fleo",
    "echt activewear",
    "better than gymshark",
    "gymshark is bad",
    "don't buy gymshark",
]

# ── Niche signals — expanded gym-only vocabulary ──────────────────────────────
NICHE_SIGNALS = {
    "Weightlifting": [
        # Movements
        "deadlift",
        "squat",
        "bench press",
        "overhead press",
        "barbell row",
        "romanian deadlift",
        "rdl",
        "hip thrust",
        "sumo",
        "conventional",
        "front squat",
        "back squat",
        "goblet squat",
        "split squat",
        "lunges",
        "leg press",
        "leg extension",
        "leg curl",
        "calf raise",
        "lat pulldown",
        "cable row",
        "dumbbell row",
        "chest fly",
        "tricep extension",
        "bicep curl",
        "shoulder press",
        # Training terms
        "barbell",
        "dumbbell",
        "kettlebell",
        "resistance band",
        "cables",
        "free weights",
        "weight rack",
        "lifting",
        "weights",
        "strength",
        "rep",
        "reps",
        "sets",
        "progressive overload",
        "1rm",
        "one rep max",
        "compound",
        "isolation",
        "superset",
        "drop set",
        "tempo",
        "time under tension",
        "mind muscle connection",
        "form",
        "technique",
        "range of motion",
        "rom",
        "full range",
        "partial rep",
        # Progress
        "personal record",
        "new pr",
        "hit a pr",
        "strength gains",
        "getting stronger",
        "adding weight",
        "plate",
        "plates",
    ],
    "Bodybuilding": [
        # Goals
        "bodybuilding",
        "physique",
        "bulk",
        "bulking",
        "cut",
        "cutting",
        "shred",
        "shredding",
        "lean bulk",
        "dirty bulk",
        "recomp",
        "body recomposition",
        "muscle mass",
        "muscle building",
        "hypertrophy",
        "gains",
        "muscle gains",
        "putting on size",
        # Nutrition
        "macros",
        "macronutrients",
        "calories",
        "caloric surplus",
        "caloric deficit",
        "protein intake",
        "hitting macros",
        "tracking calories",
        "meal prep",
        "eating enough",
        "pre workout",
        "post workout",
        "protein shake",
        "whey",
        "creatine",
        "supplements",
        "calorie counting",
        # Physique
        "definition",
        "vascularity",
        "pump",
        "muscle pump",
        "aesthetics",
        "symmetry",
        "conditioning",
        "stage ready",
        "competition prep",
        "competition",
        "posing",
        "stage",
        "natural bodybuilding",
        "natty",
        "drug free",
    ],
    "Women's Fitness": [
        # Focus areas
        "glutes",
        "booty",
        "bum",
        "growing glutes",
        "glute gains",
        "hourglass",
        "curves",
        "feminine",
        "toned",
        "lean and toned",
        "arms",
        "toned arms",
        "back fat",
        "love handles",
        # Workouts
        "hip thrust",
        "glute bridge",
        "donkey kick",
        "fire hydrant",
        "abduction",
        "resistance band workout",
        "booty workout",
        "lower body",
        "upper body",
        "full body",
        "core workout",
        "ab workout",
        "waist training",
        # Apparel specific
        "leggings",
        "sports bra",
        "gym set",
        "matching set",
        "squat proof",
        "high waist",
        "seamless",
        "scrunch",
        "gymwear",
        "activewear",
        "workout outfit",
        "gym fit",
        "fit check",
        "try on",
        "haul",
        # Community
        "women",
        "girls",
        "ladies",
        "girl gains",
        "strong women",
        "women who lift",
        "female fitness",
        "body confidence",
        "body positivity",
        "self love",
        "loving your body",
        "postpartum",
        "prenatal",
        "cycle syncing",
    ],
    "Powerlifting": [
        # The sport
        "powerlifting",
        "meet",
        "competition",
        "total",
        "wilks",
        "dots",
        "ipf",
        "usapl",
        "uspa",
        "raw",
        "equipped",
        "squat rack",
        "deadlift platform",
        "bench",
        "fed",
        # Lifts
        "competition squat",
        "competition bench",
        "competition deadlift",
        "opener",
        "second attempt",
        "third attempt",
        "max attempt",
        "peaking",
        "peak week",
        "meet prep",
        "weight cut",
        # Training
        "1rm",
        "one rep max",
        "training max",
        "e1rm",
        "estimated max",
        "percentage",
        "intensity",
        "volume",
        "conjugate",
        "westside",
        "sheiko",
        "smolov",
        "nsuns",
        "531",
        "linear progression",
        "strength sport",
        "powerbuilding",
        "strength training",
    ],
    "Calisthenics": [
        # Skills
        "calisthenics",
        "bodyweight",
        "pull up",
        "push up",
        "dip",
        "muscle up",
        "handstand",
        "handstand push up",
        "planche",
        "front lever",
        "back lever",
        "human flag",
        "l-sit",
        "pistol squat",
        "dragon flag",
        "archer push up",
        # Training
        "bar workout",
        "rings",
        "gymnastic rings",
        "parallel bars",
        "street workout",
        "park workout",
        "outdoor workout",
        "skill work",
        "progressions",
        "tuck planche",
        "straddle",
        "negatives",
        "scapular pull ups",
        "hollow body",
        "straight body",
        # Community
        "street lifting",
        "bar athlete",
        "freestyle",
    ],
    "HIIT": [
        # Formats
        "hiit",
        "high intensity interval training",
        "tabata",
        "amrap",
        "emom",
        "circuit",
        "circuit training",
        "interval training",
        "metabolic conditioning",
        "metcon",
        # Exercises
        "burpee",
        "jumping jack",
        "mountain climber",
        "box jump",
        "jump squat",
        "high knees",
        "sprint",
        "battle ropes",
        "sled push",
        "tire flip",
        "med ball",
        "wall ball",
        # Goals
        "cardio",
        "fat burn",
        "burn calories",
        "sweat",
        "conditioning",
        "endurance",
        "stamina",
        "aerobic",
        "anaerobic",
        "heart rate",
        "max heart rate",
        "zone 2",
        "zone 3",
    ],
    "CrossFit": [
        # Terminology
        "crossfit",
        "wod",
        "workout of the day",
        "box",
        "affiliate",
        "rx",
        "scaled",
        "coach",
        "whiteboard",
        # Movements
        "clean",
        "snatch",
        "clean and jerk",
        "thruster",
        "wall ball",
        "double under",
        "toes to bar",
        "kipping",
        "butterfly",
        "olympic lifting",
        "oly",
        "power clean",
        "hang clean",
        # Workouts
        "fran",
        "grace",
        "helen",
        "cindy",
        "murph",
        "karen",
        "amrap",
        "emom",
        "for time",
        "chipper",
        "ladder",
        "benchmark workout",
        "hero wod",
    ],
    "Gym Lifestyle": [
        # General gym
        "gym",
        "workout",
        "training",
        "fitness",
        "fit",
        "health",
        "active",
        "healthy lifestyle",
        "gym life",
        "gym rat",
        "gym motivation",
        "gym goals",
        "fitness journey",
        "fitness goals",
        "fitness lifestyle",
        # Motivation
        "grind",
        "hustle",
        "discipline",
        "dedication",
        "consistency",
        "showing up",
        "no days off",
        "rest day",
        "recovery",
        "sleep",
        "hydration",
        "water intake",
        # Gym culture
        "gains",
        "swole",
        "jacked",
        "shredded",
        "lean",
        "gym outfit",
        "gym bag",
        "gym playlist",
        "pre workout",
        "post workout meal",
        "protein",
        "supplement",
        "personal trainer",
        "pt",
        "coach",
        "programme",
    ],
}

# ── Content style signals ─────────────────────────────────────────────────────
CONTENT_STYLE_SIGNALS = {
    "Try-On Haul": ["try on", "haul", "trying on", "fit check", "outfit", "unboxing"],
    "Workout Vlog": ["workout", "session", "training day", "gym day", "leg day", "push day", "pull day"],
    "Tutorial": ["how to", "tutorial", "form", "technique", "guide", "tips", "beginners"],
    "Review": ["review", "honest review", "worth it", "is it good", "thoughts on", "opinion"],
    "Transformation": ["transformation", "before and after", "progress", "journey", "results"],
    "Day-in-Life": ["day in my life", "vlog", "daily", "morning routine", "follow me"],
    "Educational": ["explained", "science", "study", "research", "evidence", "why you should"],
}

# ── Existing partner pre-filter signals ───────────────────────────────────────
EXISTING_PARTNER_SIGNALS = [
    "gymshark athlete",
    "gymshark ambassador",
    "gymshark partner",
    "gymshark family",
    "sponsored by gymshark",
    "gifted by gymshark",
    "use my code",
    "discount code",
    "link in bio gymshark",
    "gymshark affiliate",
    "collab with gymshark",
]

# ── Clickbait title patterns — pre-filter ─────────────────────────────────────
CLICKBAIT_TITLE_PATTERNS = [
    "abs in",
    "lose weight in",
    "body transformation in",
    "get fit in",
    "shred in",
    "burn fat in",
    "this one exercise",
    "secret workout",
    "guaranteed results",
    "i lost",
    "dropped",
    "kg in",
    "lbs in",
    "changed my body in",
    "overnight",
    "instant results",
]

# ── Comment sentiment signals ─────────────────────────────────────────────────

# Positive about the CREATOR (+1 each)
COMMENT_POSITIVE = [
    "love your videos",
    "love your content",
    "so real",
    "so genuine",
    "you're so authentic",
    "honest",
    "trustworthy",
    "i trust you",
    "you're so relatable",
    "thank you for this",
    "this is exactly what i needed",
    "obsessed with your channel",
    "so helpful",
    "amazing content",
    "keep it up",
    "keep going",
    "don't stop",
    "please keep making videos",
    "you inspired me",
    "you motivated me",
    "because of you",
    "started going to the gym",
    "just started lifting",
    "where did you get",
    "just ordered",
    "ordering this now",
    "need this",
    "what's your code",
    "link?",
    "where is this from",
    "just bought",
    "already ordered",
    "in my cart",
    "you're my favourite",
    "best channel",
    "underrated",
    "so down to earth",
    "no bs",
    "straight to the point",
    "real talk",
    "actual review",
    "not paid to say this",
]

# Negative about the CREATOR (-2 each — trust signal)
COMMENT_NEGATIVE = [
    # Calling out inauthenticity
    "you're just doing this for money",
    "this is obviously sponsored",
    "sold out",
    "sellout",
    "all your videos are ads now",
    "fake",
    "staged",
    "not the same anymore",
    "used to be real",
    "you've changed",
    "lost your authenticity",
    # Trust issues
    "you lied",
    "stop lying",
    "misleading",
    "false advertising",
    "scam",
    "clickbait",
    "you're just trying to sell",
    "this didn't work",
    "waste of money",
    # Toxic creator behaviour
    "cancelled",
    "problematic",
    "cringe",
    "you're so rude",
    "annoying",
    "unbearable",
    "stop promoting",
    "unsubscribed",
    "reported",
    "flagged",
]

# Purchase intent in comments (+1 each — strong Gymshark signal)
COMMENT_PURCHASE_INTENT = [
    "where did you get",
    "where is this from",
    "what's the link",
    "just ordered",
    "just bought",
    "ordering now",
    "in my cart",
    "need this",
    "want this",
    "buying this",
    "what's your code",
    "any discount",
    "is there a code",
    "already ordered",
    "mine just arrived",
    "got mine",
]


# ══════════════════════════════════════════════════════════════════════════════
# CHECKPOINT SYSTEM
# ══════════════════════════════════════════════════════════════════════════════


def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
        print(f"  ✓ Checkpoint found — {len(data.get('done', {}))} creators already scored")
        return data
    print(f"  No checkpoint — starting fresh")
    return {"done": {}, "candidates": [], "searches_done": False}


def save_checkpoint(data):
    with open(CHECKPOINT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def clear_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        os.remove(CHECKPOINT_FILE)


# ══════════════════════════════════════════════════════════════════════════════
# YOUTUBE HELPERS
# ══════════════════════════════════════════════════════════════════════════════


def search_youtube(youtube, query, max_results):
    try:
        response = (
            youtube.search()
            .list(
                q=query,
                part="snippet",
                type="video",
                maxResults=max_results,
                relevanceLanguage="en",
                videoDuration="medium",
                order="date",
            )
            .execute()
        )
    except Exception as e:
        print(f"  Warning: Search error for '{query}': {e}")
        return []

    results = {}
    for item in response.get("items", []):
        cid = item["snippet"]["channelId"]
        vid = item["id"]["videoId"]
        title = item["snippet"]["title"]
        if cid not in results:
            results[cid] = {
                "channel_id": cid,
                "channel_title": item["snippet"]["channelTitle"],
                "video_urls": [],
                "video_titles": [],
                "video_ids": [],
            }
        if len(results[cid]["video_urls"]) < VIDEOS_PER_CREATOR:
            results[cid]["video_urls"].append(f"https://www.youtube.com/watch?v={vid}")
            results[cid]["video_titles"].append(title)
            results[cid]["video_ids"].append(vid)
    return list(results.values())


def get_channel_stats(youtube, channel_ids):
    if not channel_ids:
        return {}
    try:
        response = (
            youtube.channels()
            .list(
                part="statistics,snippet,brandingSettings",
                id=",".join(channel_ids),
            )
            .execute()
        )
    except Exception as e:
        print(f"  Warning: Stats error: {e}")
        return {}

    stats = {}
    for item in response.get("items", []):
        cid = item["id"]
        s = item.get("statistics", {})
        sn = item.get("snippet", {})
        bs = item.get("brandingSettings", {})
        custom_url = sn.get("customUrl", "")
        thumbs = sn.get("thumbnails", {})
        icon_url = (
            thumbs.get("high", {}).get("url")
            or thumbs.get("medium", {}).get("url")
            or thumbs.get("default", {}).get("url")
            or ""
        )
        stats[cid] = {
            "subscribers": int(s.get("subscriberCount", 0)),
            "total_views": int(s.get("viewCount", 0)),
            "video_count": int(s.get("videoCount", 0)),
            "country": sn.get("country", "Unknown"),
            "description": sn.get("description", "").lower(),
            "published_at": sn.get("publishedAt", ""),
            "custom_url": custom_url,
            "channel_title": sn.get("title", ""),  # authoritative name from channels API
            "youtube_icon_url": icon_url,
            "youtube_banner_url": bs.get("image", {}).get("bannerExternalUrl", ""),
        }
    return stats


def get_recent_titles(youtube, channel_id, max_results=10):
    try:
        response = (
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
        return [item["snippet"]["title"] for item in response.get("items", [])]
    except Exception as e:
        print(f"    Warning: Could not fetch titles: {e}")
        return []


def fetch_comments(youtube, video_id, max_results=MAX_COMMENTS):
    """Fetch top comments for a video."""
    try:
        response = (
            youtube.commentThreads()
            .list(
                part="snippet",
                videoId=video_id,
                maxResults=max_results,
                order="relevance",
                textFormat="plainText",
            )
            .execute()
        )
        comments = []
        for item in response.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"].lower()
            comments.append(text)
        return comments
    except Exception as e:
        print(f"      Warning: Could not fetch comments: {e}")
        return []


# ══════════════════════════════════════════════════════════════════════════════
# TRANSCRIPT FETCHER
# ══════════════════════════════════════════════════════════════════════════════


def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    return ""


def fetch_transcript(url, max_words=MAX_TRANSCRIPT_WORDS):
    vid = get_video_id(url)
    if not vid:
        return None
    try:
        ytt_api = YouTubeTranscriptApi()
        fetched = ytt_api.fetch(vid, languages=["en", "en-US", "en-GB"])
        text = " ".join([s.text for s in fetched])
        words = text.split()
        if len(words) > max_words:
            text = " ".join(words[:max_words])
        return text.lower()
    except (NoTranscriptFound, TranscriptsDisabled):
        return None
    except Exception as e:
        print(f"      Warning: transcript error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# PRE-FILTERS
# ══════════════════════════════════════════════════════════════════════════════


def load_gymshark_affiliates(path: Path | None = None) -> set[str]:
    """
    Load gymshark_creators_affiliates.csv and return a set of lowercase
    YouTube handles (without @) for fast membership testing.
    """
    if path is None:
        path = Path(__file__).resolve().parent.parent / "data" / "gymshark_creators_affiliates.csv"
    if not path.exists():
        return set()
    handles = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get("YouTube Handle", "").strip().lstrip("@").lower()
            if raw:
                handles.add(raw)
    return handles


def is_existing_partner(description, titles):
    combined = description + " ".join(titles).lower()
    for signal in EXISTING_PARTNER_SIGNALS:
        if signal in combined:
            return True, signal
    return False, ""


def has_clickbait_titles(titles):
    found = []
    combined = " ".join(titles).lower()
    for pattern in CLICKBAIT_TITLE_PATTERNS:
        if pattern in combined:
            found.append(pattern)
    return len(found) > 0, found


def posts_regularly(video_count, published_at):
    if not published_at or video_count < 5:
        return False
    try:
        start = datetime.strptime(published_at[:10], "%Y-%m-%d")
        months = max((datetime.today() - start).days / 30, 1)
        return (video_count / months) >= 2
    except Exception:
        return video_count >= 10


def classify_tier(subs):
    if subs < 50_000:
        return "nano"
    elif subs < 200_000:
        return "micro"
    elif subs < 600_000:
        return "mid"
    elif subs < 2_000_000:
        return "macro"
    else:
        return "mega"


def suggest_deal(tier):
    return {
        "nano": "gift_seeding",
        "micro": "affiliate",
        "mid": "paid_creative_partnership",
        "macro": "brand_ambassador",
        "mega": "co_created_collection",
    }.get(tier, "affiliate")


# ══════════════════════════════════════════════════════════════════════════════
# COMMENT SENTIMENT SCORER
# ══════════════════════════════════════════════════════════════════════════════


def score_comments(comments):
    """
    Score comment section for creator trust and purchase intent.
    Negative signals are about the CREATOR, not the product.
    """
    if not comments:
        return {
            "total_comments": 0,
            "positive_comment_count": 0,
            "negative_comment_count": 0,
            "purchase_intent_count": 0,
            "positive_comment_pct": 0.0,
            "negative_comment_pct": 0.0,
            "comment_sentiment_score": 2.0,
            "creator_trust_score": 2.0,
            "sample_positive": "none",
            "sample_negative": "none",
            "comment_samples": [],
            "comments_available": False,
        }

    pos_comments = []
    neg_comments = []
    intent_comments = []

    for comment in comments:
        is_pos = any(s in comment for s in COMMENT_POSITIVE)
        is_neg = any(s in comment for s in COMMENT_NEGATIVE)
        is_intent = any(s in comment for s in COMMENT_PURCHASE_INTENT)

        if is_pos:
            pos_comments.append(comment)
        if is_neg:
            neg_comments.append(comment)
        if is_intent:
            intent_comments.append(comment)

    total = len(comments)
    pos_pct = round(len(pos_comments) / total * 100, 1) if total > 0 else 0.0
    neg_pct = round(len(neg_comments) / total * 100, 1) if total > 0 else 0.0

    # Comment sentiment score (1-10)
    # More positive comments + purchase intent = higher score
    # Negative creator comments drag it down significantly
    sent_raw = 5 + (pos_pct / 20) + (len(intent_comments) * 0.5) - (neg_pct / 5)
    comment_sentiment = round(max(1.0, min(10.0, sent_raw)), 1)

    # Creator trust score (1-10)
    # Based specifically on creator-focused positive vs negative ratio
    trust_raw = 5 + (len(pos_comments) * 0.3) - (len(neg_comments) * 1.5)
    creator_trust = round(max(1.0, min(10.0, trust_raw)), 1)

    if len(comments) < 10:
        return {
            "total_comments": len(comments),
            "positive_comment_count": 0,
            "negative_comment_count": 0,
            "purchase_intent_count": 0,
            "positive_comment_pct": 0.0,
            "negative_comment_pct": 0.0,
            "comment_sentiment_score": 3.0,
            "creator_trust_score": 3.0,
            "sample_positive": "none",
            "sample_negative": "none",
            "comment_samples": comments,
            "comments_available": True,
        }

    return {
        "total_comments": total,
        "positive_comment_count": len(pos_comments),
        "negative_comment_count": len(neg_comments),
        "purchase_intent_count": len(intent_comments),
        "positive_comment_pct": pos_pct,
        "negative_comment_pct": neg_pct,
        "comment_sentiment_score": comment_sentiment,
        "creator_trust_score": creator_trust,
        "sample_positive": pos_comments[0][:100] if pos_comments else "none",
        "sample_negative": neg_comments[0][:100] if neg_comments else "none",
        "comment_samples": comments,
        "comments_available": True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# RULE-BASED TRANSCRIPT SCORER
# ══════════════════════════════════════════════════════════════════════════════


def count_signals(text, signals):
    found = []
    for signal in signals:
        # Word-boundary match so "tren" doesn't hit "trendy", "gear" doesn't hit "gearbox", etc.
        pattern = r"\b" + re.escape(signal.strip()) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            found.append(signal.strip())
    return found


def detect_niche(text, titles):
    combined = text + " ".join(titles).lower()
    scores = {}
    for niche, keywords in NICHE_SIGNALS.items():
        scores[niche] = sum(1 for kw in keywords if kw in combined)
    top = max(scores, key=scores.get)
    return top if scores[top] > 0 else "General Fitness"


def detect_content_style(text, titles):
    combined = text + " ".join(titles).lower()
    scores = {}
    for style, keywords in CONTENT_STYLE_SIGNALS.items():
        scores[style] = sum(1 for kw in keywords if kw in combined)
    top = max(scores, key=scores.get)
    return top if scores[top] > 0 else "Workout Vlog"


def score_creator_llm(
    all_text: str,
    titles: list,
    channel_title: str,
    stats: dict,
    comment_scores: dict,
    model: str = "api-llama-4-scout",
) -> dict:
    """
    Use the LLM to evaluate all scoring dimensions for a creator in one call.

    Replaces the rule-based keyword matching in score_creator when USE_LLM_SCORING=True.
    The LLM reads the transcript, video titles, and channel context holistically and
    returns structured scores for every dimension the pipeline needs.

    Falls back to rule-based scores if the LLM call fails so the pipeline never breaks.
    """
    from pydantic import BaseModel
    from utils.connect import ask_json

    class CreatorScoringResult(BaseModel):
        authenticity_score: int
        niche_score: int
        comment_sentiment_score: int
        audience_brand_risk: str  # HIGH | MEDIUM | LOW
        audience_brand_risk_reason: str
        audience_risk_level: str  # HIGH | MEDIUM | LOW (from comment categorization)
        comment_flag_categories: list[str]  # e.g., ["toxicity", "body_image", "spam"]
        comment_flag_breakdown: dict  # e.g., {"toxicity": 3, "body_image": 2, "spam": 1}
        brand_safety: str  # RED | AMBER | GREEN
        clickbait_detected: bool
        competitor_loyalty: bool
        existing_partner: bool
        signals_authentic_pos: list[str]
        signals_authentic_neg: list[str]
        brand_safety_notes: str
        clickbait_examples: list[str]
        competitor_brands: list[str]
        niche: str
        content_style: str
        audience_tone: str
        authenticity_reasoning: str
        brand_fit_reasoning: str

    subs = stats.get("subscribers", 0)
    er = stats.get("estimated_er_pct", 0)
    comment_samples = comment_scores.get("comment_samples", [])
    total_comments = comment_scores.get("total_comments", 0)
    if comment_samples:
        comments_section = f"ALL COMMENTS ({len(comment_samples)} total):\n" + "\n".join(
            f"  - {c[:120]}" for c in comment_samples
        )
    else:
        comments_section = "COMMENTS: no comment data available"

    sample_text = all_text[:2000]
    titles_str = "\n".join(f"  {i + 1}. {t}" for i, t in enumerate(titles[:20]))

    prompt = f"""You are a Gymshark brand partnerships analyst evaluating a fitness YouTube creator for potential collaboration.

CHANNEL: {channel_title}
SUBSCRIBERS: {subs:,}
ENGAGEMENT RATE: {er}%

RECENT VIDEO TITLES ({len(titles[:20])} most recent):
{titles_str}

{comments_section}

TRANSCRIPT EXCERPT:
{sample_text}

---

Evaluate this creator across every dimension below. Be strict and realistic — most creators score 5-7, not 9-10.

SCORING DIMENSIONS (all 1–10 integers):

authenticity_score — Does the creator speak as a genuine buyer/athlete, not a marketer?
  Look for: purchased themselves, honest pros/cons, real training talk, personal opinions
  Penalise: discount codes, "gifted by", PR language, "use my code", affiliate links
  1-3=heavy commercial language  5=neutral  8-10=clearly genuine and unsponsored

niche_score — Is this creator genuinely a gym-goer who makes real fitness content?
  Check BOTH the transcript AND the video titles above — titles are the strongest signal of what they consistently post about
  Look for: gym sessions, specific exercises (deadlifts, squats, hip thrusts), training programmes, workout vlogs, fitness progress
  Titles like "leg day", "push/pull/legs", "full body workout", "gym routine" are strong positive signals
  NOT enough: general wellness, lifestyle vlogging, or only wearing gym clothes without training context
  If titles are mostly fashion hauls, lifestyle, or unrelated topics — score low even if one transcript mentions the gym
  1-3=not a real fitness creator  5=some fitness content mixed with other topics  8-10=clearly posts gym content consistently

comment_sentiment_score — How positively does the audience respond to this creator in comments?
  Look for: trust signals ("so genuine", "you inspired me", "underrated"), purchase intent ("just ordered", "in my cart"), community warmth
  Penalise: distrust signals ("you've changed", "this is obviously sponsored", "sellout"), creator-directed negativity
  IMPORTANT: if fewer than 10 comments are shown, score 3 — insufficient audience engagement is itself a negative signal
  If no comments provided at all, score 2
  1-3=audience distrust, negativity, or insufficient engagement  5=neutral/mixed  8-10=strong positive community response

audience_brand_risk — Does the audience's comment section contain topics that could damage Gymshark's brand?
  This is separate from the creator's own content — it is about what the AUDIENCE talks about
  HIGH: visible toxic language, hate speech, extreme diet talk ("eat less", "starving"), body shaming, bullying in comments
  MEDIUM: some concerning patterns present but not dominant, or borderline content
  LOW: clean comment section with no brand risk signals
  If no comments available, set MEDIUM — cannot verify audience safety

COMMENT CATEGORY ANALYSIS:
Categorize flagged or concerning comments from the comment section above into:
- toxicity: hate speech, harassment, aggressive language
- body_image: unhealthy body standards, extreme dieting, shaming
- spam: bot-like or excessive promotional messages
- competitor_mention: mentions of competing fitness brands (Alphalete, Lululemon, YoungLA, etc.)

comment_flag_categories — list of category names that appear in the comments (empty list if none found)
comment_flag_breakdown — dict with count per category, e.g. {"toxicity": 2, "body_image": 1, "spam": 3}

AUDIENCE RISK LEVEL DECISION:
audience_risk_level — Set based on comment category breakdown:
- HIGH: if toxicity >= 3 comments OR body_image >= 3 comments OR total flagged >= 20% of comments shown
- MEDIUM: if toxicity 1-2 OR body_image 1-2 OR total flagged 8-20%
- LOW: if total flagged < 8% AND no toxicity
- UNKNOWN: if fewer than 10 comments available

BOOLEAN FLAGS:
brand_safety — RED (2+ serious risk signals: steroids, eating disorders, hate), AMBER (1 risk or 2+ clickbait), GREEN (clean)
clickbait_detected — true if titles/transcript contain unrealistic promises ("abs in 7 days", "guaranteed results")
competitor_loyalty — true if they actively promote Alphalete, Lululemon, YoungLA, AYBL, NVGTN, or similar competitors (2+ signals)
existing_partner — true if they appear to already be a Gymshark ambassador/affiliate/athlete

LIST FIELDS (empty list if none found):
signals_authentic_pos — exact phrases showing genuine purchase/training (up to 5)
signals_authentic_neg — exact phrases showing commercial/partnership language (up to 5)
clickbait_examples — specific clickbait phrases found (up to 3)
competitor_brands — specific competitor brands mentioned (up to 3)

TEXT FIELDS:
niche — one of: Weightlifting, Bodybuilding, Women's Fitness, Powerlifting, Calisthenics, HIIT, CrossFit, Gym Lifestyle, General Fitness
content_style — one of: Try-On Haul, Workout Vlog, Tutorial, Review, Transformation, Day-in-Life, Educational
audience_tone — one of: Motivational, Aspirational, Relatable
brand_safety_notes — one sentence explaining any safety concerns, or "No safety concerns"
authenticity_reasoning — one sentence explaining the authenticity score
brand_fit_reasoning — one sentence summarising overall Gymshark fit"""

    # Append top-performer context if profile is available
    if _PERFORMER_PROFILE:
        top_niche = _PERFORMER_PROFILE.get("top_niche", "")
        top_style = _PERFORMER_PROFILE.get("top_content_style", "")
        signals = _PERFORMER_PROFILE.get("common_buying_signals", [])
        niche_bonuses = _PERFORMER_PROFILE.get("scoring_adjustments", {}).get("niche_bonus", {})
        top_niches = [n for n, v in niche_bonuses.items() if v > 0.4]
        prompt += f"""

---
GYMSHARK PERFORMANCE CONTEXT (from existing partner campaign data):
Gymshark's highest-converting creators come from these niches: {", ".join(top_niches) if top_niches else top_niche}
Best-performing content style historically: {top_style}
Audience buying signals seen in top performers: {", ".join(signals[:5]) if signals else "N/A"}

When scoring niche_score and brand_fit_reasoning, weight creators in these niches
and content styles more heavily — campaign data shows they convert best for Gymshark."""

    try:
        result = ask_json(prompt, schema=CreatorScoringResult, model=model)
        return {
            "authenticity_score": max(1, min(10, int(result.authenticity_score))),
            "niche_score": max(1, min(10, int(result.niche_score))),
            "comment_sentiment_score": max(1, min(10, int(result.comment_sentiment_score))),
            "audience_brand_risk": result.audience_brand_risk
            if result.audience_brand_risk in ("HIGH", "MEDIUM", "LOW")
            else "MEDIUM",
            "audience_brand_risk_reason": result.audience_brand_risk_reason,
            "audience_risk_level": result.audience_risk_level
            if result.audience_risk_level in ("HIGH", "MEDIUM", "LOW", "UNKNOWN")
            else "UNKNOWN",
            "comment_flag_categories": result.comment_flag_categories or [],
            "comment_flag_breakdown": result.comment_flag_breakdown or {},
            "brand_safety": result.brand_safety if result.brand_safety in ("RED", "AMBER", "GREEN") else "AMBER",
            "clickbait_detected": bool(result.clickbait_detected),
            "competitor_loyalty": bool(result.competitor_loyalty),
            "existing_partner": bool(result.existing_partner),
            "signals_authentic_pos": result.signals_authentic_pos,
            "signals_authentic_neg": result.signals_authentic_neg,
            "brand_safety_notes": result.brand_safety_notes,
            "clickbait_examples": result.clickbait_examples,
            "competitor_brands": result.competitor_brands,
            "niche": result.niche,
            "content_style": result.content_style,
            "audience_tone": result.audience_tone,
            "authenticity_reasoning": result.authenticity_reasoning,
            "brand_fit_reasoning": result.brand_fit_reasoning,
            "scoring_method": "llm-based holistic scoring",
        }
    except Exception:
        # Full fallback to rule-based — never block the pipeline
        return None


def score_creator(transcripts, titles, channel_title, stats, comment_scores):
    """
    Score creator from transcript signals + comment sentiment + channel stats.
    When USE_LLM_SCORING=True the LLM evaluates all dimensions in one call;
    rule-based keyword matching is the fallback.
    """
    all_text = " ".join([t for t in transcripts if t]) + " " + " ".join(titles).lower()
    has_transcript = any(t is not None for t in transcripts)

    # ── LLM path (required — no fallback) ────────────────────────────────────
    llm = score_creator_llm(all_text, titles, channel_title, stats, comment_scores)

    if llm is None:
        raise RuntimeError(
            f"LLM scoring failed for {channel_title}. "
            "Check that TRITONAI_API_KEY is set and the LLM model is available."
        )

    # LLM gave us all the sub-scores — compute GFS from them
    # authenticity(40%) + comment_sentiment(30%) + niche_score(20%) + engagement_score(10%)
    comment_sentiment = llm["comment_sentiment_score"]
    subs = stats.get("subscribers", 1)
    tot_views = stats.get("total_views", 0)
    vid_count = max(stats.get("video_count", 1), 1)
    est_er = round(min((tot_views / vid_count / subs) * 100, 15.0), 2) if subs > 0 else 0.0
    if subs < 500_000 and est_er > 3.0:
        engagement_score = 9
    elif est_er > 5.0:
        engagement_score = 8
    elif est_er < 1.0:
        engagement_score = 5
    else:
        engagement_score = 7
    # Niche and content-style bonuses from analyze_top_performers.py profile
    _adjustments = _PERFORMER_PROFILE.get("scoring_adjustments", {})
    niche_bonus = _adjustments.get("niche_bonus", {}).get(llm["niche"], 0.0)
    style_bonus = _adjustments.get("content_style_bonus", {}).get(llm["content_style"], 0.0)

    fit_raw = (
        (llm["authenticity_score"] * 0.40)
        + (comment_sentiment * 0.30)
        + (llm["niche_score"] * 0.20)
        + (engagement_score * 0.10)
        + niche_bonus
        + style_bonus
        - (len(llm["clickbait_examples"]) * 1.5)
        - (2.0 if llm["brand_safety"] == "RED" else 1.0 if llm["brand_safety"] == "AMBER" else 0.0)
        - (len(llm["competitor_brands"]) * 1.0)
        - (len(llm["signals_authentic_neg"]) * 0.5)
    )
    brand_fit = round(max(1.0, min(10.0, fit_raw)), 1)
    outreach_recommended = (
        brand_fit >= MIN_BRAND_FIT_SCORE
        and llm["authenticity_score"] >= MIN_AUTHENTICITY_SCORE
        and llm["brand_safety"] != "RED"
        and llm["audience_brand_risk"] != "HIGH"
        and not llm["clickbait_detected"]
        and not llm["competitor_loyalty"]
        and not llm["existing_partner"]
    )
    subs = stats.get("subscribers", 1)
    tot_views = stats.get("total_views", 0)
    vid_count = max(stats.get("video_count", 1), 1)
    est_er = round(min((tot_views / vid_count / subs) * 100, 15.0), 2) if subs > 0 else 0.0

    return {
        "niche": llm["niche"],
        "content_style": llm["content_style"],
        "audience_tone": llm["audience_tone"],
        "authenticity_score": llm["authenticity_score"],
        "authenticity_reasoning": llm["authenticity_reasoning"],
        "niche_score": llm["niche_score"],
        "engagement_score": engagement_score,
        "gymshark_brand_fit": brand_fit,
        "brand_fit_reasoning": llm["brand_fit_reasoning"],
        "transcript_available": has_transcript,
        "signals_authentic_pos": llm["signals_authentic_pos"],
        "signals_authentic_neg": llm["signals_authentic_neg"],
        "audience_brand_risk": llm["audience_brand_risk"],
        "audience_brand_risk_reason": llm["audience_brand_risk_reason"],
        "audience_risk_level": llm["audience_risk_level"],
        "comment_flag_categories": llm["comment_flag_categories"],
        "comment_flag_breakdown": llm["comment_flag_breakdown"],
        "brand_safety": llm["brand_safety"],
        "brand_safety_notes": llm["brand_safety_notes"],
        "clickbait_detected": llm["clickbait_detected"],
        "clickbait_examples": llm["clickbait_examples"],
        "competitor_loyalty": llm["competitor_loyalty"],
        "competitor_brands": llm["competitor_brands"],
        "existing_partner": llm["existing_partner"],
        "red_flags": llm["brand_safety_notes"] if llm["brand_safety"] != "GREEN" else "none",
        "controversy_details": llm["brand_safety_notes"] if llm["brand_safety"] != "GREEN" else "none",
        "outreach_recommended": outreach_recommended,
        "estimated_er_pct": est_er,
        "scoring_method": "llm-holistic",
        "total_comments_analyzed": comment_scores.get("total_comments", 0),
        "positive_comment_pct": comment_scores.get("positive_comment_pct", 0.0),
        "negative_comment_pct": comment_scores.get("negative_comment_pct", 0.0),
        "purchase_intent_count": comment_scores.get("purchase_intent_count", 0),
        "comment_sentiment_score": llm["comment_sentiment_score"],
        "creator_trust_score": comment_scores.get("creator_trust_score", 5.0),
        "comment_reasoning": comment_scores.get("comment_reasoning", ""),
        "sample_positive_comment": comment_scores.get("sample_positive", "none"),
        "sample_negative_comment": comment_scores.get("sample_negative", "none"),
        "comments_available": comment_scores.get("comments_available", False),
    }


def build_row(channel, stats, scores, rank):
    subs = stats.get("subscribers", 0)
    tier = classify_tier(subs)

    return {
        "rank": rank,
        "creator_id": str(uuid.uuid4())[:8].upper(),
        "name": stats.get("channel_title") or channel["channel_title"],
        "youtube_handle": "@"
        + (stats.get("custom_url") or channel["channel_title"].lower().replace(" ", "")).lstrip("@"),
        "channel_id": channel.get("channel_id", ""),
        "youtube_channel_url": "https://www.youtube.com/"
        + (
            "@" + (stats.get("custom_url") or "").lstrip("@")
            if stats.get("custom_url")
            else f"channel/{channel.get('channel_id', '')}"
        ),
        "youtube_icon_url": stats.get("youtube_icon_url", ""),
        "youtube_banner_url": stats.get("youtube_banner_url", ""),
        "tier": tier,
        "suggested_deal_type": suggest_deal(tier),
        "niche": scores["niche"],
        "content_style": scores["content_style"],
        "audience_tone": scores["audience_tone"],
        "subscribers": subs,
        "total_views": stats.get("total_views", 0),
        "video_count": stats.get("video_count", 0),
        "estimated_er_pct": scores["estimated_er_pct"],
        "country": stats.get("country", "Unknown"),
        "gymshark_brand_fit": scores["gymshark_brand_fit"],
        "authenticity_score": scores["authenticity_score"],
        "niche_score": scores["niche_score"],
        "engagement_score": scores["engagement_score"],
        "brand_fit_reasoning": scores["brand_fit_reasoning"],
        "authenticity_reasoning": scores["authenticity_reasoning"],
        "signals_authentic_pos": scores["signals_authentic_pos"],
        "signals_authentic_neg": scores["signals_authentic_neg"],
        "transcript_available": scores["transcript_available"],
        "audience_brand_risk": scores["audience_brand_risk"],
        "audience_brand_risk_reason": scores["audience_brand_risk_reason"],
        "audience_risk_level": scores.get("audience_risk_level", "UNKNOWN"),
        "comment_flag_categories": scores.get("comment_flag_categories", []),
        "comment_flag_breakdown": scores.get("comment_flag_breakdown", {}),
        "brand_safety": scores["brand_safety"],
        "brand_safety_notes": scores["brand_safety_notes"],
        "clickbait_detected": scores["clickbait_detected"],
        "clickbait_examples": scores["clickbait_examples"],
        "competitor_loyalty": scores["competitor_loyalty"],
        "competitor_brands": scores["competitor_brands"],
        "existing_partner": scores["existing_partner"],
        "red_flags": scores["red_flags"],
        "controversy_details": scores["controversy_details"],
        "outreach_recommended": scores["outreach_recommended"],
        "scoring_method": scores["scoring_method"],
        # Comment fields
        "total_comments_analyzed": scores["total_comments_analyzed"],
        "positive_comment_pct": scores["positive_comment_pct"],
        "negative_comment_pct": scores["negative_comment_pct"],
        "purchase_intent_count": scores["purchase_intent_count"],
        "comment_sentiment_score": scores["comment_sentiment_score"],
        "creator_trust_score": scores["creator_trust_score"],
        "comment_reasoning": scores["comment_reasoning"],
        "sample_positive_comment": scores["sample_positive_comment"],
        "sample_negative_comment": scores["sample_negative_comment"],
        "comments_available": scores["comments_available"],
        "videos_analyzed": len(channel.get("video_urls", [])),
        "source": "YouTube organic mention — transcript + comment scoring",
        "date_added": datetime.today().strftime("%Y-%m-%d"),
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════


def main():
    print("=" * 65)
    print("Gymshark Creator Discovery")
    print("LLM-Based Holistic Scoring")
    print("Requires TRITONAI_API_KEY for model access")
    print("=" * 65)

    if "PASTE_YOUR" in YOUTUBE_API_KEY:
        print("\n❌ YouTube API key not set.")
        print("   Get one free at: https://console.cloud.google.com")
        print("   Enable: YouTube Data API v3")
        return

    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    print(f"\nChecking for saved progress...")
    checkpoint = load_checkpoint()

    # ── Steps 1-3: Search + filter ────────────────────────────────────────────
    if checkpoint.get("searches_done") and checkpoint.get("candidates"):
        print(f"\n[1-3/3] Loaded {len(checkpoint['candidates'])} candidates from checkpoint")
        candidates = [(c["channel"], c["stats"]) for c in checkpoint["candidates"]]
    else:
        print(f"\n[1/3] Searching YouTube...")
        all_channels = {}
        for query in SEARCH_QUERIES:
            print(f"  → '{query}'")
            for c in search_youtube(youtube, query, RESULTS_PER_QUERY):
                if c["channel_id"] not in all_channels:
                    all_channels[c["channel_id"]] = c
            time.sleep(0.5)
        print(f"  Found {len(all_channels)} unique channels")

        print(f"\n[2/3] Fetching channel statistics...")
        all_stats = {}
        ids = list(all_channels.keys())
        for i in range(0, len(ids), 50):
            all_stats.update(get_channel_stats(youtube, ids[i : i + 50]))
            time.sleep(0.3)

        print(f"\n[3/3] Pre-filtering...")
        affiliate_handles = load_gymshark_affiliates()
        candidates = []
        skipped = {"too_small": 0, "existing_partner": 0, "clickbait": 0, "irregular": 0, "no_stats": 0}

        for cid, channel in all_channels.items():
            stats = all_stats.get(cid, {})
            subs = stats.get("subscribers", 0)
            desc = stats.get("description", "")

            if not stats or subs == 0:
                skipped["no_stats"] += 1
                continue
            if subs < 1_000:
                skipped["too_small"] += 1
                continue
            if not posts_regularly(stats.get("video_count", 0), stats.get("published_at", "")):
                skipped["irregular"] += 1
                continue

            # Use authoritative name from full channel API when available
            display_name = stats.get("channel_title") or channel["channel_title"]
            print(f"  Checking: {display_name} ({subs:,} subs)")

            # Hard-filter: known Gymshark affiliates by YouTube handle
            custom_url = stats.get("custom_url", "").lstrip("@").lower()
            if custom_url and custom_url in affiliate_handles:
                print(f"    ✗ Gymshark affiliate ({custom_url})")
                skipped["existing_partner"] += 1
                continue

            titles = get_recent_titles(youtube, cid, TITLES_TO_SCAN)
            time.sleep(0.3)

            is_partner, signal = is_existing_partner(desc, titles)
            if is_partner:
                print(f"    ✗ Existing partner ({signal})")
                skipped["existing_partner"] += 1
                continue

            has_cb, cb_found = has_clickbait_titles(titles)
            if has_cb:
                print(f"    ✗ Clickbait titles: {cb_found[:2]}")
                skipped["clickbait"] += 1
                continue

            channel["recent_titles"] = titles
            candidates.append((channel, stats))
            print(f"    ✓ Passes pre-filter")

        print(f"\n  Passed: {len(candidates)}")
        for k, v in skipped.items():
            if v:
                print(f"  Skipped ({k}): {v}")

        checkpoint["candidates"] = [{"channel": ch, "stats": st} for ch, st in candidates]
        checkpoint["searches_done"] = True
        save_checkpoint(checkpoint)

    if not candidates:
        print("\n❌ No candidates found.")
        return

    # ── Scoring ───────────────────────────────────────────────────────────────
    already_done = checkpoint.get("done", {})
    print(f"\n[Scoring] Transcripts + comments for {len(candidates)} creators...\n")

    creator_rows = []

    for channel, stats in candidates:
        cid = channel["channel_id"]
        name = channel["channel_title"]
        subs = stats.get("subscribers", 0)
        titles = channel.get("recent_titles", [])

        if cid in already_done:
            print(f"  ↩ {name} — loaded from checkpoint")
            saved = already_done[cid]
            if saved:
                creator_rows.append((channel, stats, saved))
            continue

        print(f"  Scoring: {name} ({subs:,} subs)")

        # Fetch transcripts
        transcripts = []
        for i, url in enumerate(channel.get("video_urls", [])[:VIDEOS_PER_CREATOR]):
            print(f"    → Transcript {i + 1}...")
            transcript = fetch_transcript(url)
            transcripts.append(transcript)
            print(f"      {'✓ ' + str(len(transcript.split())) + ' words' if transcript else '✗ No transcript'}")
            time.sleep(0.5)

        # Fetch comments
        all_comments = []
        for i, vid_id in enumerate(channel.get("video_ids", [])[:VIDEOS_PER_CREATOR]):
            print(f"    → Comments video {i + 1}...")
            comments = fetch_comments(youtube, vid_id, MAX_COMMENTS)
            all_comments.extend(comments)
            print(f"      ✓ {len(comments)} comments fetched")
            time.sleep(0.3)

        # Score comments
        comment_scores = score_comments(all_comments)
        print(
            f"    → Comment sentiment: {comment_scores['positive_comment_pct']}% positive | "
            f"{comment_scores['purchase_intent_count']} purchase intent | "
            f"Trust: {comment_scores['creator_trust_score']}/10"
        )

        # Score creator — LLM or rule-based depending on USE_LLM_SCORING flag
        scores = score_creator(transcripts, titles, name, stats, comment_scores)

        # Final filters
        if scores["existing_partner"]:
            print(f"    ✗ Likely existing partner")
            checkpoint["done"][cid] = None
            save_checkpoint(checkpoint)
            continue
        if scores["brand_safety"] == "RED":
            print(f"    ✗ RED safety")
            checkpoint["done"][cid] = None
            save_checkpoint(checkpoint)
            continue
        if scores["clickbait_detected"]:
            print(f"    ✗ Clickbait detected")
            checkpoint["done"][cid] = None
            save_checkpoint(checkpoint)
            continue
        if scores["competitor_loyalty"]:
            print(f"    ✗ Competitor loyalty")
            checkpoint["done"][cid] = None
            save_checkpoint(checkpoint)
            continue
        if scores["gymshark_brand_fit"] < MIN_BRAND_FIT_SCORE:
            print(f"    ✗ Brand fit {scores['gymshark_brand_fit']}/10 below {MIN_BRAND_FIT_SCORE}")
            checkpoint["done"][cid] = None
            save_checkpoint(checkpoint)
            continue
        if scores["authenticity_score"] < MIN_AUTHENTICITY_SCORE:
            print(f"    ✗ Authenticity {scores['authenticity_score']}/10 below threshold")
            checkpoint["done"][cid] = None
            save_checkpoint(checkpoint)
            continue

        creator_rows.append((channel, stats, scores))
        checkpoint["done"][cid] = scores
        save_checkpoint(checkpoint)

        rec = "✓ RECOMMENDED" if scores["outreach_recommended"] else "~ REVIEW NEEDED"
        method = "transcript" if scores["transcript_available"] else "titles only"
        print(
            f"    {rec} | Fit: {scores['gymshark_brand_fit']}/10 | "
            f"Auth: {scores['authenticity_score']}/10 | "
            f"Comments: {scores['comment_sentiment_score']}/10 | "
            f"Safety: {scores['brand_safety']}"
        )

    if not creator_rows:
        print("\n❌ No creators passed filters. Try lowering MIN_BRAND_FIT_SCORE.")
        return

    # ── Sort and write ─────────────────────────────────────────────────────────
    creator_rows.sort(key=lambda x: x[2].get("gymshark_brand_fit", 0), reverse=True)
    final_rows = [build_row(ch, st, sc, i + 1) for i, (ch, st, sc) in enumerate(creator_rows)]

    FIELDS = [
        "rank",
        "creator_id",
        "name",
        "youtube_handle",
        "tier",
        "suggested_deal_type",
        "niche",
        "content_style",
        "audience_tone",
        "subscribers",
        "total_views",
        "video_count",
        "estimated_er_pct",
        "country",
        "gymshark_brand_fit",
        "authenticity_score",
        "niche_score",
        "engagement_score",
        "brand_fit_reasoning",
        "authenticity_reasoning",
        "signals_authentic_pos",
        "signals_authentic_neg",
        "transcript_available",
        "audience_brand_risk",
        "audience_brand_risk_reason",
        "brand_safety",
        "brand_safety_notes",
        "clickbait_detected",
        "clickbait_examples",
        "competitor_loyalty",
        "competitor_brands",
        "existing_partner",
        "red_flags",
        "controversy_details",
        "outreach_recommended",
        "audience_risk_level",
        "comment_flag_categories",
        "comment_flag_breakdown",
        "total_comments_analyzed",
        "positive_comment_pct",
        "negative_comment_pct",
        "purchase_intent_count",
        "comment_sentiment_score",
        "creator_trust_score",
        "comment_reasoning",
        "sample_positive_comment",
        "sample_negative_comment",
        "comments_available",
        "scoring_method",
        "videos_analyzed",
        "source",
        "date_added",
    ]

    with open("creators.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(final_rows)

    clear_checkpoint()

    recommended = sum(1 for r in final_rows if r["outreach_recommended"])
    avg_fit = sum(r["gymshark_brand_fit"] for r in final_rows) / len(final_rows)
    with_trans = sum(1 for r in final_rows if r["transcript_available"])
    with_comm = sum(1 for r in final_rows if r["comments_available"])

    print(f"\n{'=' * 65}")
    print(f"✓  {len(final_rows)} creators written to creators.csv")
    print(f"   Recommended for outreach:  {recommended}")
    print(f"   Avg brand-fit score:       {avg_fit:.1f}/10")
    print(f"   Scored with transcript:    {with_trans}/{len(final_rows)}")
    print(f"   Scored with comments:      {with_comm}/{len(final_rows)}")
    print(f"\n   Tier breakdown:")
    for tier in ["nano", "micro", "mid", "macro", "mega"]:
        count = sum(1 for r in final_rows if r["tier"] == tier)
        if count:
            print(f"   {tier:6s}: {count}")
    print(f"\n   Top 5 by brand fit:")
    for r in final_rows[:5]:
        print(
            f"   #{r['rank']} {r['name']:30s} "
            f"Fit: {r['gymshark_brand_fit']}/10 | "
            f"Comments: {r['comment_sentiment_score']}/10 | "
            f"{r['tier']} | {r['niche']}"
        )
    print(f"\n   No Gemini API required — checkpoint cleared")


if __name__ == "__main__":
    main()
