"""
Tests for skills/skills/skill-06-pipeline-workflow/pipeline_helpers.py

Tests cover Steps 1-3 (scoring, outreach, product briefs) and all three
human-in-the-loop gates. LLM calls are mocked; input() is mocked for gate
functions to simulate human decisions.

Brand risk is evaluated during scoring (Step 1) via the LLM and stored in
creators.csv — no separate Skill 02 step or Gate 2 risk review.
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
    "pipeline_helpers",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "skills",
            "skill-06-pipeline-workflow",
            "pipeline_helpers.py",
        )
    ),
)
ph = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ph)


# ---------------------------------------------------------------------------
# CSV fixture helpers
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
        "niche_score": "7.0",
        "engagement_score": "7.0",
        "brand_fit_reasoning": "test",
        "authenticity_reasoning": "test",
        "signals_authentic_pos": "none",
        "signals_authentic_neg": "none",
        "transcript_available": "True",
        "audience_brand_risk": "LOW",
        "audience_brand_risk_reason": "clean comment section",
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


def _write_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Step 1 — run_scoring_step
# ---------------------------------------------------------------------------


def test_scoring_step_returns_eligible_list(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    _write_csv([_creator_row()], creators_csv)
    eligible = ph.run_scoring_step(creators_csv, str(tmp_path))
    assert len(eligible) == 1
    assert eligible[0]["creator_id"] == "C001"


def test_scoring_step_writes_json(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    _write_csv([_creator_row()], creators_csv)
    ph.run_scoring_step(creators_csv, str(tmp_path))
    out = tmp_path / "01_shortlisted.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert "eligible" in data
    assert "ineligible" in data


def test_scoring_step_disqualifies_red_creators(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    _write_csv([_creator_row(brand_safety="RED")], creators_csv)
    eligible = ph.run_scoring_step(creators_csv, str(tmp_path))
    assert len(eligible) == 0
    data = json.loads((tmp_path / "01_shortlisted.json").read_text())
    assert data["ineligible_count"] == 1


def test_scoring_step_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        ph.run_scoring_step("/nonexistent/creators.csv", str(tmp_path))


# ---------------------------------------------------------------------------
# Step 2 — run_outreach_step (LLM mocked)
# ---------------------------------------------------------------------------


def test_outreach_step_writes_draft_file(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)

    approved = [{"creator_id": "C001", "name": "Test Creator", "tier": "nano"}]

    with patch("utils.connect.ask", return_value="Hi! Great content. Want some kit?"):
        results = ph.run_outreach_step(approved, creators_csv, crm_csv, str(tmp_path))

    assert "C001" in results
    assert results["C001"]["status"] == "drafted"
    draft_file = tmp_path / "04_outreach_drafts" / "C001.txt"
    assert draft_file.exists()
    assert len(draft_file.read_text()) > 10


def test_outreach_step_handles_missing_creator_gracefully(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    _write_csv([_creator_row(creator_id="OTHER")], creators_csv)
    _write_csv([_crm_row(creator_id="OTHER")], crm_csv)

    approved = [{"creator_id": "C001", "name": "Missing", "tier": "nano"}]

    with patch("utils.connect.ask", return_value="Hi!"):
        results = ph.run_outreach_step(approved, creators_csv, crm_csv, str(tmp_path))

    assert results["C001"]["status"] == "error"


# ---------------------------------------------------------------------------
# run_pipeline — integration (LLM mocked, no real API)
# ---------------------------------------------------------------------------


def test_run_pipeline_dry_run(tmp_path):
    """Dry run stops after Step 1 — no LLM calls, no draft files."""
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")

    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)

    summary = ph.run_pipeline(
        creators_path=creators_csv,
        crm_path=crm_csv,
        output_dir=str(tmp_path),
        draft_outreach=False,
    )

    assert "step1_eligible" in summary
    assert summary["step2_drafted"] == 0
    assert (tmp_path / "05_pipeline_summary.json").exists()


def test_run_pipeline_full_with_mock_llm(tmp_path):
    """Full pipeline with mocked LLM — verifies all steps run and produce output."""
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")

    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)

    with patch("utils.connect.ask", return_value="Hi! Love your fitness content."):
        summary = ph.run_pipeline(
            creators_path=creators_csv,
            crm_path=crm_csv,
            output_dir=str(tmp_path),
        )

    assert summary["step1_eligible"] == 1
    assert (tmp_path / "01_shortlisted.json").exists()
    assert (tmp_path / "05_pipeline_summary.json").exists()


# ---------------------------------------------------------------------------
# Human Gate 1 — human_gate_scoring
# ---------------------------------------------------------------------------


def _eligible_list():
    return [
        {
            "creator_id": "C001",
            "name": "Alice",
            "tier": "nano",
            "gymshark_brand_fit": 7.0,
            "recommendation": "Outreach now",
        },
        {
            "creator_id": "C002",
            "name": "Bob",
            "tier": "micro",
            "gymshark_brand_fit": 6.5,
            "recommendation": "Outreach now",
        },
    ]


# ---------------------------------------------------------------------------
# _build_gate1_reasoning
# ---------------------------------------------------------------------------


def test_gate1_reasoning_outreach_now_highlights_strong_auth():
    creator = {
        "gymshark_brand_fit": 7.0,
        "tier": "nano",
        "authenticity_score": 9.0,
        "niche_score": 9.0,
        "signals_authentic_pos": "not sponsored, honest review",
    }
    reasoning = ph._build_gate1_reasoning(creator)
    assert "exceptional" in reasoning
    assert "niche fit" in reasoning
    assert "transcript verified" in reasoning


def test_gate1_reasoning_outreach_now_strong_auth():
    creator = {
        "gymshark_brand_fit": 6.8,
        "tier": "nano",
        "authenticity_score": 7.0,
        "niche_score": 9.0,
        "signals_authentic_pos": "honest review",
    }
    reasoning = ph._build_gate1_reasoning(creator)
    assert "strong" in reasoning


def test_gate1_reasoning_do_not_recommend_shows_gap():
    creator = {
        "gymshark_brand_fit": 5.7,
        "tier": "mega",
        "authenticity_score": 5.0,
        "niche_score": 8.0,
        "signals_authentic_pos": "none",
    }
    reasoning = ph._build_gate1_reasoning(creator)
    assert "mega min 7.5" in reasoning
    assert "1.8 pts short" in reasoning
    assert "no transcript authenticity signals found" in reasoning


def test_gate1_reasoning_borderline_shows_gap():
    creator = {
        "gymshark_brand_fit": 4.7,
        "tier": "nano",
        "authenticity_score": 5.0,
        "niche_score": 7.0,
        "signals_authentic_pos": "",
    }
    reasoning = ph._build_gate1_reasoning(creator)
    assert "nano min 5.0" in reasoning
    assert "0.3 pts short" in reasoning


def test_gate1_reasoning_no_transcript_signals_noted():
    creator = {
        "gymshark_brand_fit": 5.5,
        "tier": "nano",
        "authenticity_score": 5.0,
        "niche_score": 7.0,
        "signals_authentic_pos": "none",
    }
    reasoning = ph._build_gate1_reasoning(creator)
    assert "channel stats" in reasoning


def test_human_gate_scoring_proceeds_all_on_yes(capsys):
    with patch.object(ph, "_human_prompt", return_value="Y"):
        result = ph.human_gate_scoring(_eligible_list())
    assert len(result) == 2


def test_human_gate_scoring_proceeds_all_on_empty_input(capsys):
    with patch.object(ph, "_human_prompt", return_value=""):
        result = ph.human_gate_scoring(_eligible_list())
    assert len(result) == 2


def test_human_gate_scoring_excludes_specified_ids(capsys):
    with patch.object(ph, "_human_prompt", return_value="C001"):
        result = ph.human_gate_scoring(_eligible_list())
    assert len(result) == 1
    assert result[0]["creator_id"] == "C002"


def test_human_gate_scoring_excludes_multiple_ids(capsys):
    with patch.object(ph, "_human_prompt", return_value="C001,C002"):
        result = ph.human_gate_scoring(_eligible_list())
    assert result == []


# ---------------------------------------------------------------------------
# Human Gate 2 — human_gate_outreach
# ---------------------------------------------------------------------------


def _make_draft_file(tmp_path, creator_id="C001"):
    drafts_dir = tmp_path / "04_outreach_drafts"
    drafts_dir.mkdir(exist_ok=True)
    draft = drafts_dir / f"{creator_id}.txt"
    draft.write_text(f"OUTREACH DRAFT\nHi {creator_id}, want to partner?\nWord count: 10")
    return str(tmp_path)


def test_human_gate_outreach_approved_on_yes(tmp_path):
    _make_draft_file(tmp_path)
    results = {"C001": {"name": "Alice", "status": "drafted", "validation_issues": []}}
    drafts_dir = str(tmp_path / "04_outreach_drafts")
    with patch.object(ph, "_human_prompt", return_value="Y"):
        approved = ph.human_gate_outreach(results, drafts_dir)
    assert approved == ["C001"]


def test_human_gate_outreach_not_approved_on_no(tmp_path):
    _make_draft_file(tmp_path)
    results = {"C001": {"name": "Alice", "status": "drafted", "validation_issues": []}}
    drafts_dir = str(tmp_path / "04_outreach_drafts")
    with patch.object(ph, "_human_prompt", return_value="N"):
        approved = ph.human_gate_outreach(results, drafts_dir)
    assert approved == []


def test_human_gate_outreach_skips_failed_drafts(tmp_path):
    results = {"C001": {"name": "Alice", "status": "error", "error": "LLM failed"}}
    with patch.object(ph, "_human_prompt", return_value="Y"):
        approved = ph.human_gate_outreach(results, str(tmp_path))
    assert approved == []


def test_human_gate_outreach_multiple_drafts(tmp_path):
    _make_draft_file(tmp_path, "C001")
    _make_draft_file(tmp_path, "C002")
    results = {
        "C001": {"name": "Alice", "status": "drafted", "validation_issues": []},
        "C002": {"name": "Bob", "status": "drafted", "validation_issues": []},
    }
    drafts_dir = str(tmp_path / "04_outreach_drafts")
    with patch.object(ph, "_human_prompt", side_effect=["Y", "N"]):
        approved = ph.human_gate_outreach(results, drafts_dir)
    assert approved == ["C001"]


# ---------------------------------------------------------------------------
# Human Gate 3 — human_gate_responses
# ---------------------------------------------------------------------------


def test_human_gate_responses_returns_yes_ids(capsys):
    name_map = {"C001": "Alice", "C002": "Bob"}
    with patch.object(ph, "_human_prompt", return_value="1"):
        result = ph.human_gate_responses(["C001", "C002"], name_map)
    assert result == ["C001"]


def test_human_gate_responses_empty_input_returns_empty(capsys):
    with patch.object(ph, "_human_prompt", return_value=""):
        result = ph.human_gate_responses(["C001"], {"C001": "Alice"})
    assert result == []


def test_human_gate_responses_ignores_unknown_ids(capsys):
    with patch.object(ph, "_human_prompt", return_value="99"):
        result = ph.human_gate_responses(["C001"], {"C001": "Alice"})
    assert result == []


def test_human_gate_responses_no_approved_ids_returns_empty(capsys):
    result = ph.human_gate_responses([], {})
    assert result == []


# ---------------------------------------------------------------------------
# Step 3 — run_brief_step
# ---------------------------------------------------------------------------


def _intake_row(**overrides) -> dict:
    base = {
        "creator_id": "C001",
        "ha_subscribers": "5000",
        "ha_engagement_rate": "5.0",
        "ha_audience_quality": "good",
        "ha_fake_followers_pct": "2.0",
        "ha_fraud_risk_label": "low",
        "ha_audience_male_pct": "55.0",
        "ha_top_country": "GB",
        "ig_followers": "3000",
        "ig_engagement_rate": "4.0",
        "pipeline_action": "proceed",
    }
    base.update(overrides)
    return base


def test_run_brief_step_generates_file(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    intake_csv = str(tmp_path / "hypeauditor_intake_log.csv")
    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)
    _write_csv([_intake_row()], intake_csv)

    with patch.object(ph._brief, "ask", return_value="KEY MESSAGE: Feel strong.\nCONTENT FORMAT: YouTube."):
        results = ph.run_brief_step(["C001"], creators_csv, crm_csv, str(tmp_path), intake_csv)

    assert results["C001"]["status"] == "generated"
    assert (tmp_path / "06_product_briefs" / "C001.txt").exists()


def test_run_brief_step_missing_creator_returns_error(tmp_path):
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    intake_csv = str(tmp_path / "hypeauditor_intake_log.csv")
    _write_csv([_creator_row(creator_id="OTHER")], creators_csv)
    _write_csv([_crm_row(creator_id="OTHER")], crm_csv)
    _write_csv([_intake_row(creator_id="OTHER")], intake_csv)

    with patch("utils.connect.ask", return_value="brief text"):
        results = ph.run_brief_step(["C001"], creators_csv, crm_csv, str(tmp_path), intake_csv)

    assert results["C001"]["status"] == "error"


def test_run_brief_step_empty_yes_ids_returns_empty(tmp_path):
    results = ph.run_brief_step([], str(tmp_path), str(tmp_path), str(tmp_path), str(tmp_path))
    assert results == {}


# ---------------------------------------------------------------------------
# run_pipeline with human_review=True (all gates mocked)
# ---------------------------------------------------------------------------


def test_run_pipeline_interactive_full(tmp_path):
    """Interactive pipeline: all human gates return approvals; checks summary keys."""
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    intake_csv = str(tmp_path / "hypeauditor_intake_log.csv")

    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)
    _write_csv([_intake_row()], intake_csv)

    # Gate 1: proceed all; Gate 2: approve draft; Gate 3: no response yet
    input_responses = ["Y", "Y", ""]
    with (
        patch("utils.connect.ask", return_value="Hi! Want to partner with Gymshark?"),
        patch.object(ph, "_human_prompt", side_effect=input_responses),
    ):
        summary = ph.run_pipeline(
            creators_path=creators_csv,
            crm_path=crm_csv,
            intake_path=intake_csv,
            output_dir=str(tmp_path),
            human_review=True,
        )

    assert summary["human_review"] is True
    assert summary["step1_eligible"] == 1
    assert summary["step2_drafted"] == 1
    assert "step2_approved_to_send" in summary
    assert "step3_briefs_generated" in summary


# ---------------------------------------------------------------------------
# load_simulated_responses
# ---------------------------------------------------------------------------


def _write_responses_csv(rows: list[dict], path: str) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def _response_row(**overrides) -> dict:
    base = {
        "creator_id": "C001",
        "name": "Test Creator",
        "tier": "nano",
        "deal_type": "gift_seeding",
        "outreach_sent_date": "2026-05-20",
        "responded_yes": "True",
        "response_date": "2026-05-22",
        "response_notes": "Excited about the gifted product",
    }
    base.update(overrides)
    return base


def test_load_simulated_responses_returns_yes_ids(tmp_path):
    csv_path = str(tmp_path / "outreach_responses.csv")
    _write_responses_csv([_response_row(creator_id="C001", responded_yes="True")], csv_path)
    result = ph.load_simulated_responses(csv_path, ["C001"])
    assert result == ["C001"]


def test_load_simulated_responses_filters_to_approved_ids(tmp_path):
    csv_path = str(tmp_path / "outreach_responses.csv")
    rows = [
        _response_row(creator_id="C001", responded_yes="True"),
        _response_row(creator_id="C002", responded_yes="True"),
    ]
    _write_responses_csv(rows, csv_path)
    result = ph.load_simulated_responses(csv_path, ["C001"])
    assert result == ["C001"]
    assert "C002" not in result


def test_load_simulated_responses_excludes_no_responses(tmp_path):
    csv_path = str(tmp_path / "outreach_responses.csv")
    rows = [
        _response_row(creator_id="C001", responded_yes="True"),
        _response_row(creator_id="C002", responded_yes="False"),
    ]
    _write_responses_csv(rows, csv_path)
    result = ph.load_simulated_responses(csv_path, ["C001", "C002"])
    assert result == ["C001"]


def test_load_simulated_responses_missing_file_returns_empty(tmp_path):
    result = ph.load_simulated_responses(str(tmp_path / "nonexistent.csv"), ["C001"])
    assert result == []


def test_load_simulated_responses_empty_approved_ids(tmp_path):
    csv_path = str(tmp_path / "outreach_responses.csv")
    _write_responses_csv([_response_row(creator_id="C001", responded_yes="True")], csv_path)
    result = ph.load_simulated_responses(csv_path, [])
    assert result == []


def test_run_pipeline_automated_reads_simulated_responses(tmp_path):
    """Automated pipeline uses outreach_responses.csv to generate product briefs."""
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    intake_csv = str(tmp_path / "hypeauditor_intake_log.csv")
    responses_csv = str(tmp_path / "outreach_responses.csv")

    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)
    _write_csv([_intake_row()], intake_csv)
    _write_responses_csv([_response_row(creator_id="C001", responded_yes="True")], responses_csv)

    with patch("utils.connect.ask", return_value="Hi! Want to partner with Gymshark?"):
        summary = ph.run_pipeline(
            creators_path=creators_csv,
            crm_path=crm_csv,
            intake_path=intake_csv,
            responses_path=responses_csv,
            output_dir=str(tmp_path),
            human_review=False,
        )

    assert summary["step3_briefs_generated"] == 1


def test_run_pipeline_automated_no_responses_file_skips_briefs(tmp_path):
    """Automated pipeline skips briefs if no responses CSV exists."""
    creators_csv = str(tmp_path / "creators.csv")
    crm_csv = str(tmp_path / "crm_records.csv")
    intake_csv = str(tmp_path / "hypeauditor_intake_log.csv")

    _write_csv([_creator_row()], creators_csv)
    _write_csv([_crm_row()], crm_csv)
    _write_csv([_intake_row()], intake_csv)

    with patch("utils.connect.ask", return_value="Hi! Want to partner with Gymshark?"):
        summary = ph.run_pipeline(
            creators_path=creators_csv,
            crm_path=crm_csv,
            intake_path=intake_csv,
            responses_path=str(tmp_path / "nonexistent.csv"),
            output_dir=str(tmp_path),
            human_review=False,
        )

    assert summary["step3_briefs_generated"] == 0
