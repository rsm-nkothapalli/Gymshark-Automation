"""
Tests for data/analyze_top_performers.py

LLM calls and YouTube API calls are not tested here.
All pure-logic functions are covered.
"""

import csv
import io
import os
import sys
import importlib.util

import pytest

# Load module directly — data/ folder isn't a package
_spec = importlib.util.spec_from_file_location(
    "analyze_top_performers",
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "data", "analyze_top_performers.py")
    ),
)
atp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(atp)


# ── load_campaign_metrics ─────────────────────────────────────────────────────

SAMPLE_CAMPAIGNS = """campaign_id,creator_id,creator_name,tier,deal_type,platform,campaign_start,campaign_end,status,promo_code,budget_gbp,reach,impressions,total_engagements,utm_clicks,promo_redemptions,revenue_attributed_gbp,roi_x,avg_order_value_gbp,renewal_recommended
C001,EP001,Alice,micro,affiliate,YouTube,2025-01-01,2025-03-01,completed,GSALIC11,1000,50000,80000,5000,2000,1200,8000,8.0,6.67,Yes
C002,EP001,Alice,micro,affiliate,YouTube,2025-04-01,2025-06-01,completed,GSALIC22,1200,60000,90000,6000,2400,1500,9600,8.0,6.40,Yes
C003,EP002,Bob,macro,brand_ambassador,YouTube,2025-01-01,2025-06-01,completed,GSBOB11,20000,400000,800000,80000,15000,8000,100000,5.0,12.50,Yes
"""

SAMPLE_PARTNERS = """creator_id,name,youtube_handle,tier,niche,subscribers,country,estimated_er_pct,deal_type,partner_since
EP001,Alice,@alice,micro,Women's Fitness,80000,GB,11.0,affiliate,2023-01-01
EP002,Bob,@bob,macro,Bodybuilding,600000,US,6.0,brand_ambassador,2022-01-01
"""


def _write_temp_csv(tmp_path, filename, content):
    p = tmp_path / filename
    p.write_text(content)
    return str(p)


def test_load_campaign_metrics_basic(tmp_path):
    camp = _write_temp_csv(tmp_path, "campaigns.csv", SAMPLE_CAMPAIGNS)
    parts = _write_temp_csv(tmp_path, "partners.csv", SAMPLE_PARTNERS)
    metrics = atp.load_campaign_metrics(camp, parts)
    assert "EP001" in metrics
    assert "EP002" in metrics


def test_load_campaign_metrics_aggregates_multiple_campaigns(tmp_path):
    camp = _write_temp_csv(tmp_path, "campaigns.csv", SAMPLE_CAMPAIGNS)
    parts = _write_temp_csv(tmp_path, "partners.csv", SAMPLE_PARTNERS)
    metrics = atp.load_campaign_metrics(camp, parts)
    assert metrics["EP001"]["campaign_count"] == 2


def test_load_campaign_metrics_avg_roi(tmp_path):
    camp = _write_temp_csv(tmp_path, "campaigns.csv", SAMPLE_CAMPAIGNS)
    parts = _write_temp_csv(tmp_path, "partners.csv", SAMPLE_PARTNERS)
    metrics = atp.load_campaign_metrics(camp, parts)
    assert metrics["EP001"]["avg_roi_x"] == 8.0


def test_load_campaign_metrics_conversion_rate(tmp_path):
    camp = _write_temp_csv(tmp_path, "campaigns.csv", SAMPLE_CAMPAIGNS)
    parts = _write_temp_csv(tmp_path, "partners.csv", SAMPLE_PARTNERS)
    metrics = atp.load_campaign_metrics(camp, parts)
    # EP001: total redemptions=2700, total clicks=4400
    assert metrics["EP001"]["conversion_rate"] == round(2700 / 4400, 3)


def test_load_campaign_metrics_niche_from_partners(tmp_path):
    camp = _write_temp_csv(tmp_path, "campaigns.csv", SAMPLE_CAMPAIGNS)
    parts = _write_temp_csv(tmp_path, "partners.csv", SAMPLE_PARTNERS)
    metrics = atp.load_campaign_metrics(camp, parts)
    assert metrics["EP001"]["niche"] == "Women's Fitness"
    assert metrics["EP002"]["niche"] == "Bodybuilding"


# ── rank_creators ─────────────────────────────────────────────────────────────

