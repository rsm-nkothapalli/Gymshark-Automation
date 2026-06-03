"""
Tests for score_creator_llm and the USE_LLM_SCORING branch in score_creator.
Uses real LLM calls (api-llama-4-scout) — asserts on structure and valid
ranges, not exact values, since LLM output is non-deterministic.
Requires TRITONAI_API_KEY in .env.

All tests are marked @pytest.mark.integration and are skipped by the default
pytest run (see pyproject.toml addopts). Run explicitly with:
    uv run pytest -m integration tests/test_community_scoring.py
"""

import importlib.util
import os

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SCRIPT = os.path.join(_PROJECT_ROOT, "data", "collect_creators_gemin_2i.py")

spec = importlib.util.spec_from_file_location("collect_creators", _SCRIPT)
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

GENUINE_TRANSCRIPT = """
I bought this gymshark set with my own money — no one asked me to review this,
completely unsponsored. I've been wearing these leggings to the gym three times
a week for the past month. Honest thoughts: the fabric holds up really well after
washing, no pilling at all. The waistband sits perfectly during squats and hip thrusts.
Is it worth the money? I'd say yes for the quality, but let me know in the comments
what you think — are you a gymshark person or not? Your feedback genuinely helps
me decide what to review next. For my beginners out there, don't be intimidated —
everyone starts somewhere. Just showing up consistently is what matters.
"""

GENUINE_TITLES = [
    "I Bought Gymshark With My Own Money — Honest Review",
    "Full Week of Workouts | No Sponsor | Real Talk",
    "Squat Form Tips for Beginners | Let Me Know If This Helps",
]

COMMERCIAL_TRANSCRIPT = """
Use my code FITLIFE20 for 20% off! Gymshark sent me this PR package and I'm so
grateful — thank you gymshark for this amazing collaboration. Link in bio for
the affiliate discount. As a gymshark ambassador I get to share these exclusive
deals with you guys. This collab has been incredible and the brand is so generous.
"""

COMMERCIAL_TITLES = [
    "GYMSHARK HAUL | Use Code FITLIFE for 20% off!!",
    "Gymshark Ambassador Unboxing PR Package",
]

DEFAULT_STATS = {
    "subscribers": 50_000,
    "total_views": 2_000_000,
    "video_count": 80,
}

DEFAULT_COMMENTS = {
    "comments_available": True,
    "positive_comment_pct": 40.0,
    "purchase_intent_count": 3,
    "negative_comment_count": 1,
    "negative_comment_pct": 2.0,
    "comment_sentiment_score": 7.0,
    "creator_trust_score": 7.0,
    "total_comments": 50,
    "sample_positive": "love your content",
    "sample_negative": "none",
    "comment_reasoning": "mostly positive",
    "comment_samples": [
        "love your content, so real and genuine",
        "just ordered this because of your review!",
        "you inspired me to start going to the gym",
        "so helpful, thank you for being honest",
        "in my cart already, can't wait to try",
        "you're so authentic, no bs ever",
        "been watching for years, never let me down",
        "ordered the set you recommended, obsessed",
        "your reviews are the only ones I trust",
        "just started lifting because of you!",
    ],
}

VALID_NICHES = {
    "Weightlifting",
    "Bodybuilding",
    "Women's Fitness",
    "Powerlifting",
    "Calisthenics",
    "HIIT",
    "CrossFit",
    "Gym Lifestyle",
    "General Fitness",
}
VALID_STYLES = {
    "Try-On Haul",
    "Workout Vlog",
    "Tutorial",
    "Review",
    "Transformation",
    "Day-in-Life",
    "Educational",
}
VALID_TONES = {"Motivational", "Aspirational", "Relatable"}
VALID_SAFETY = {"RED", "AMBER", "GREEN"}


# ---------------------------------------------------------------------------
# score_creator_llm — structure and range tests (real LLM)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_llm_returns_dict_not_none():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None, "LLM returned None — check TRITONAI_API_KEY in .env"


@pytest.mark.integration
def test_llm_scores_are_integers_in_valid_range():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    for field in ("authenticity_score", "niche_score", "comment_sentiment_score"):
        assert isinstance(result[field], int), f"{field} should be int"
        assert 1 <= result[field] <= 10, f"{field}={result[field]} out of range"


