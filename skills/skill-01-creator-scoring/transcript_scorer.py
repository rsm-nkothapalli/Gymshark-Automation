"""
transcript_scorer.py — LLM-based transcript scoring for Skill 01
-----------------------------------------------------------------
Replaces keyword-list counting in collect_creators_gemin_2i.py with a
single LLM call that reads the actual transcript and returns structured
scores for authenticity, community, brand safety, and brand fit.

The LLM understands context: "I tested Nike shoes" ≠ brand safety risk;
"I've been running sarms cycles" = risk — impossible to distinguish with
substring matching.

Usage
-----
  from skills.skills.skill-01-creator-scoring import transcript_scorer   # via importlib
  scores = transcript_scorer.score_transcript_llm(transcripts, titles, channel_title, stats, comment_scores)

The returned dict has the same keys as the keyword-based score_creator()
output so it is a drop-in replacement for the transcript-derived fields.
"""

import os
import sys

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# ensure project root is on path so utils.connect is importable
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from utils.connect import ask_json

MODEL = "api-llama-4-scout"

# Max transcript characters sent to the LLM — keeps token cost low
_MAX_TRANSCRIPT_CHARS = 3000
_MAX_TITLES = 10

# ---------------------------------------------------------------------------
# Structured output schema
# ---------------------------------------------------------------------------

COMPETITOR_BRANDS = [
    "alphalete",
    "lululemon",
    "youngla",
    "aybl",
    "nvgtn",
    "fleo",
    "echt activewear",
    "better bodies",
    "gym king",
]


class TranscriptScores(BaseModel):
    authenticity_score: float = Field(
        ge=1,
        le=10,
        description="How authentic and non-commercial the creator feels. 1=heavily sponsored/fake, 10=extremely genuine.",
    )
    authenticity_reasoning: str = Field(description="One sentence explaining the authenticity score.")
    community_score: float = Field(
        ge=1,
        le=10,
        description="How strongly the creator engages and builds community. 1=broadcast-only, 10=highly interactive.",
    )
    brand_safety: str = Field(
        description="GREEN, AMBER, or RED. GREEN=no concerns. AMBER=minor issues needing review. RED=clear disqualifier."
    )
    brand_safety_notes: str = Field(description="Specific reason for AMBER or RED, or 'No safety concerns' for GREEN.")
    signals_authentic_pos: str = Field(
        description="Comma-separated words/phrases from the transcript that signal authenticity, or 'none'."
    )
    signals_authentic_neg: str = Field(
        description="Comma-separated words/phrases that signal heavy commercialisation or inauthenticity, or 'none'."
    )
    clickbait_detected: bool = Field(
        description="True if video titles use misleading, sensationalist, or bait-and-switch language."
    )
    clickbait_examples: str = Field(description="Examples of clickbait titles found, or 'none'.")
    competitor_loyalty: bool = Field(
        description="True if the creator repeatedly promotes or expresses loyalty to a direct Gymshark competitor."
    )
    competitor_brands: str = Field(description="Competitor brand names found, or 'none'.")
    red_flags: str = Field(
        description="Specific content that is disqualifying (PEDs, eating disorder promotion, hate speech), or 'none'."
    )
    controversy_details: str = Field(
        description="Any controversy, drama, or cancel-culture events visible in the content, or 'none'."
    )
    niche: str = Field(
        description="Primary content niche. One of: Weightlifting, General Fitness, Bodybuilding, Running, Yoga/Pilates, Gym Lifestyle, Nutrition, CrossFit."
    )
    content_style: str = Field(
        description="Primary content format. One of: Tutorial, Vlog, Review, Challenge, Transformation, Motivation."
    )
    audience_tone: str = Field(
        description="The emotional register of the content. One of: Motivational, Educational, Aspirational, Relatable, Entertaining."
    )
    brand_fit_reasoning: str = Field(
        description="One or two sentences explaining how well this creator fits Gymshark's brand identity."
    )


# ---------------------------------------------------------------------------
# Main scoring function
# ---------------------------------------------------------------------------


