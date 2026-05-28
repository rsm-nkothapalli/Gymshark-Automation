"""
gymshark_mcp_server.py — Gymshark Influencer Pipeline MCP Server
-----------------------------------------------------------------
Exposes three pipeline functions as callable MCP tools so Claude Code
(or any MCP-compatible client) can invoke them during a conversation.

Tools
-----
score_creators          Skill 01: score & shortlist from creators.csv
check_creator_risk      Skill 02: sentiment risk for a specific creator
draft_outreach_message  Skill 03: LLM-drafted outreach for a creator

Usage
-----
Run directly (stdio transport — used by Claude Code):
  uv run python mcp/gymshark_mcp_server.py

Or register in .claude/settings.json under mcpServers (see README).
"""

import importlib.util
import json
import os
import sys

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))
_SKILLS_DIR = os.path.join(_PROJECT_ROOT, "skills")

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _load_module(name: str, rel_path: str):
    abs_path = os.path.join(_SKILLS_DIR, rel_path)
    spec = importlib.util.spec_from_file_location(name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scoring = _load_module("scoring_helpers", "skill-01-creator-scoring/scoring_helpers.py")
_sentiment = _load_module("sentiment_helpers", "skill-02-sentiment-risk/sentiment_helpers.py")
_outreach = _load_module("outreach_helpers", "skill-03-outreach-drafting/outreach_helpers.py")

_DEFAULT_CREATORS = os.path.join(_PROJECT_ROOT, "data", "creators.csv")
_DEFAULT_SENTIMENT = os.path.join(_PROJECT_ROOT, "data", "comment_sentiment.csv")
_DEFAULT_CRM = os.path.join(_PROJECT_ROOT, "data", "crm_records.csv")

# ---------------------------------------------------------------------------
# MCP SERVER
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Gymshark Influencer Pipeline",
    instructions=(
        "Tools for the Gymshark influencer marketing pipeline. "
        "Use score_creators first to get a shortlist, then check_creator_risk "
        "for each shortlisted creator, then draft_outreach_message for approved ones."
    ),
)


# ---------------------------------------------------------------------------
# TOOL 1 — score_creators
# ---------------------------------------------------------------------------


@mcp.tool()
def score_creators() -> str:
    """
    Score and shortlist Gymshark creator prospects from data/creators.csv.

    Applies tier-minimum GFS thresholds and hard disqualifiers (RED brand
    safety, clickbait, competitor loyalty). Returns a ranked shortlist with
    a recommendation label per creator.

    Workflow step: Phase 1 — Creator Sourcing (Skill 01)

    Returns JSON with:
      eligible   — ranked list of creators that passed all filters
      ineligible — creators that failed a hard disqualifier (with reason)
    """
    try:
        eligible, ineligible = _scoring.shortlist_creators(_DEFAULT_CREATORS)
        return json.dumps(
            {
                "eligible_count": len(eligible),
                "ineligible_count": len(ineligible),
                "eligible": [
                    {
                        "creator_id": c["creator_id"],
                        "name": c["name"],
                        "tier": c["tier"],
                        "gymshark_brand_fit": c["gymshark_brand_fit"],
                        "recommendation": c.get("recommendation", ""),
                    }
                    for c in eligible
                ],
                "ineligible": [
                    {
                        "creator_id": c["creator_id"],
                        "name": c["name"],
                        "disqualification_reason": c.get("disqualification_reason", ""),
                    }
                    for c in ineligible
                ],
            },
            indent=2,
        )
    except FileNotFoundError as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# TOOL 2 — check_creator_risk
# ---------------------------------------------------------------------------


@mcp.tool()
def check_creator_risk(creator_id: str) -> str:
    """
    Run sentiment and brand risk analysis for a specific creator.

    Reads data/comment_sentiment.csv and computes positive/negative/flagged
    percentages, then assigns a risk level.

    Workflow step: Phase 1b — Pre-Outreach Safety Check (Skill 02)

    Args:
        creator_id: The creator's ID string (from creators.csv creator_id column)

    Returns JSON with:
      risk_level    — LOW | MEDIUM | HIGH | UNKNOWN
      recommendation — plain-English action
      metrics       — sentiment breakdown (positive_pct, flagged_pct, etc.)
      reason        — explanation of how the risk level was determined
    """
    try:
        rows = _sentiment.load_sentiment_data(creator_id, filepath=_DEFAULT_SENTIMENT)
        if not rows:
            return json.dumps(
                {
                    "creator_id": creator_id,
                    "risk_level": "UNKNOWN",
                    "reason": "No comment data found for this creator_id",
                    "recommendation": "Verify creator_id is correct, then expand comment sample",
                    "metrics": None,
                }
            )

        metrics = _sentiment.calculate_sentiment_metrics(rows)
        risk_level, emoji, reason = _sentiment.assign_risk_level(metrics)

        action_map = {
            "LOW": "Proceed to outreach — no brand safety concerns",
            "MEDIUM": "Human review required before outreach",
            "HIGH": "Do not proceed — brand safety risk identified",
            "UNKNOWN": "Expand comment sample before deciding",
        }

        return json.dumps(
            {
                "creator_id": creator_id,
                "risk_level": risk_level,
                "emoji": emoji,
                "reason": reason,
                "recommendation": action_map.get(risk_level, "Unknown"),
                "metrics": metrics,
            },
            indent=2,
        )
    except FileNotFoundError as exc:
        return json.dumps({"error": str(exc)})


# ---------------------------------------------------------------------------
# TOOL 3 — draft_outreach_message
# ---------------------------------------------------------------------------


@mcp.tool()
def draft_outreach_message(creator_id: str, model: str = "api-llama-4-scout") -> str:
    """
    Draft a personalized Gymshark outreach message for an approved creator.

    Loads the creator's profile from creators.csv and CRM record from
    crm_records.csv, selects tier-appropriate tone and word limit, then
    calls the LLM to write the message. Validates the draft against banned
    phrases and word-count rules.

    Workflow step: Phase 2 — Outreach Drafting (Skill 03)

    Args:
        creator_id: The creator's ID string (from creators.csv)
        model:      LLM model ID to use (default: api-llama-4-scout)

    Returns the formatted outreach draft as plain text, including:
      - Creator name, channel, deal type, word count header
      - Message body
      - Any validation issues flagged for human review
    """
    try:
        from utils.connect import ask

        context = _outreach.load_creator_context(creator_id, _DEFAULT_CREATORS, _DEFAULT_CRM)
        tier = context.get("tier", "micro")
        prompt = _outreach.build_outreach_prompt(context)
        message = ask(prompt, model=model)
        issues = _outreach.validate_message(message, tier)
        review_note = "; ".join(issues) if issues else ""
        return _outreach.format_outreach_output(context, message, review_note)

    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except FileNotFoundError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        return json.dumps({"error": f"Unexpected error: {exc}"})


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
