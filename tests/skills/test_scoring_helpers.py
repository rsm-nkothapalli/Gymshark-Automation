"""
Tests for skills/skills/skill-01-creator-scoring/scoring_helpers.py
"""

import csv
import importlib.util
import os

import pytest

# Load module from hyphenated path
_spec = importlib.util.spec_from_file_location(
    "scoring_helpers",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "skills",
            "skill-01-creator-scoring",
            "scoring_helpers.py",
        )
    ),
)
scoring_helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scoring_helpers)

get_tier_threshold = scoring_helpers.get_tier_threshold
is_disqualified = scoring_helpers.is_disqualified
get_recommendation = scoring_helpers.get_recommendation
load_creators = scoring_helpers.load_creators
shortlist_creators = scoring_helpers.shortlist_creators
format_shortlist_table = scoring_helpers.format_shortlist_table
format_ineligible_list = scoring_helpers.format_ineligible_list


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_csv(rows: list[dict], path: str) -> str:
    """Write rows to a CSV at path, return path."""
    if not rows:
        return path
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


def _base_creator(**overrides) -> dict:
    """Return a minimal valid creator row (all disqualifiers off, GFS=7.0)."""
    base = {
        "rank": "1",
        "creator_id": "TEST001",
        "name": "Test Creator",
        "youtube_handle": "@test",
        "tier": "nano",
        "suggested_deal_type": "gift_seeding",
        "niche": "General Fitness",
        "content_style": "Vlog",
        "audience_tone": "Motivational",
        "subscribers": "5000",
        "total_views": "100000",
        "video_count": "50",
        "estimated_er_pct": "5.0",
        "country": "GB",
        "gymshark_brand_fit": "7.0",
        "authenticity_score": "7.0",
        "community_score": "7.0",
        "niche_alignment_score": "7.0",
        "production_quality": "5.0",
        "brand_fit_reasoning": "test reasoning",
        "authenticity_reasoning": "test",
        "signals_authentic_pos": "none",
        "signals_authentic_neg": "none",
        "signals_community": "none",
        "transcript_available": "True",
        "brand_safety": "GREEN",
        "brand_safety_notes": "none",
        "clickbait_detected": "False",
        "clickbait_examples": "none",
        "competitor_loyalty": "False",
        "competitor_brands": "none",
        "existing_partner": "False",
        "red_flags": "none",
        "controversy_details": "none",
        "outreach_recommended": "True",
        "scoring_method": "rule-based",
        "videos_analyzed": "1",
        "source": "test",
        "date_added": "2026-05-12",
    }
    base.update(overrides)
    return base


def _loaded(row: dict) -> dict:
    """Apply the same type coercions that load_creators performs."""
    for bool_col in (
        "clickbait_detected",
        "competitor_loyalty",
        "existing_partner",
        "outreach_recommended",
        "transcript_available",
    ):
        if bool_col in row:
            row[bool_col] = str(row[bool_col]).strip().lower() in ("true", "yes", "1")
    for float_col in (
        "gymshark_brand_fit",
        "authenticity_score",
        "community_score",
        "niche_alignment_score",
        "production_quality",
    ):
        try:
            row[float_col] = float(row[float_col])
        except (ValueError, KeyError):
            pass
    for int_col in ("subscribers", "rank"):
        try:
            row[int_col] = int(row[int_col])
        except (ValueError, KeyError):
            pass
    return row


# ---------------------------------------------------------------------------
# get_tier_threshold
# ---------------------------------------------------------------------------


def test_tier_thresholds_all_known():
    assert get_tier_threshold("nano") == 5.0
    assert get_tier_threshold("micro") == 5.5
    assert get_tier_threshold("mid") == 6.0
    assert get_tier_threshold("macro") == 6.5
    assert get_tier_threshold("mega") == 7.5


def test_tier_threshold_case_insensitive():
    assert get_tier_threshold("NANO") == 5.0
    assert get_tier_threshold("Micro") == 5.5


def test_tier_threshold_unknown_falls_back_to_micro():
    assert get_tier_threshold("unknown") == 5.5
    assert get_tier_threshold("") == 5.5


# ---------------------------------------------------------------------------
# is_disqualified
# ---------------------------------------------------------------------------


def test_not_disqualified_clean_creator():
    c = _loaded(_base_creator())
    disq, reason = is_disqualified(c)
    assert disq is False
    assert reason == ""


def test_disqualified_red_brand_safety():
    c = _loaded(_base_creator(brand_safety="RED"))
    disq, reason = is_disqualified(c)
    assert disq is True
    assert "RED" in reason


def test_disqualified_clickbait():
    c = _loaded(_base_creator(clickbait_detected="True"))
    disq, reason = is_disqualified(c)
    assert disq is True
    assert "clickbait" in reason


def test_disqualified_competitor_loyalty():
    c = _loaded(_base_creator(competitor_loyalty="True"))
    disq, reason = is_disqualified(c)
    assert disq is True
    assert "competitor" in reason


def test_disqualified_outreach_not_recommended():
    c = _loaded(_base_creator(outreach_recommended="False"))
    disq, reason = is_disqualified(c)
    assert disq is True
    assert "outreach_recommended" in reason


# ---------------------------------------------------------------------------
# get_recommendation
# ---------------------------------------------------------------------------


def test_recommendation_outreach_now_at_threshold():
    c = _loaded(_base_creator(tier="nano", gymshark_brand_fit="5.0"))
    assert get_recommendation(c).startswith("Outreach now")