@pytest.mark.integration
def test_llm_brand_safety_is_valid_label():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    assert result["brand_safety"] in VALID_SAFETY


@pytest.mark.integration
def test_llm_audience_brand_risk_is_valid_label():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    assert result["audience_brand_risk"] in {"HIGH", "MEDIUM", "LOW"}
    assert isinstance(result["audience_brand_risk_reason"], str) and result["audience_brand_risk_reason"]


@pytest.mark.integration
def test_llm_boolean_flags_are_booleans():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    for flag in ("clickbait_detected", "competitor_loyalty", "existing_partner"):
        assert isinstance(result[flag], bool), f"{flag} should be bool"


@pytest.mark.integration
def test_llm_list_fields_are_lists():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    for field in ("signals_authentic_pos", "signals_authentic_neg", "clickbait_examples", "competitor_brands"):
        assert isinstance(result[field], list), f"{field} should be list"


@pytest.mark.integration
def test_llm_text_fields_are_non_empty_strings():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    for field in ("niche", "content_style", "audience_tone", "authenticity_reasoning", "brand_fit_reasoning"):
        assert isinstance(result[field], str) and result[field], f"{field} should be non-empty string"


@pytest.mark.integration
def test_llm_niche_is_one_of_expected_values():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    assert result["niche"] in VALID_NICHES, f"Unexpected niche: {result['niche']}"


@pytest.mark.integration
def test_llm_content_style_is_one_of_expected_values():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    assert result["content_style"] in VALID_STYLES, f"Unexpected content_style: {result['content_style']}"


@pytest.mark.integration
def test_llm_scores_genuine_creator_higher_authenticity_than_commercial():
    """Genuine purchase language should score higher authenticity than commercial/ambassador language."""
    genuine = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "Genuine", DEFAULT_STATS, DEFAULT_COMMENTS)
    commercial = cc.score_creator_llm(
        COMMERCIAL_TRANSCRIPT, COMMERCIAL_TITLES, "Commercial", DEFAULT_STATS, DEFAULT_COMMENTS
    )
    assert genuine is not None and commercial is not None
    assert genuine["authenticity_score"] > commercial["authenticity_score"], (
        f"Expected genuine ({genuine['authenticity_score']}) > commercial ({commercial['authenticity_score']})"
    )