def score_transcript_llm(
    transcripts: list[str],
    titles: list[str],
    channel_title: str,
    stats: dict,
    comment_scores: dict,
    model: str = MODEL,
) -> dict:
    """
    Score a creator's transcript content using the LLM.

    Parameters
    ----------
    transcripts   : list of raw transcript strings (one per video analysed)
    titles        : list of video title strings
    channel_title : YouTube channel name
    stats         : dict with subscribers, total_views, video_count
    comment_scores: dict from collect_comments.py (comment_sentiment_score, etc.)
    model         : LLM model id

    Returns
    -------
    dict with the same keys as score_creator() — compatible drop-in replacement
    for the transcript-derived portion of that function.
    """
    # --- build transcript excerpt (keep token cost low) ---
    combined_transcript = " ".join(t for t in transcripts if t)[:_MAX_TRANSCRIPT_CHARS]
    title_sample = "\n".join(f"  - {t}" for t in titles[:_MAX_TITLES])
    has_transcript = bool(combined_transcript.strip())

    # --- niche_alignment_score stays rule-based (pure engagement maths) ---
    subs = stats.get("subscribers", 1)
    tot_views = stats.get("total_views", 0)
    vid_count = max(stats.get("video_count", 1), 1)
    avg_views = tot_views / vid_count
    est_er = round(min((avg_views / subs) * 100, 15.0), 2) if subs > 0 else 0.0

    if subs < 500_000 and est_er > 3.0:
        niche_score = 9
    elif est_er > 5.0:
        niche_score = 8
    elif est_er < 1.0:
        niche_score = 5
    else:
        niche_score = 7

    # --- build LLM prompt ---
    transcript_section = (
        f"TRANSCRIPT EXCERPT:\n{combined_transcript}"
        if has_transcript
        else "TRANSCRIPT: Not available — score from titles and channel name only."
    )

    competitor_list = ", ".join(COMPETITOR_BRANDS)

    prompt = f"""You are a Gymshark influencer marketing analyst. Evaluate this YouTube fitness creator for brand partnership potential.

CHANNEL: {channel_title}
SUBSCRIBERS: {stats.get("subscribers", "unknown"):,}

VIDEO TITLES (sample):
{title_sample}

{transcript_section}

GYMSHARK BRAND VALUES: authentic, community-first, performance-driven, inclusive fitness lifestyle. NOT: supplement-heavy, diet culture, shock content, or creators loyal to direct competitors.

COMPETITOR BRANDS TO CHECK FOR: {competitor_list}

Score this creator on every field in the schema. Be specific — cite actual words or phrases from the transcript/titles as evidence. Do not be lenient: a creator who promotes PEDs, eating disorders, or hate speech is RED regardless of their subscriber count."""

    # --- call LLM with structured output ---
    llm_scores: TranscriptScores = ask_json(prompt, schema=TranscriptScores, model=model)

    # --- compute GFS using same weighted formula as rule-based scorer ---
    auth_score = round(max(1.0, min(10.0, llm_scores.authenticity_score)), 1)
    comm_score = round(max(1.0, min(10.0, llm_scores.community_score)), 1)
    comment_sentiment = comment_scores.get("comment_sentiment_score", 5.0)

    safety_penalty = {"GREEN": 0, "AMBER": 2.0, "RED": 4.0}.get(llm_scores.brand_safety.upper(), 0)
    clickbait_penalty = 1.5 if llm_scores.clickbait_detected else 0.0
    competitor_penalty = 1.0 if llm_scores.competitor_loyalty else 0.0

    fit_raw = (
        (auth_score * 0.30)
        + (comment_sentiment * 0.25)
        + (niche_score * 0.20)
        + (comm_score * 0.15)
        + (5 * 0.10)  # production quality baseline
        - safety_penalty
        - clickbait_penalty
        - competitor_penalty
    )
    brand_fit = round(max(1.0, min(10.0, fit_raw)), 1)

    # --- outreach eligibility (same thresholds as collect_creators_gemin_2i.py) ---
    _MIN_BRAND_FIT = 5
    _MIN_AUTH = 5

    outreach_recommended = (
        brand_fit >= _MIN_BRAND_FIT
        and auth_score >= _MIN_AUTH
        and llm_scores.brand_safety.upper() != "RED"
        and not llm_scores.clickbait_detected
        and not llm_scores.competitor_loyalty
    )

    # build comment reasoning (same as rule-based)
    if comment_scores.get("comments_available"):
        comment_reason = (
            f"{comment_scores['positive_comment_pct']}% positive, "
            f"{comment_scores['negative_comment_count']} creator-negative flags, "
            f"{comment_scores['purchase_intent_count']} purchase intent signals"
        )
    else:
        comment_reason = "Comments unavailable — disabled or restricted"

    return {
        "niche": llm_scores.niche,
        "content_style": llm_scores.content_style,
        "audience_tone": llm_scores.audience_tone,
        "authenticity_score": auth_score,
        "authenticity_reasoning": llm_scores.authenticity_reasoning,
        "community_score": comm_score,
        "niche_alignment_score": niche_score,
        "production_quality": 5,
        "gymshark_brand_fit": brand_fit,
        "brand_fit_reasoning": llm_scores.brand_fit_reasoning,
        "transcript_available": has_transcript,
        "signals_authentic_pos": llm_scores.signals_authentic_pos,
        "signals_authentic_neg": llm_scores.signals_authentic_neg,
        "brand_safety": llm_scores.brand_safety.upper(),
        "brand_safety_notes": llm_scores.brand_safety_notes,
        "clickbait_detected": llm_scores.clickbait_detected,
        "clickbait_examples": llm_scores.clickbait_examples,
        "competitor_loyalty": llm_scores.competitor_loyalty,
        "competitor_brands": llm_scores.competitor_brands,
        "existing_partner": False,
        "red_flags": llm_scores.red_flags,
        "controversy_details": llm_scores.controversy_details,
        "outreach_recommended": outreach_recommended,
        "estimated_er_pct": est_er,
        "scoring_method": "llm-transcript" if has_transcript else "llm-titles-only",
        # comment fields pass through unchanged
        "total_comments_analyzed": comment_scores.get("total_comments", 0),
        "positive_comment_pct": comment_scores.get("positive_comment_pct", 0.0),
        "negative_comment_pct": comment_scores.get("negative_comment_pct", 0.0),
        "purchase_intent_count": comment_scores.get("purchase_intent_count", 0),
        "comment_sentiment_score": comment_scores.get("comment_sentiment_score", 5.0),
        "creator_trust_score": comment_scores.get("creator_trust_score", 5.0),
        "comment_reasoning": comment_reason,
        "sample_positive_comment": comment_scores.get("sample_positive", "none"),
        "sample_negative_comment": comment_scores.get("sample_negative", "none"),
        "comments_available": comment_scores.get("comments_available", False),
    }