def test_rank_creators_orders_by_roi():
    metrics = {
        "A": {"name": "Alice", "avg_roi_x": 8.0, "conversion_rate": 0.6, "tier": "micro", "niche": "Women's Fitness", "deal_type": "affiliate", "campaign_count": 2, "cpa_gbp": 1.0, "youtube_handle": ""},
        "B": {"name": "Bob", "avg_roi_x": 5.0, "conversion_rate": 0.4, "tier": "macro", "niche": "Bodybuilding", "deal_type": "brand_ambassador", "campaign_count": 1, "cpa_gbp": 2.5, "youtube_handle": ""},
        "C": {"name": "Carol", "avg_roi_x": 6.5, "conversion_rate": None, "tier": "mid", "niche": "Gym Lifestyle", "deal_type": "paid_creative_partnership", "campaign_count": 1, "cpa_gbp": None, "youtube_handle": ""},
    }
    ranked = atp.rank_creators(metrics, top_n=3)
    assert ranked[0]["name"] == "Alice"
    assert ranked[1]["name"] == "Carol"
    assert ranked[2]["name"] == "Bob"


def test_rank_creators_respects_top_n():
    metrics = {str(i): {"name": f"C{i}", "avg_roi_x": float(i), "conversion_rate": None, "tier": "micro", "niche": "", "deal_type": "affiliate", "campaign_count": 1, "cpa_gbp": None, "youtube_handle": ""} for i in range(10)}
    ranked = atp.rank_creators(metrics, top_n=3)
    assert len(ranked) == 3


def test_rank_creators_empty():
    assert atp.rank_creators({}, top_n=5) == []


# ── categorize_video ──────────────────────────────────────────────────────────

def test_categorize_sponsored_title():
    assert atp.categorize_video("Gymshark haul #ad try on") == "sponsored"


def test_categorize_sponsored_transcript():
    assert atp.categorize_video("new gymshark items", "use my code for 10% off") == "sponsored"


def test_categorize_haul():
    assert atp.categorize_video("Gymshark haul 2025 try on") == "haul"


def test_categorize_workout():
    assert atp.categorize_video("Full body workout vlog") == "workout"


def test_categorize_tutorial():
    assert atp.categorize_video("How to deadlift for beginners") == "tutorial"


def test_categorize_review():
    assert atp.categorize_video("Honest review — is it worth it?") == "review"


def test_categorize_other():
    assert atp.categorize_video("Day at the beach with my dog") == "other"


def test_categorize_sponsored_takes_priority_over_haul():
    # A sponsored haul should still be classified as sponsored
    assert atp.categorize_video("Gymshark gifted haul try on") == "sponsored"


# ── calculate_view_patterns ───────────────────────────────────────────────────

SAMPLE_VIDEOS = [
    {"title": "Leg day vlog", "views": 80000, "category": "workout"},
    {"title": "Arm workout", "views": 60000, "category": "workout"},
    {"title": "How to squat", "views": 120000, "category": "tutorial"},
    {"title": "Gymshark haul #ad", "views": 40000, "category": "sponsored"},
    {"title": "Gymshark haul #ad 2", "views": 35000, "category": "sponsored"},
]


def test_calculate_view_patterns_avg_by_category():
    result = atp.calculate_view_patterns(SAMPLE_VIDEOS)
    assert result["avg_views_by_category"]["workout"] == 70000
    assert result["avg_views_by_category"]["tutorial"] == 120000
    assert result["avg_views_by_category"]["sponsored"] == 37500


def test_calculate_view_patterns_best_organic():
    result = atp.calculate_view_patterns(SAMPLE_VIDEOS)
    assert result["best_organic_category"] == "tutorial"


def test_calculate_view_patterns_sponsored_gap():
    result = atp.calculate_view_patterns(SAMPLE_VIDEOS)
    # sponsored avg = 37500, organic avg = (70000+120000)/2 = 95000
    # gap = (37500 - 95000) / 95000 * 100 = -60.5%
    assert result["sponsored_organic_gap_pct"] == pytest.approx(-60.5, abs=0.2)


def test_calculate_view_patterns_empty():
    assert atp.calculate_view_patterns([]) == {}


def test_calculate_view_patterns_no_sponsored():
    videos = [
        {"title": "Workout", "views": 50000, "category": "workout"},
        {"title": "Tutorial", "views": 80000, "category": "tutorial"},
    ]
    result = atp.calculate_view_patterns(videos)
    assert result["sponsored_organic_gap_pct"] is None
    assert result["best_organic_category"] == "tutorial"