@pytest.mark.integration
def test_llm_detects_no_competitor_loyalty_for_genuine_creator():
    result = cc.score_creator_llm(GENUINE_TRANSCRIPT, GENUINE_TITLES, "Genuine", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result is not None
    assert result["competitor_loyalty"] is False


@pytest.mark.integration
def test_llm_returns_none_gracefully_on_bad_input():
    """Empty transcript and no titles should not raise — returns None or valid dict."""
    result = cc.score_creator_llm("", [], "Unknown", {}, {})
    # Either a valid dict or None (LLM failed) — must not raise
    assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# score_creator — LLM branch integration (USE_LLM_SCORING=True)
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_score_creator_llm_path_returns_gymshark_brand_fit(monkeypatch):
    monkeypatch.setattr(cc, "USE_LLM_SCORING", True)
    result = cc.score_creator([GENUINE_TRANSCRIPT], GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert "gymshark_brand_fit" in result
    assert 1.0 <= result["gymshark_brand_fit"] <= 10.0


@pytest.mark.integration
def test_score_creator_llm_path_scoring_method_label(monkeypatch):
    monkeypatch.setattr(cc, "USE_LLM_SCORING", True)
    result = cc.score_creator([GENUINE_TRANSCRIPT], GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert "llm" in result["scoring_method"].lower()


@pytest.mark.integration
def test_score_creator_llm_path_includes_risk_metadata(monkeypatch):
    monkeypatch.setattr(cc, "USE_LLM_SCORING", True)
    result = cc.score_creator([GENUINE_TRANSCRIPT], GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert result["audience_risk_level"] in {"HIGH", "MEDIUM", "LOW", "UNKNOWN"}
    assert isinstance(result["comment_flag_categories"], list)
    assert isinstance(result["comment_flag_breakdown"], dict)


@pytest.mark.integration
def test_score_creator_rule_based_path_unchanged(monkeypatch):
    monkeypatch.setattr(cc, "USE_LLM_SCORING", False)
    result = cc.score_creator([GENUINE_TRANSCRIPT], GENUINE_TITLES, "TestCreator", DEFAULT_STATS, DEFAULT_COMMENTS)
    assert "rule-based" in result["scoring_method"]
    assert 1.0 <= result["gymshark_brand_fit"] <= 10.0


# ---------------------------------------------------------------------------
# Predicted failure cases — LLM scorer specific failure modes
# FC: LLM thin-comment inflation (comment_sentiment inflated by cherry-picked samples)
# FC: LLM transcript bias over lifestyle title pattern (niche_score inflated)
# ---------------------------------------------------------------------------

# A creator with only 4 comments, all glowing.  The LLM prompt says "score 3 if fewer than 10
# comments" but natural language instructions can be overridden by strong positive evidence.
# The code-side guard in score_creator() must enforce the cap regardless.
THIN_COMMENTS = {
    "comments_available": True,
    "total_comments": 4,
    "comment_samples": [
        "love your content, so real and genuine",
        "just ordered this because of your review!",
        "you inspired me to start going to the gym",
        "your reviews are the only ones I trust",
    ],
    "positive_comment_pct": 100.0,
    "purchase_intent_count": 2,
    "negative_comment_count": 0,
    "negative_comment_pct": 0.0,
    "comment_sentiment_score": 9.0,
    "creator_trust_score": 9.0,
    "sample_positive": "love your content",
    "sample_negative": "none",
    "comment_reasoning": "very positive",
}

# Titles that are overwhelmingly lifestyle/fashion — gym is not the creator's primary topic.
LIFESTYLE_TITLES = [
    "GRWM for Autumn | Cozy Fall Vibes",
    "Coffee Shop Morning Routine | Studying Vlog",
    "What I Eat in a Day | Intuitive Eating",
    "My Skincare Routine | Glow Up Tips",
    "Autumn Outfit Haul | TikTok Finds Under £30",
    "Weekly Vlog | London Fashion Week",
    "Cozy At-Home Day | Self Care Sunday",
    "Room Decor Transformation | Aesthetic Makeover",
    "My Morning Routine | Productivity Tips",
    "Holiday Gift Guide | What I'm Getting Everyone",
]

# Transcript sounds vaguely gym-adjacent — enough to fool a surface-level check.
GYM_ADJACENT_TRANSCRIPT = """
I went to the gym this morning and had a great session.
I've been trying to be more consistent with fitness this year.
Wore my new gymshark set and felt really good in it.
Anyway, here's my current skincare routine for glowing skin...
"""


@pytest.mark.integration
def test_thin_comment_sample_capped_at_3_by_score_creator(monkeypatch):
    """Code guard in score_creator must cap comment_sentiment_score to ≤ 3 when total_comments < 10,
    regardless of how positively the LLM rates the cherry-picked sample comments."""
    monkeypatch.setattr(cc, "USE_LLM_SCORING", True)
    result = cc.score_creator([GENUINE_TRANSCRIPT], GENUINE_TITLES, "ThinCommentsCreator", DEFAULT_STATS, THIN_COMMENTS)
    assert result["comment_sentiment_score"] <= 3, (
        f"Expected comment_sentiment_score ≤ 3 for 4-comment sample, got {result['comment_sentiment_score']}. "
        "Thin comment samples inflate the 30%-weighted GFS and surface irrelevant creators."
    )


@pytest.mark.integration
def test_lifestyle_title_pattern_suppresses_niche_score():
    """LLM must score niche_score ≤ 5 when titles are overwhelmingly lifestyle/fashion
    even if the transcript contains passing gym mentions.  Titles are the primary signal
    of what a creator consistently posts about — transcript bias must not override them."""
    result = cc.score_creator_llm(
        GYM_ADJACENT_TRANSCRIPT, LIFESTYLE_TITLES, "LifestyleCreator", DEFAULT_STATS, DEFAULT_COMMENTS
    )
    assert result is not None
    assert result["niche_score"] <= 5, (
        f"Expected niche_score ≤ 5 for lifestyle-dominant titles, got {result['niche_score']}. "
        "A single gym mention in the transcript should not overcome 10 non-fitness titles."
    )