def test_recommendation_outreach_now_above_threshold():
    c = _loaded(_base_creator(tier="micro", gymshark_brand_fit="7.0"))
    assert get_recommendation(c).startswith("Outreach now")


def test_recommendation_borderline():
    # nano threshold = 5.0; borderline = 4.5–4.99
    c = _loaded(_base_creator(tier="nano", gymshark_brand_fit="4.8"))
    assert get_recommendation(c).startswith("FLAG: borderline")


def test_recommendation_do_not_recommend():
    # nano threshold = 5.0; below borderline = < 4.5
    c = _loaded(_base_creator(tier="nano", gymshark_brand_fit="3.0"))
    assert get_recommendation(c).startswith("Do not recommend")


def test_recommendation_amber_flag_appended():
    c = _loaded(_base_creator(tier="nano", gymshark_brand_fit="6.0", brand_safety="AMBER"))
    assert "AMBER" in get_recommendation(c)


def test_recommendation_existing_partner_flag_appended():
    c = _loaded(_base_creator(tier="nano", gymshark_brand_fit="6.0", existing_partner="True"))
    assert "existing partner" in get_recommendation(c)


# ---------------------------------------------------------------------------
# load_creators
# ---------------------------------------------------------------------------


def test_load_creators_returns_list(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _make_csv([_base_creator()], csv_path)
    creators = load_creators(csv_path)
    assert isinstance(creators, list)
    assert len(creators) == 1


def test_load_creators_coerces_numeric(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _make_csv([_base_creator(gymshark_brand_fit="6.5", subscribers="5000")], csv_path)
    creators = load_creators(csv_path)
    assert isinstance(creators[0]["gymshark_brand_fit"], float)
    assert creators[0]["gymshark_brand_fit"] == 6.5
    assert isinstance(creators[0]["subscribers"], int)
    assert creators[0]["subscribers"] == 5000


def test_load_creators_coerces_booleans(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _make_csv([_base_creator(clickbait_detected="True", competitor_loyalty="False")], csv_path)
    creators = load_creators(csv_path)
    assert creators[0]["clickbait_detected"] is True
    assert creators[0]["competitor_loyalty"] is False


def test_load_creators_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_creators("/nonexistent/path/creators.csv")


# ---------------------------------------------------------------------------
# shortlist_creators
# ---------------------------------------------------------------------------


def test_shortlist_separates_eligible_and_ineligible(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    rows = [
        _base_creator(creator_id="A", gymshark_brand_fit="7.0", brand_safety="GREEN"),
        _base_creator(creator_id="B", gymshark_brand_fit="6.0", brand_safety="RED"),
    ]
    _make_csv(rows, csv_path)
    eligible, ineligible = shortlist_creators(csv_path)
    assert len(eligible) == 1
    assert len(ineligible) == 1
    assert eligible[0]["creator_id"] == "A"
    assert ineligible[0]["creator_id"] == "B"


def test_shortlist_eligible_sorted_by_gfs_descending(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    rows = [
        _base_creator(creator_id="LOW", gymshark_brand_fit="5.5"),
        _base_creator(creator_id="HIGH", gymshark_brand_fit="8.0"),
        _base_creator(creator_id="MID", gymshark_brand_fit="6.5"),
    ]
    _make_csv(rows, csv_path)
    eligible, _ = shortlist_creators(csv_path)
    scores = [c["gymshark_brand_fit"] for c in eligible]
    assert scores == sorted(scores, reverse=True)


def test_shortlist_eligible_has_recommendation_key(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _make_csv([_base_creator()], csv_path)
    eligible, _ = shortlist_creators(csv_path)
    assert "recommendation" in eligible[0]


def test_shortlist_ineligible_has_disqualification_reason_key(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _make_csv([_base_creator(brand_safety="RED")], csv_path)
    _, ineligible = shortlist_creators(csv_path)
    assert "disqualification_reason" in ineligible[0]


def test_shortlist_empty_csv_returns_empty_lists(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write(",".join(_base_creator().keys()) + "\n")
    eligible, ineligible = shortlist_creators(csv_path)
    assert eligible == []
    assert ineligible == []


def test_shortlist_against_real_creators_csv():
    """Smoke test: real data/creators.csv loads and produces at least one result."""
    real_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "creators.csv"))
    if not os.path.exists(real_path):
        pytest.skip("data/creators.csv not present")
    eligible, ineligible = shortlist_creators(real_path)
    assert isinstance(eligible, list)
    assert isinstance(ineligible, list)
    assert len(eligible) + len(ineligible) > 0


# ---------------------------------------------------------------------------
# format helpers
# ---------------------------------------------------------------------------


def test_format_shortlist_table_contains_name(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _make_csv([_base_creator(name="Naomi Fitness")], csv_path)
    eligible, _ = shortlist_creators(csv_path)
    assert "Naomi Fitness" in format_shortlist_table(eligible)


def test_format_shortlist_table_empty():
    assert "No eligible" in format_shortlist_table([])


def test_format_ineligible_list_contains_name(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _make_csv([_base_creator(name="Bad Creator", brand_safety="RED")], csv_path)
    _, ineligible = shortlist_creators(csv_path)
    assert "Bad Creator" in format_ineligible_list(ineligible)


def test_format_ineligible_list_empty():
    assert format_ineligible_list([]) == "None."