def test_calculate_view_patterns_total_count():
    result = atp.calculate_view_patterns(SAMPLE_VIDEOS)
    assert result["total_videos_analyzed"] == 5


# ── _composite_weight ─────────────────────────────────────────────────────────

def test_composite_weight_uses_all_three_metrics():
    creator = {"avg_roi_x": 8.0, "conversion_rate": 0.6, "cpa_gbp": 1.0}
    w = atp._composite_weight(creator, max_roi=8.0, max_cr=0.6, min_cpa=1.0)
    assert w == pytest.approx(1.0, abs=0.01)


def test_composite_weight_none_conversion_rate():
    # Non-UTM deals have no conversion_rate — should still produce a weight
    creator = {"avg_roi_x": 5.0, "conversion_rate": None, "cpa_gbp": None}
    w = atp._composite_weight(creator, max_roi=5.0, max_cr=1.0, min_cpa=1.0)
    assert w > 0


def test_composite_weight_roi_only():
    creator = {"avg_roi_x": 4.0, "conversion_rate": None, "cpa_gbp": None}
    # Only ROI contributes (50%) — rest is 0
    w = atp._composite_weight(creator, max_roi=8.0, max_cr=0.0, min_cpa=0.0)
    assert w == pytest.approx(0.25, abs=0.01)  # 4/8 * 0.5


def test_composite_weight_high_cpa_scores_lower():
    cheap = {"avg_roi_x": 5.0, "conversion_rate": 0.5, "cpa_gbp": 1.0}
    expensive = {"avg_roi_x": 5.0, "conversion_rate": 0.5, "cpa_gbp": 10.0}
    w_cheap = atp._composite_weight(cheap, max_roi=5.0, max_cr=0.5, min_cpa=1.0)
    w_expensive = atp._composite_weight(expensive, max_roi=5.0, max_cr=0.5, min_cpa=1.0)
    assert w_cheap > w_expensive


# ── build_scoring_adjustments ─────────────────────────────────────────────────

SAMPLE_ANALYSES = [
    {"name": "Alice", "niche": "Women's Fitness", "primary_content_style": "Workout Vlog", "avg_roi_x": 8.0, "conversion_rate": 0.6, "cpa_gbp": 1.0},
    {"name": "Bob", "niche": "Bodybuilding", "primary_content_style": "Tutorial", "avg_roi_x": 5.0, "conversion_rate": 0.4, "cpa_gbp": 2.0},
    {"name": "Carol", "niche": "Women's Fitness", "primary_content_style": "Workout Vlog", "avg_roi_x": 6.0, "conversion_rate": 0.5, "cpa_gbp": 1.5},
]


def test_build_scoring_adjustments_top_niche_gets_highest_bonus():
    result = atp.build_scoring_adjustments(SAMPLE_ANALYSES)
    bonuses = result["niche_bonus"]
    # Women's Fitness appears twice with better metrics — should have highest bonus
    assert bonuses["Women's Fitness"] > bonuses["Bodybuilding"]


def test_build_scoring_adjustments_top_style_gets_highest_bonus():
    result = atp.build_scoring_adjustments(SAMPLE_ANALYSES)
    bonuses = result["content_style_bonus"]
    assert bonuses["Workout Vlog"] > bonuses["Tutorial"]


def test_build_scoring_adjustments_known_niches_filled():
    result = atp.build_scoring_adjustments(SAMPLE_ANALYSES)
    for niche in atp.KNOWN_NICHES:
        assert niche in result["niche_bonus"]


def test_build_scoring_adjustments_bonuses_capped_at_scale():
    result = atp.build_scoring_adjustments(SAMPLE_ANALYSES)
    for bonus in result["niche_bonus"].values():
        assert bonus <= 0.8


def test_build_scoring_adjustments_handles_none_conversion_rate():
    analyses = [
        {"name": "Alice", "niche": "Women's Fitness", "primary_content_style": "Workout Vlog", "avg_roi_x": 8.0, "conversion_rate": None, "cpa_gbp": None},
        {"name": "Bob", "niche": "Bodybuilding", "primary_content_style": "Tutorial", "avg_roi_x": 5.0, "conversion_rate": None, "cpa_gbp": None},
    ]
    result = atp.build_scoring_adjustments(analyses)
    assert result["niche_bonus"]["Women's Fitness"] > result["niche_bonus"]["Bodybuilding"]


def test_build_scoring_adjustments_empty():
    result = atp.build_scoring_adjustments([])
    assert result["niche_bonus"] == {}
    assert result["content_style_bonus"] == {}
