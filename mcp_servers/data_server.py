"""
data_server.py — Gymshark Pipeline Data Resource Server
--------------------------------------------------------
Read-only MCP resources that expose the pipeline's data files so the model
can browse creator profiles, CRM records, and campaign results without
running a tool.

Resources
---------
creators://all                — all creators from creators.csv as JSON
creators://{creator_id}       — single creator profile merged with CRM record
campaigns://summary           — portfolio metrics from campaign_performance.csv

Usage
-----
  uv run python mcp_servers/data_server.py        (stdio — used by Claude Code)
  uv run mcp dev mcp_servers/data_server.py       (inspector UI for testing)
"""

import csv
import json
import os
import sys

from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, ".."))

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

_DEFAULT_CREATORS = os.path.join(_PROJECT_ROOT, "data", "creators.csv")
_DEFAULT_CRM = os.path.join(_PROJECT_ROOT, "data", "crm_records.csv")
_DEFAULT_CAMPAIGNS = os.path.join(_PROJECT_ROOT, "data", "campaign_performance.csv")
_DEFAULT_PARTNERS = os.path.join(_PROJECT_ROOT, "data", "existing_partners.csv")

# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------


def _read_csv(path: str) -> list[dict]:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _index_by(rows: list[dict], key: str) -> dict:
    return {r[key]: r for r in rows if key in r}


# ---------------------------------------------------------------------------
# MCP SERVER
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Gymshark Pipeline Data",
    instructions=(
        "Read-only data resources for the Gymshark influencer pipeline. "
        "Use creators://all to browse prospects, creators://{creator_id} for a "
        "specific profile, and campaigns://summary for portfolio ROI metrics."
    ),
)


# ---------------------------------------------------------------------------
# RESOURCE 1 — creators://all
# ---------------------------------------------------------------------------


@mcp.resource("creators://all")
def get_all_creators() -> str:
    """
    All Gymshark creator prospects from data/creators.csv.

    Returns JSON array of creator profiles with key fields:
    creator_id, name, tier, subscribers, gymshark_brand_fit,
    brand_safety, outreach_recommended, suggested_deal_type.
    """
    rows = _read_csv(_DEFAULT_CREATORS)
    if not rows:
        return json.dumps({"error": "creators.csv not found — run data/collect_creators_gemin_2i.py first"})

    summary = [
        {
            "creator_id": r.get("creator_id"),
            "name": r.get("name"),
            "tier": r.get("tier"),
            "subscribers": r.get("subscribers"),
            "gymshark_brand_fit": r.get("gymshark_brand_fit"),
            "authenticity_score": r.get("authenticity_score"),
            "niche": r.get("niche"),
            "brand_safety": r.get("brand_safety"),
            "outreach_recommended": r.get("outreach_recommended"),
            "suggested_deal_type": r.get("suggested_deal_type"),
        }
        for r in rows
    ]
    return json.dumps({"count": len(summary), "creators": summary}, indent=2)


# ---------------------------------------------------------------------------
# RESOURCE 2 — creators://{creator_id}
# ---------------------------------------------------------------------------


@mcp.resource("creators://{creator_id}")
def get_creator(creator_id: str) -> str:
    """
    Full profile for a single creator, merged with their CRM record.

    Combines all fields from creators.csv and crm_records.csv for the
    given creator_id. Use this before drafting outreach to get the
    complete picture.

    Args:
        creator_id: The creator's ID string (e.g. C7BDE989)
    """
    creators = _index_by(_read_csv(_DEFAULT_CREATORS), "creator_id")
    crm = _index_by(_read_csv(_DEFAULT_CRM), "creator_id")

    if creator_id not in creators:
        return json.dumps({"error": f"creator_id '{creator_id}' not found in creators.csv"})

    profile = dict(creators[creator_id])
    if creator_id in crm:
        for k, v in crm[creator_id].items():
            if k not in profile or not profile[k]:
                profile[k] = v

    return json.dumps(profile, indent=2)


# ---------------------------------------------------------------------------
# RESOURCE 3 — campaigns://summary
# ---------------------------------------------------------------------------


@mcp.resource("campaigns://summary")
def get_campaign_summary() -> str:
    """
    Portfolio-level campaign performance summary from existing partners.

    Reads data/campaign_performance.csv and data/existing_partners.csv.
    Returns aggregate metrics by tier and deal type, plus top performers.

    Note: ROI is only meaningful for affiliate and brand_ambassador deals
    (UTM-tracked). gift_seeding and paid_creative_partnership are excluded
    from ROI comparisons.
    """
    campaigns = _read_csv(_DEFAULT_CAMPAIGNS)
    partners = _index_by(_read_csv(_DEFAULT_PARTNERS), "creator_id")

    if not campaigns:
        return json.dumps({"error": "campaign_performance.csv not found — run data/simulate_campaigns.py first"})

    total_budget = sum(float(r.get("budget_gbp", 0)) for r in campaigns)
    total_revenue = sum(float(r.get("revenue_attributed_gbp", 0)) for r in campaigns)
    roi_deals = [r for r in campaigns if r.get("deal_type") in ("affiliate", "brand_ambassador")]
    avg_roi = sum(float(r.get("roi_x", 0)) for r in roi_deals) / len(roi_deals) if roi_deals else None
    renewals = sum(1 for r in campaigns if r.get("renewal_recommended", "").lower() == "true")

    by_tier: dict[str, dict] = {}
    for r in campaigns:
        tier = r.get("tier", "unknown")
        cid = r.get("creator_id", "")
        name = partners.get(cid, {}).get("name", cid)
        roi = float(r.get("roi_x", 0))
        budget = float(r.get("budget_gbp", 0))
        by_tier.setdefault(tier, {"campaigns": 0, "total_budget_gbp": 0.0, "roi_values": [], "names": []})
        by_tier[tier]["campaigns"] += 1
        by_tier[tier]["total_budget_gbp"] += budget
        by_tier[tier]["roi_values"].append(roi)
        by_tier[tier]["names"].append(name)

    tier_summary = {
        tier: {
            "campaigns": v["campaigns"],
            "total_budget_gbp": round(v["total_budget_gbp"], 2),
            "avg_roi_x": round(sum(v["roi_values"]) / len(v["roi_values"]), 2) if v["roi_values"] else None,
            "creators": v["names"],
        }
        for tier, v in by_tier.items()
    }

    return json.dumps(
        {
            "total_campaigns": len(campaigns),
            "total_budget_gbp": round(total_budget, 2),
            "total_revenue_attributed_gbp": round(total_revenue, 2),
            "avg_roi_x_tracked_deals": round(avg_roi, 2) if avg_roi else None,
            "renewal_recommended_count": renewals,
            "by_tier": tier_summary,
        },
        indent=2,
    )


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
