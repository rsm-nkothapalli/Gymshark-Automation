"""
Tests for skills/skills/skill-01-creator-scoring/transcript_scorer.py

LLM calls are mocked via patch.object so no real API key is needed.
Tests verify: schema parsing, GFS formula, outreach eligibility logic,
fallback behaviour for missing transcripts, and correct key names in output.
"""

import importlib.util
import os
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Load module via importlib (hyphenated directory path)
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "transcript_scorer",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "skills",
            "skill-01-creator-scoring",
            "transcript_scorer.py",
        )
    ),
)
ts = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ts)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _llm_response(**overrides) -> ts.TranscriptScores:
    """Return a valid TranscriptScores object with safe defaults."""
    defaults = dict(
        authenticity_score=8.0,
        authenticity_reasoning="Shows honest reviews and personal fitness journey.",
        community_score=7.0,
        brand_safety="GREEN",
        brand_safety_notes="No safety concerns",
        signals_authentic_pos="honest review, my honest opinion",
        signals_authentic_neg="none",
        clickbait_detected=False,
        clickbait_examples="none",
        competitor_loyalty=False,
        competitor_brands="none",
        red_flags="none",
        controversy_details="none",
        niche="General Fitness",
        content_style="Vlog",
        audience_tone="Motivational",
        brand_fit_reasoning="Authentic lifestyle content aligns with Gymshark community values.",
    )
    defaults.update(overrides)
    return ts.TranscriptScores(**defaults)


def _stats(**overrides) -> dict:
    base = {"subscribers": 50_000, "total_views": 5_000_000, "video_count": 100}
    base.update(overrides)
    return base


