"""
Tests for skills/skills/skill-04-campaign-analytics/analytics_helpers.py
"""

import importlib.util
import os
import pytest

pd = pytest.importorskip("pandas")

_spec = importlib.util.spec_from_file_location(
    "analytics_helpers",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "skills",
            "skill-04-campaign-analytics",
            "analytics_helpers.py",
        )
    ),
)
ah = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ah)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_df(**overrides):
    """Return a minimal valid campaigns DataFrame with two rows."""
    base = {
        "campaign_id": ["C1", "C2"],
        "creator_id": ["A1", "A2"],
        "creator_name": ["Alice", "Bob"],
        "tier": ["nano", "micro"],
        "deal_type": ["gift_seeding", "affiliate"],
        "campaign_start": ["2026-01-01", "2026-02-01"],
        "campaign_end": ["2026-01-28", "2026-03-01"],
        "budget_gbp": [50.0, 200.0],
        "revenue_attributed_gbp": [5000.0, 10000.0],
        "promo_redemptions": [80.0, 60.0],
        "utm_clicks": [100.0, 200.0],
        "reach": [1000.0, 5000.0],
        "impressions": [2000.0, 8000.0],
        "renewal_recommended": ["Yes", "Yes"],
    }
    base.update(overrides)
    return pd.DataFrame(base)


# ── validate_campaign_columns ─────────────────────────────────────────────────


def test_validate_columns_all_present():
    assert ah.validate_campaign_columns(_make_df()) == []


def test_validate_columns_detects_missing():
    df = _make_df().drop(columns=["budget_gbp"])
    assert "budget_gbp" in ah.validate_campaign_columns(df)


# ── calculate_campaign_metrics ────────────────────────────────────────────────


def test_roi_pct_formula():
    df = _make_df(budget_gbp=[100.0, 100.0], revenue_attributed_gbp=[300.0, 50.0])
    m = ah.calculate_campaign_metrics(df)
    assert m["roi_pct"].iloc[0] == pytest.approx(200.0)
    assert m["roi_pct"].iloc[1] == pytest.approx(-50.0)


def test_zero_budget_gives_nan_roi():
    df = _make_df(budget_gbp=[0.0, 100.0])
    m = ah.calculate_campaign_metrics(df)
    assert pd.isna(m["roi_pct"].iloc[0])
    assert not pd.isna(m["roi_pct"].iloc[1])


def test_conversion_rate_formula():
    df = _make_df(promo_redemptions=[25.0, 50.0], utm_clicks=[100.0, 200.0])
    m = ah.calculate_campaign_metrics(df)
    assert m["conversion_rate_pct"].iloc[0] == pytest.approx(25.0)
    assert m["conversion_rate_pct"].iloc[1] == pytest.approx(25.0)


def test_zero_clicks_gives_nan_conversion():
    df = _make_df(utm_clicks=[0.0, 100.0])
    m = ah.calculate_campaign_metrics(df)
    assert pd.isna(m["conversion_rate_pct"].iloc[0])


def test_cost_per_click():
    df = _make_df(budget_gbp=[100.0, 200.0], utm_clicks=[50.0, 100.0])
    m = ah.calculate_campaign_metrics(df)
    assert m["cost_per_click"].iloc[0] == pytest.approx(2.0)
    assert m["cost_per_click"].iloc[1] == pytest.approx(2.0)


def test_revenue_per_pound():
    df = _make_df(budget_gbp=[100.0, 200.0], revenue_attributed_gbp=[500.0, 600.0])
    m = ah.calculate_campaign_metrics(df)
    assert m["revenue_per_pound"].iloc[0] == pytest.approx(5.0)
    assert m["revenue_per_pound"].iloc[1] == pytest.approx(3.0)


# ── aggregate_by_tier ─────────────────────────────────────────────────────────


def test_aggregate_by_tier_groups_correctly():
    df = ah.calculate_campaign_metrics(_make_df())
    result = ah.aggregate_by_tier(df)
    assert set(result["tier"]) == {"nano", "micro"}


def test_aggregate_by_tier_sorted_desc():
    df = ah.calculate_campaign_metrics(
        _make_df(
            budget_gbp=[10.0, 100.0],
            revenue_attributed_gbp=[1000.0, 200.0],
        )
    )
    result = ah.aggregate_by_tier(df)
    assert result["avg_roi_pct"].iloc[0] >= result["avg_roi_pct"].iloc[1]


# ── aggregate_by_deal_type ────────────────────────────────────────────────────


def test_aggregate_by_deal_type_groups_correctly():
    df = ah.calculate_campaign_metrics(_make_df())
    result = ah.aggregate_by_deal_type(df)
    assert set(result["deal_type"]) == {"gift_seeding", "affiliate"}


# ── get_top_performers ────────────────────────────────────────────────────────


def test_top_performers_filters_correctly():
    df = ah.calculate_campaign_metrics(
        _make_df(
            budget_gbp=[10.0, 500.0],
            revenue_attributed_gbp=[5000.0, 600.0],
            promo_redemptions=[50.0, 5.0],
            utm_clicks=[100.0, 200.0],
        )
    )
    top = ah.get_top_performers(df, roi_threshold=150, conv_threshold=3)
    assert len(top) == 1
    assert top["creator_name"].iloc[0] == "Alice"


def test_top_performers_empty_when_none_qualify():
    df = ah.calculate_campaign_metrics(_make_df(budget_gbp=[100.0, 100.0], revenue_attributed_gbp=[110.0, 105.0]))
    assert ah.get_top_performers(df).empty


# ── get_bottom_performers ─────────────────────────────────────────────────────


def test_bottom_performers_negative_roi():
    df = ah.calculate_campaign_metrics(_make_df(budget_gbp=[100.0, 100.0], revenue_attributed_gbp=[50.0, 500.0]))
    bot = ah.get_bottom_performers(df, roi_threshold=20)
    assert len(bot) == 1
    assert bot["creator_name"].iloc[0] == "Alice"


def test_bottom_performers_empty_when_all_good():
    df = ah.calculate_campaign_metrics(_make_df(budget_gbp=[10.0, 10.0], revenue_attributed_gbp=[1000.0, 2000.0]))
    assert ah.get_bottom_performers(df).empty


# ── portfolio_summary ─────────────────────────────────────────────────────────


def test_portfolio_summary_totals():
    df = ah.calculate_campaign_metrics(_make_df(budget_gbp=[100.0, 200.0], revenue_attributed_gbp=[500.0, 1000.0]))
    s = ah.portfolio_summary(df)
    assert s["campaigns_analysed"] == 2
    assert s["total_spend_gbp"] == pytest.approx(300.0)
    assert s["total_revenue_gbp"] == pytest.approx(1500.0)
    assert s["blended_roi_pct"] == pytest.approx(400.0)


def test_portfolio_summary_zero_spend():
    df = ah.calculate_campaign_metrics(_make_df(budget_gbp=[0.0, 0.0]))
    s = ah.portfolio_summary(df)
    assert s["blended_roi_pct"] == 0
