"""
simulate_crm.py
---------------
Generates CRM relationship records for the 8 real Gymshark creator
candidates discovered by collect_creators_gemini.py

Since these are UNDISCOVERED creators (not existing partners), all
records start at "Prospect" status — they haven't been contacted yet.
This is the starting point for the outreach workflow.

Reads directly from creators.csv

Output: crm_records.csv
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(7)

# ── Account managers ──────────────────────────────────────────────────────────
ACCOUNT_MANAGERS = ["Stephanie H.", "James T.", "Aisha K.", "Ben R.", "Charlotte M."]

# ── Outreach channels — how Gymshark would first contact them ─────────────────
OUTREACH_CHANNELS = ["Instagram DM", "Email via Management", "YouTube Comment", "Direct Email", "Event"]

# ── AI-generated outreach message templates ───────────────────────────────────
# These mirror what the GenAI pipeline would auto-draft for each creator
OUTREACH_NOTES = [
    "AI pipeline flagged as high brand-fit candidate. Transcript analysis showed strong authentic fitness content. Recommended for gifted product seeding outreach.",
    "Discovered via organic Gymshark mention in YouTube video. Creator purchased product themselves — strong authenticity signal. Suggested initial contact: gifted set + affiliate link.",
    "Rule-based transcript scoring: authenticity 7/10, community signals present. No existing brand deals detected. Priority: send PR package and monitor engagement.",
    "Creator organically mentioned Gymshark in review video. No promo code or partnership signals found. Ideal nano affiliate candidate for fitness leggings range.",
    "Identified via YouTube search. Women's fitness niche, strong fit-check content. Recommended for gifted seeding with affiliate code to track conversion.",
    "Comment sentiment analysis shows 78%+ positive audience response. Purchase intent signals detected in comments. High potential for affiliate partnership.",
    "Transcript shows genuine product feedback — mentions specific fit details (squat proof, waistband quality). Authentic voice aligns with Gymshark values.",
    "AI flagged: creator talks about buying Gymshark with own money. No competitor brand loyalty detected. Recommended first step: send DM + gifted set.",
]


# ── Priority levels based on brand fit score ─────────────────────────────────
def get_priority(brand_fit_score):
    score = float(brand_fit_score) if brand_fit_score != "N/A" else 5.0
    if score >= 7.0:
        return "High"
    elif score >= 6.0:
        return "Medium"
    else:
        return "Low"


def random_future_date(days_ahead_max=30):
    offset = random.randint(1, days_ahead_max)
    return (datetime.today() + timedelta(days=offset)).strftime("%Y-%m-%d")


def generate_crm_record(creator: dict) -> dict:
    brand_fit = creator.get("gymshark_brand_fit", "5.0")
    priority = get_priority(brand_fit)

    return {
        "crm_id": str(uuid.uuid4())[:8].upper(),
        "creator_id": creator["creator_id"],
        "creator_name": creator["name"],
        "youtube_handle": creator["youtube_handle"],
        "tier": creator["tier"],
        "niche": creator["niche"],
        "subscribers": creator["subscribers"],
        "country": creator["country"],
        # Pipeline status — all Prospect since these are undiscovered
        "relationship_status": "Prospect",
        "pipeline_stage": "AI Discovery — Pending Human Review",
        "priority": priority,
        "account_manager": random.choice(ACCOUNT_MANAGERS),
        # Outreach plan
        "outreach_channel": random.choice(OUTREACH_CHANNELS),
        "suggested_deal_type": creator["suggested_deal_type"],
        "proposed_next_step": "Send gifted set + affiliate link proposal",
        "follow_up_date": random_future_date(30),
        # Scores from creator discovery
        "gymshark_brand_fit": creator.get("gymshark_brand_fit", "N/A"),
        "authenticity_score": creator.get("authenticity_score", "N/A"),
        "comment_sentiment_score": creator.get("comment_sentiment_score", "N/A"),
        "creator_trust_score": creator.get("creator_trust_score", "N/A"),
        "brand_safety": creator.get("brand_safety", "GREEN"),
        # AI pipeline notes
        "ai_discovery_notes": random.choice(OUTREACH_NOTES),
        "transcript_analyzed": creator.get("transcript_available", False),
        "comments_analyzed": creator.get("comments_available", False),
        "purchase_intent_signals": creator.get("purchase_intent_count", 0),
        "positive_comment_pct": creator.get("positive_comment_pct", 0),
        # Contract fields — empty until outreach succeeds
        "contract_start": "N/A",
        "contract_end": "N/A",
        "contract_value_gbp": "N/A",
        "exclusivity_terms": "N/A",
        # Flags
        "existing_partner": creator.get("existing_partner", False),
        "competitor_loyalty": creator.get("competitor_loyalty", False),
        "red_flags": creator.get("red_flags", "none"),
        "crm_created": datetime.today().strftime("%Y-%m-%d"),
        "crm_last_updated": datetime.today().strftime("%Y-%m-%d"),
        "source": "AI Creator Discovery Pipeline",
    }


# ── Load creators ──────────────────────────────────────────────────────────────
with open("creators.csv", newline="", encoding="utf-8") as f:
    creators = list(csv.DictReader(f))

print(f"Loaded {len(creators)} creators from creators.csv")

crm_records = [generate_crm_record(c) for c in creators]

# ── Write CSV ──────────────────────────────────────────────────────────────────
FIELDS = [
    "crm_id",
    "creator_id",
    "creator_name",
    "youtube_handle",
    "tier",
    "niche",
    "subscribers",
    "country",
    "relationship_status",
    "pipeline_stage",
    "priority",
    "account_manager",
    "outreach_channel",
    "suggested_deal_type",
    "proposed_next_step",
    "follow_up_date",
    "gymshark_brand_fit",
    "authenticity_score",
    "comment_sentiment_score",
    "creator_trust_score",
    "brand_safety",
    "ai_discovery_notes",
    "transcript_analyzed",
    "comments_analyzed",
    "purchase_intent_signals",
    "positive_comment_pct",
    "contract_start",
    "contract_end",
    "contract_value_gbp",
    "exclusivity_terms",
    "existing_partner",
    "competitor_loyalty",
    "red_flags",
    "crm_created",
    "crm_last_updated",
    "source",
]

with open("crm_records.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(crm_records)

print(f"✓  {len(crm_records)} CRM records written to crm_records.csv")
print(f"   All creators set to: Prospect (undiscovered — not yet contacted)")
print(f"\n   Priority breakdown:")
for p in ["High", "Medium", "Low"]:
    count = sum(1 for r in crm_records if r["priority"] == p)
    print(f"   {p:6s}: {count}")
print(f"\n   Creator pipeline:")
for r in crm_records:
    print(
        f"   {r['creator_name']:30s} | Priority: {r['priority']:6s} | Fit: {r['gymshark_brand_fit']}/10 | {r['outreach_channel']}"
    )