def _comment_scores(**overrides) -> dict:
    base = {
        "comment_sentiment_score": 7.0,
        "creator_trust_score": 7.0,
        "positive_comment_pct": 80.0,
        "negative_comment_pct": 5.0,
        "negative_comment_count": 5,
        "purchase_intent_count": 3,
        "total_comments": 100,
        "comments_available": True,
        "sample_positive": "Great video!",
        "sample_negative": "none",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Return value completeness
# ---------------------------------------------------------------------------


def test_returns_all_required_keys():
    with patch.object(ts, "ask_json", return_value=_llm_response()):
        result = ts.score_transcript_llm(
            transcripts=["I love training and honest fitness content."],
            titles=["My workout routine"],
            channel_title="FitCreator",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )

    required = {
        "niche",
        "content_style",
        "audience_tone",
        "authenticity_score",
        "authenticity_reasoning",
        "community_score",
        "niche_alignment_score",
        "production_quality",
        "gymshark_brand_fit",
        "brand_fit_reasoning",
        "transcript_available",
        "signals_authentic_pos",
        "signals_authentic_neg",
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
        "estimated_er_pct",
        "scoring_method",
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
    }
    assert required.issubset(result.keys()), f"Missing keys: {required - result.keys()}"


# ---------------------------------------------------------------------------
# GFS formula
# ---------------------------------------------------------------------------


def test_gfs_green_no_penalties():
    with patch.object(
        ts,
        "ask_json",
        return_value=_llm_response(
            authenticity_score=8.0,
            community_score=7.0,
            brand_safety="GREEN",
            clickbait_detected=False,
            competitor_loyalty=False,
        ),
    ):
        result = ts.score_transcript_llm(
            transcripts=["workout content"],
            titles=["Leg day"],
            channel_title="Fit",
            stats=_stats(subscribers=50_000, total_views=5_000_000, video_count=100),
            comment_scores=_comment_scores(comment_sentiment_score=7.0),
        )
    assert result["gymshark_brand_fit"] >= 6.0


def test_gfs_red_safety_gets_heavy_penalty():
    with patch.object(
        ts,
        "ask_json",
        return_value=_llm_response(
            authenticity_score=9.0,
            community_score=9.0,
            brand_safety="RED",
            brand_safety_notes="Promotes steroid use openly",
            red_flags="steroids, sarms mentioned positively",
        ),
    ):
        result = ts.score_transcript_llm(
            transcripts=["I use sarms daily"],
            titles=["My PED stack"],
            channel_title="JuicedCreator",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )
    # RED penalty (-4.0) should noticeably lower GFS
    assert result["gymshark_brand_fit"] < 8.0


def test_gfs_clamped_between_1_and_10():
    # Worst case — everything bad
    with patch.object(
        ts,
        "ask_json",
        return_value=_llm_response(
            authenticity_score=1.0,
            community_score=1.0,
            brand_safety="RED",
            clickbait_detected=True,
            competitor_loyalty=True,
        ),
    ):
        result = ts.score_transcript_llm(
            transcripts=[""],
            titles=[],
            channel_title="Bad",
            stats=_stats(subscribers=1, total_views=1, video_count=1),
            comment_scores=_comment_scores(comment_sentiment_score=1.0),
        )
    assert 1.0 <= result["gymshark_brand_fit"] <= 10.0


# ---------------------------------------------------------------------------
# Outreach eligibility
# ---------------------------------------------------------------------------


def test_outreach_recommended_when_all_clear():
    with patch.object(
        ts,
        "ask_json",
        return_value=_llm_response(
            authenticity_score=8.0,
            brand_safety="GREEN",
            clickbait_detected=False,
            competitor_loyalty=False,
        ),
    ):
        result = ts.score_transcript_llm(
            transcripts=["great content"],
            titles=["Workout"],
            channel_title="FitChannel",
            stats=_stats(),
            comment_scores=_comment_scores(comment_sentiment_score=7.0),
        )
    assert result["outreach_recommended"] is True


def test_outreach_not_recommended_when_red():
    with patch.object(
        ts,
        "ask_json",
        return_value=_llm_response(
            brand_safety="RED",
            red_flags="steroid promotion",
        ),
    ):
        result = ts.score_transcript_llm(
            transcripts=["sarms content"],
            titles=["PED video"],
            channel_title="JuicedChannel",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )
    assert result["outreach_recommended"] is False


def test_outreach_not_recommended_when_competitor_loyal():
    with patch.object(
        ts,
        "ask_json",
        return_value=_llm_response(
            competitor_loyalty=True,
            competitor_brands="alphalete",
        ),
    ):
        result = ts.score_transcript_llm(
            transcripts=["alphalete content"],
            titles=["Alphalete haul"],
            channel_title="AlphaleteCreator",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )
    assert result["outreach_recommended"] is False


# ---------------------------------------------------------------------------
# Transcript availability
# ---------------------------------------------------------------------------


def test_transcript_available_true_when_text_present():
    with patch.object(ts, "ask_json", return_value=_llm_response()):
        result = ts.score_transcript_llm(
            transcripts=["actual transcript text here"],
            titles=["Video"],
            channel_title="C",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )
    assert result["transcript_available"] is True


def test_transcript_available_false_when_empty():
    with patch.object(ts, "ask_json", return_value=_llm_response()):
        result = ts.score_transcript_llm(
            transcripts=["", None],
            titles=["Video"],
            channel_title="C",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )
    assert result["transcript_available"] is False


def test_scoring_method_reflects_transcript_availability():
    with patch.object(ts, "ask_json", return_value=_llm_response()):
        with_transcript = ts.score_transcript_llm(
            transcripts=["real text"],
            titles=["V"],
            channel_title="C",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )
        without_transcript = ts.score_transcript_llm(
            transcripts=[""],
            titles=["V"],
            channel_title="C",
            stats=_stats(),
            comment_scores=_comment_scores(),
        )
    assert with_transcript["scoring_method"] == "llm-transcript"
    assert without_transcript["scoring_method"] == "llm-titles-only"


# ---------------------------------------------------------------------------
# Engagement-based niche_alignment_score (rule-based, not LLM)
# ---------------------------------------------------------------------------


def test_niche_score_high_for_small_channel_high_er():
    # subscribers < 500k and ER > 3% → niche_score = 9
    with patch.object(ts, "ask_json", return_value=_llm_response()):
        result = ts.score_transcript_llm(
            transcripts=["content"],
            titles=["V"],
            channel_title="C",
            stats={"subscribers": 10_000, "total_views": 500_000, "video_count": 10},
            comment_scores=_comment_scores(),
        )
    assert result["niche_alignment_score"] == 9


def test_niche_score_low_for_tiny_er():
    with patch.object(ts, "ask_json", return_value=_llm_response()):
        result = ts.score_transcript_llm(
            transcripts=["content"],
            titles=["V"],
            channel_title="C",
            stats={"subscribers": 1_000_000, "total_views": 5_000, "video_count": 100},
            comment_scores=_comment_scores(),
        )
    assert result["niche_alignment_score"] == 5


# ---------------------------------------------------------------------------
# Comments pass-through
# ---------------------------------------------------------------------------


def test_comment_fields_pass_through_unchanged():
    comments = _comment_scores(
        total_comments=200,
        positive_comment_pct=90.0,
        purchase_intent_count=10,
        comment_sentiment_score=8.5,
    )
    with patch.object(ts, "ask_json", return_value=_llm_response()):
        result = ts.score_transcript_llm(
            transcripts=["text"],
            titles=["V"],
            channel_title="C",
            stats=_stats(),
            comment_scores=comments,
        )
    assert result["total_comments_analyzed"] == 200
    assert result["positive_comment_pct"] == 90.0
    assert result["purchase_intent_count"] == 10
    assert result["comment_sentiment_score"] == 8.5
