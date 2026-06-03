"""
Tests for mcp/gymshark_mcp_server.py

Validates that each tool returns well-formed JSON (or plain text for
draft_outreach_message), handles missing creators gracefully, and
routes data correctly — without making real LLM or API calls.
"""

import csv
import importlib.util
import json
import os
from unittest.mock import patch

import pytest

pytest.importorskip("mcp", reason="mcp package not installed — skipping MCP server tests")

# ---------------------------------------------------------------------------
# Load the MCP server module directly (tools are plain Python functions)
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "gymshark_mcp_server",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "gymshark_mcp_server.py")),
)
_mcp_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mcp_mod)

score_creators = _mcp_mod.score_creators
check_creator_risk = _mcp_mod.check_creator_risk
draft_outreach_message = _mcp_mod.draft_outreach_message


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _creator_row(**overrides) -> dict:
    base = {
        "rank": "1",
        "creator_id": "C001",
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
        "brand_fit_reasoning": "test",
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


def _crm_row(**overrides) -> dict:
    base = {
        "creator_id": "C001",
        "priority": "High",
        "outreach_channel": "Instagram DM",
        "suggested_deal_type": "gift_seeding",
        "account_manager": "Test Manager",
        "pipeline_stage": "Prospect",
        "ai_discovery_notes": "Posts authentic fitness content",
        "proposed_next_step": "Send gifted product",
        "relationship_status": "Prospect",
    }
    base.update(overrides)
    return base


def _sentiment_rows(creator_id: str, n: int = 55, flagged_pct: float = 0.0) -> list[dict]:
    n_flagged = int(n * flagged_pct / 100)
    return [
        {
            "creator_id": creator_id,
            "comment_id": f"C{i}",
            "comment_text": f"comment {i}",
            "sentiment_label": "POSITIVE",
            "compound_score": "0.8",
            "negative_creator_flag": "Yes" if i < n_flagged else "No",
        }
        for i in range(n)
    ]


def _write_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Tool 1 — score_creators
# ---------------------------------------------------------------------------


def test_score_creators_returns_valid_json(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    _write_csv([_creator_row()], creators_csv)

    with patch.object(_mcp_mod, "_DEFAULT_CREATORS", creators_csv):
        result = score_creators()

    data = json.loads(result)
    assert "eligible" in data
    assert "ineligible" in data
    assert "eligible_count" in data


def test_score_creators_eligible_has_required_fields(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    _write_csv([_creator_row()], creators_csv)

    with patch.object(_mcp_mod, "_DEFAULT_CREATORS", creators_csv):
        result = score_creators()

    data = json.loads(result)
    assert data["eligible_count"] == 1
    creator = data["eligible"][0]
    for field in ("creator_id", "name", "tier", "gymshark_brand_fit", "recommendation"):
        assert field in creator, f"Missing field: {field}"


def test_score_creators_red_goes_to_ineligible(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    _write_csv([_creator_row(brand_safety="RED")], creators_csv)

    with patch.object(_mcp_mod, "_DEFAULT_CREATORS", creators_csv):
        result = score_creators()

    data = json.loads(result)
    assert data["eligible_count"] == 0
    assert data["ineligible_count"] == 1
    assert "disqualification_reason" in data["ineligible"][0]


def test_score_creators_missing_file_returns_error_json(tmp_path):
    with patch.object(_mcp_mod, "_DEFAULT_CREATORS", "/nonexistent/creators.csv"):
        result = score_creators()

    data = json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# Tool 2 — check_creator_risk
# ---------------------------------------------------------------------------


def test_check_creator_risk_low_risk(tmp_path):
    sentiment_csv = str(tmp_path / "comment_sentiment.csv")
    _write_csv(_sentiment_rows("C001", flagged_pct=0.0), sentiment_csv)

    with patch.object(_mcp_mod, "_DEFAULT_SENTIMENT", sentiment_csv):
        result = check_creator_risk("C001")

    data = json.loads(result)
    assert data["risk_level"] == "LOW"
    assert data["creator_id"] == "C001"
    assert "recommendation" in data
    assert "metrics" in data


def test_check_creator_risk_high_risk(tmp_path):
    sentiment_csv = str(tmp_path / "comment_sentiment.csv")
    _write_csv(_sentiment_rows("C001", flagged_pct=20.0), sentiment_csv)

    with patch.object(_mcp_mod, "_DEFAULT_SENTIMENT", sentiment_csv):
        result = check_creator_risk("C001")

    data = json.loads(result)
    assert data["risk_level"] == "HIGH"


def test_check_creator_risk_unknown_when_no_data(tmp_path):
    sentiment_csv = str(tmp_path / "comment_sentiment.csv")
    # Write rows for a different creator
    _write_csv(_sentiment_rows("OTHER"), sentiment_csv)

    with patch.object(_mcp_mod, "_DEFAULT_SENTIMENT", sentiment_csv):
        result = check_creator_risk("C001")

    data = json.loads(result)
    assert data["risk_level"] == "UNKNOWN"


def test_check_creator_risk_returns_all_required_fields(tmp_path):
    sentiment_csv = str(tmp_path / "comment_sentiment.csv")
    _write_csv(_sentiment_rows("C001"), sentiment_csv)

    with patch.object(_mcp_mod, "_DEFAULT_SENTIMENT", sentiment_csv):
        result = check_creator_risk("C001")

    data = json.loads(result)
    for field in ("creator_id", "risk_level", "emoji", "reason", "recommendation", "metrics"):
        assert field in data, f"Missing field: {field}"


def test_check_creator_risk_missing_file_returns_error(tmp_path):
    with patch.object(_mcp_mod, "_DEFAULT_SENTIMENT", "/nonexistent/sentiment.csv"):
        result = check_creator_risk("C001")

    data = json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# Tool 3 — draft_outreach_message
# ---------------------------------------------------------------------------


def test_draft_outreach_message_returns_formatted_draft(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)

    with (
        patch.object(_mcp_mod, "_DEFAULT_CREATORS", creators_csv),
        patch.object(_mcp_mod, "_DEFAULT_CRM", crm_csv),
        patch("utils.connect.ask", return_value="Hi! Your fitness content is authentic."),
    ):
        result = draft_outreach_message("C001")

    assert "OUTREACH DRAFT" in result
    assert "Test Creator" in result
    assert "Word count:" in result


def test_draft_outreach_message_missing_creator_returns_error(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    _write_csv([_creator_row(creator_id="OTHER")], creators_csv)
    _write_csv([_crm_row(creator_id="OTHER")], crm_csv)

    with (
        patch.object(_mcp_mod, "_DEFAULT_CREATORS", creators_csv),
        patch.object(_mcp_mod, "_DEFAULT_CRM", crm_csv),
        patch("utils.connect.ask", return_value="Draft message"),
    ):
        result = draft_outreach_message("C001")

    data = json.loads(result)
    assert "error" in data


def test_draft_outreach_message_missing_file_returns_error(tmp_path):
    with (
        patch.object(_mcp_mod, "_DEFAULT_CREATORS", "/nonexistent/creators.csv"),
        patch.object(_mcp_mod, "_DEFAULT_CRM", "/nonexistent/crm.csv"),
        patch("utils.connect.ask", return_value="Draft message"),
    ):
        result = draft_outreach_message("C001")

    data = json.loads(result)
    assert "error" in data


def test_draft_outreach_message_llm_failure_returns_error(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)

    with (
        patch.object(_mcp_mod, "_DEFAULT_CREATORS", creators_csv),
        patch.object(_mcp_mod, "_DEFAULT_CRM", crm_csv),
        patch("utils.connect.ask", side_effect=Exception("LLM unavailable")),
    ):
        result = draft_outreach_message("C001")

    data = json.loads(result)
    assert "error" in data
