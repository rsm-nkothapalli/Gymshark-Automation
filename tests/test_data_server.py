"""
Tests for mcp_servers/data_server.py

Validates that each resource returns well-formed JSON and handles
missing files gracefully — without requiring real data files.
"""

import csv
import importlib.util
import json
import os
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Load module
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "data_server",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mcp_servers", "data_server.py")),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

get_all_creators = _mod.get_all_creators
get_creator = _mod.get_creator
get_campaign_summary = _mod.get_campaign_summary


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _creator_row(**overrides) -> dict:
    base = {
        "creator_id": "C001",
        "name": "Test Creator",
        "tier": "nano",
        "subscribers": "5000",
        "gymshark_brand_fit": "7.0",
        "authenticity_score": "7.0",
        "niche": "General Fitness",
        "brand_safety": "GREEN",
        "outreach_recommended": "True",
        "suggested_deal_type": "gift_seeding",
    }
    base.update(overrides)
    return base


def _crm_row(**overrides) -> dict:
    base = {
        "creator_id": "C001",
        "outreach_channel": "Instagram DM",
        "suggested_deal_type": "gift_seeding",
        "account_manager": "Test Manager",
    }
    base.update(overrides)
    return base


def _campaign_row(**overrides) -> dict:
    base = {
        "campaign_id": "CAM001",
        "creator_id": "P001",
        "tier": "micro",
        "deal_type": "affiliate",
        "budget_gbp": "500",
        "reach": "10000",
        "revenue_attributed_gbp": "1500",
        "roi_x": "3.0",
        "renewal_recommended": "True",
    }
    base.update(overrides)
    return base


def _partner_row(**overrides) -> dict:
    base = {
        "creator_id": "P001",
        "name": "Partner Creator",
        "tier": "micro",
        "deal_type": "affiliate",
        "subscribers": "50000",
    }
    base.update(overrides)
    return base


def _write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# get_all_creators
# ---------------------------------------------------------------------------


def test_get_all_creators_returns_valid_json(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _write_csv([_creator_row(), _creator_row(creator_id="C002", name="Second Creator")], csv_path)

    with patch.object(_mod, "_DEFAULT_CREATORS", csv_path):
        result = get_all_creators()

    data = json.loads(result)
    assert data["count"] == 2
    assert len(data["creators"]) == 2


def test_get_all_creators_has_required_fields(tmp_path):
    csv_path = str(tmp_path / "creators.csv")
    _write_csv([_creator_row()], csv_path)

    with patch.object(_mod, "_DEFAULT_CREATORS", csv_path):
        result = get_all_creators()

    creator = json.loads(result)["creators"][0]
    for field in ("creator_id", "name", "tier", "gymshark_brand_fit", "brand_safety", "outreach_recommended"):
        assert field in creator, f"Missing field: {field}"


def test_get_all_creators_missing_file_returns_error():
    with patch.object(_mod, "_DEFAULT_CREATORS", "/nonexistent/creators.csv"):
        result = get_all_creators()

    data = json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# get_creator
# ---------------------------------------------------------------------------


def test_get_creator_returns_profile(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)

    with patch.object(_mod, "_DEFAULT_CREATORS", creators_csv), patch.object(_mod, "_DEFAULT_CRM", crm_csv):
        result = get_creator("C001")

    data = json.loads(result)
    assert data["creator_id"] == "C001"
    assert data["name"] == "Test Creator"


def test_get_creator_merges_crm_fields(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row(outreach_channel="Email via Management")], crm_csv)

    with patch.object(_mod, "_DEFAULT_CREATORS", creators_csv), patch.object(_mod, "_DEFAULT_CRM", crm_csv):
        result = get_creator("C001")

    data = json.loads(result)
    assert data["outreach_channel"] == "Email via Management"


def test_get_creator_unknown_id_returns_error(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    _write_csv([_creator_row()], creators_csv)

    with (
        patch.object(_mod, "_DEFAULT_CREATORS", creators_csv),
        patch.object(_mod, "_DEFAULT_CRM", "/nonexistent/crm.csv"),
    ):
        result = get_creator("UNKNOWN")

    data = json.loads(result)
    assert "error" in data


# ---------------------------------------------------------------------------
# get_campaign_summary
# ---------------------------------------------------------------------------


def test_get_campaign_summary_returns_valid_json(tmp_path):
    camp_csv = str(tmp_path / "campaign_performance.csv")
    partners_csv = str(tmp_path / "existing_partners.csv")
    _write_csv([_campaign_row()], camp_csv)
    _write_csv([_partner_row()], partners_csv)

    with patch.object(_mod, "_DEFAULT_CAMPAIGNS", camp_csv), patch.object(_mod, "_DEFAULT_PARTNERS", partners_csv):
        result = get_campaign_summary()

    data = json.loads(result)
    assert "total_campaigns" in data
    assert data["total_campaigns"] == 1


def test_get_campaign_summary_calculates_totals(tmp_path):
    camp_csv = str(tmp_path / "campaign_performance.csv")
    partners_csv = str(tmp_path / "existing_partners.csv")
    rows = [
        _campaign_row(budget_gbp="500", revenue_attributed_gbp="1500", roi_x="3.0"),
        _campaign_row(
            campaign_id="CAM002", creator_id="P002", budget_gbp="1000", revenue_attributed_gbp="2000", roi_x="2.0"
        ),
    ]
    _write_csv(rows, camp_csv)
    _write_csv([_partner_row(), _partner_row(creator_id="P002", name="Partner 2")], partners_csv)

    with patch.object(_mod, "_DEFAULT_CAMPAIGNS", camp_csv), patch.object(_mod, "_DEFAULT_PARTNERS", partners_csv):
        result = get_campaign_summary()

    data = json.loads(result)
    assert data["total_budget_gbp"] == 1500.0
    assert data["total_revenue_attributed_gbp"] == 3500.0


def test_get_campaign_summary_missing_file_returns_error():
    with (
        patch.object(_mod, "_DEFAULT_CAMPAIGNS", "/nonexistent/campaigns.csv"),
        patch.object(_mod, "_DEFAULT_PARTNERS", "/nonexistent/partners.csv"),
    ):
        result = get_campaign_summary()

    data = json.loads(result)
    assert "error" in data


def test_get_campaign_summary_renewal_count(tmp_path):
    camp_csv = str(tmp_path / "campaign_performance.csv")
    partners_csv = str(tmp_path / "existing_partners.csv")
    rows = [
        _campaign_row(renewal_recommended="True"),
        _campaign_row(campaign_id="CAM002", creator_id="P002", renewal_recommended="False"),
    ]
    _write_csv(rows, camp_csv)
    _write_csv([_partner_row(), _partner_row(creator_id="P002", name="Partner 2")], partners_csv)

    with patch.object(_mod, "_DEFAULT_CAMPAIGNS", camp_csv), patch.object(_mod, "_DEFAULT_PARTNERS", partners_csv):
        result = get_campaign_summary()

    assert json.loads(result)["renewal_recommended_count"] == 1
