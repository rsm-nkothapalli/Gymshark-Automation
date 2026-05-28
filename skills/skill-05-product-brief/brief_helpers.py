"""
brief_helpers.py
----------------
Generates a product recommendation and creative brief for creators who
have accepted Gymshark outreach. Covers both gift_seeding and affiliate
deal types. Uses the LLM for the creative brief section.

Workflow position: after Skill 03 (outreach) and before Skill 04 (campaign analytics).
"""

import csv
import os
import random

from utils.connect import ask

MODEL = "api-llama-4-scout"

# ── Gymshark product lines ────────────────────────────────────────────────────

PRODUCT_LINES = {
    "adapt": {
        "description": "Seamless sculpt collection — leggings, sports bras, matching sets for yoga and pilates",
        "best_for": ["yoga", "pilates", "women's fitness"],
        "example_items": ["Adapt Animal Seamless Leggings", "Adapt Sports Bra", "Adapt Set"],
    },
    "seamless": {
        "description": "Everyday seamless range — versatile gym-to-street seamless sets and separates",
        "best_for": ["general fitness", "gym lifestyle", "women's fitness"],
        "example_items": ["Seamless T-Shirt", "Seamless Shorts", "Seamless Cycling Shorts"],
    },
    "form": {
        "description": "Technical compression range — form-fitting performance wear for intense training",
        "best_for": ["physique", "fitness model", "competition prep"],
        "example_items": ["Form Seamless Shorts", "Form Crop Top", "Form Long Sleeve"],
    },
    "cbum": {
        "description": "Chris Bumstead Essentials — classic bodybuilding aesthetic collab with CBum",
        "best_for": ["bodybuilding", "physique", "classic aesthetics"],
        "example_items": ["CBum T-Shirt", "CBum Shorts", "CBum Snapback"],
    },
    "training": {
        "description": "All-purpose gym training — shorts, t-shirts, hoodies, joggers",
        "best_for": ["gym lifestyle", "general fitness"],
        "example_items": ["Arrival Shorts", "Rest Day Hoodie", "Training Oversized T-Shirt"],
    },
    "lifting": {
        "description": "Strength and powerlifting — supportive shorts, tanks, wrist wraps",
        "best_for": ["powerlifting", "strength training"],
        "example_items": ["Legacy Lifting Shorts", "Power Lifting Tank", "Gymshark Wrist Wraps"],
    },
    "running": {
        "description": "Lightweight running gear — shorts, tights, breathable tops",
        "best_for": ["running", "cardio", "outdoor fitness"],
        "example_items": ["Speed Shorts", "Running Tights", "Training Tee"],
    },
    "hiit": {
        "description": "High-intensity training gear — durable, sweat-wicking pieces built for explosive workouts",
        "best_for": ["hiit", "crossfit", "circuit training"],
        "example_items": ["Flex Shorts", "Speed Shorts", "Training T-Shirt"],
    },
    "rest_day": {
        "description": "Casual athleisure — oversized hoodies, joggers, comfort sets",
        "best_for": ["lifestyle", "recovery", "gym lifestyle"],
        "example_items": ["Rest Day Hoodie", "Rest Day Joggers", "Crest Oversized T-Shirt"],
    },
}

# ── Product line selector ─────────────────────────────────────────────────────


def recommend_product_line(niche: str, gender_male_pct: float) -> str:
    """
    Rule-based product line selector based on creator niche and audience gender split.
    Returns a key from PRODUCT_LINES.
    """
    niche_lower = niche.lower()

    if "bodybuilding" in niche_lower:
        return "cbum"
    if any(k in niche_lower for k in ["powerlifting", "strength"]):
        return "lifting"
    if any(k in niche_lower for k in ["running", "cardio", "outdoor"]):
        return "running"
    if any(k in niche_lower for k in ["hiit", "crossfit", "circuit"]):
        return "hiit"
    if any(k in niche_lower for k in ["yoga", "pilates"]):
        return "adapt"
    if any(k in niche_lower for k in ["physique", "fitness model", "competition"]):
        return "form"
    if gender_male_pct < 45:
        return "seamless"
    return "training"


# ── Promo code generator (affiliate only) ─────────────────────────────────────


def generate_promo_code(creator_name: str) -> str:
    """Generate a unique Gymshark promo code for affiliate creators."""
    clean = "".join(c for c in creator_name.upper() if c.isalpha())[:4]
    return f"GS{clean}{random.randint(10, 99)}"


# ── Data loader ───────────────────────────────────────────────────────────────


def load_creator_brief_data(
    creator_id: str,
    creators_path: str = "data/creators.csv",
    crm_path: str = "data/crm_records.csv",
    intake_path: str = "data/hypeauditor_intake_log.csv",
) -> dict | None:
    """
    Merge creator profile, CRM deal type, and HypeAuditor audience data
    into a single dict for brief generation.
    Returns None if creator_id is not found.
    """
    creator_row = None
    with open(creators_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["creator_id"] == creator_id:
                creator_row = dict(row)
                break
    if creator_row is None:
        return None

    deal_type = "gift_seeding"
    with open(crm_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["creator_id"] == creator_id:
                deal_type = row.get("suggested_deal_type", deal_type)
                break

    gender_male_pct = 50.0
    top_country = "GB"
    with open(intake_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["creator_id"] == creator_id:
                gender_male_pct = float(row.get("ha_audience_male_pct") or 50)
                top_country = row.get("ha_top_country", "GB")
                break

    return {
        "creator_id": creator_id,
        "creator_name": creator_row.get("name", ""),
        "youtube_handle": creator_row.get("youtube_handle", ""),
        "tier": creator_row.get("tier", "nano"),
        "niche": creator_row.get("niche", "General Fitness"),
        "subscribers": int(creator_row.get("subscribers", 0)),
        "deal_type": deal_type,
        "gender_male_pct": gender_male_pct,
        "top_country": top_country,
        "ai_discovery_notes": creator_row.get("ai_discovery_notes", ""),
    }


# ── LLM creative brief ────────────────────────────────────────────────────────


def generate_creative_brief(creator_data: dict, product_line: str) -> str:
    """
    Use the LLM to write a personalized creative brief for this creator.
    Returns a short plain-text brief under 200 words.
    """
    line = PRODUCT_LINES[product_line]
    deal_note = (
        "This is a gifted partnership — no posting obligation, but we hope they love the kit."
        if creator_data["deal_type"] == "gift_seeding"
        else "This is an affiliate partnership — they earn commission on every sale via their promo code."
    )

    prompt = f"""You are a Gymshark brand partnerships manager writing a creative brief for an influencer.

Creator: {creator_data["creator_name"]} (@{creator_data["youtube_handle"]})
Tier: {creator_data["tier"]}
Niche: {creator_data["niche"]}
Audience: {100 - creator_data["gender_male_pct"]:.0f}% female / {creator_data["gender_male_pct"]:.0f}% male, top country: {creator_data["top_country"]}
Deal: {creator_data["deal_type"]} — {deal_note}
Product line to feature: {product_line.upper()} — {line["description"]}
Suggested items: {", ".join(line["example_items"])}

Write a creative brief in exactly this format (under 200 words total):

KEY MESSAGE: [one sentence — what Gymshark wants the audience to feel or do]
CONTENT FORMAT: [specific format suggestion e.g. YouTube workout integration, Instagram try-on Reel]
MUST INCLUDE: [two brand points they must mention]
AVOID: [one thing — tone, claim, or comparison to avoid]
POSTING WINDOW: [best time to post based on their niche and audience]

Be specific to this creator's niche and audience. No generic language."""

    try:
        return ask(prompt, model=MODEL)
    except Exception:
        line_info = PRODUCT_LINES[product_line]
        return (
            f"KEY MESSAGE: Share your authentic {creator_data['niche'].lower()} journey "
            f"with Gymshark's {product_line.upper()} collection.\n"
            f"CONTENT FORMAT: YouTube workout video integration or Instagram Reel try-on.\n"
            f"MUST INCLUDE: Gymshark quality and fit; use your unique link/code.\n"
            f"AVOID: Overclaiming specific performance benefits.\n"
            f"POSTING WINDOW: Tuesday–Thursday, 6–9 AM or 6–9 PM local time.\n\n"
            f"[Note: Generated from template — LLM unavailable. "
            f"Suggested items: {', '.join(line_info['example_items'])}]"
        )


# ── Full brief generator ──────────────────────────────────────────────────────


def generate_full_brief(creator_id: str) -> str:
    """
    Load creator data, select product line, generate creative brief,
    assign promo code if affiliate, and return a formatted output.
    """
    data = load_creator_brief_data(creator_id)
    if data is None:
        return f"Creator {creator_id} not found."

    if data["deal_type"] not in ("gift_seeding", "affiliate"):
        return f"{data['creator_name']} is on a {data['deal_type']} deal — use the paid creative brief process instead."

    product_line = recommend_product_line(data["niche"], data["gender_male_pct"])
    line_info = PRODUCT_LINES[product_line]
    brief = generate_creative_brief(data, product_line)

    lines = [
        f"PRODUCT BRIEF — {data['creator_name']} (@{data['youtube_handle']})",
        "=" * 55,
        f"Deal type:    {data['deal_type'].replace('_', ' ').upper()}",
        f"Tier:         {data['tier'].capitalize()}",
        f"Niche:        {data['niche']}",
        "",
        "PRODUCT RECOMMENDATION",
        f"  Line:   {product_line.upper()} — {line_info['description']}",
        f"  Send:   {', '.join(line_info['example_items'])}",
    ]

    if data["deal_type"] == "affiliate":
        promo = generate_promo_code(data["creator_name"])
        lines += [
            "",
            "AFFILIATE DETAILS",
            f"  Promo code:  {promo}",
            "  Commission:  12% of attributed revenue",
            "  Tracking:    UTM link + promo code redemptions",
        ]

    lines += [
        "",
        "CREATIVE BRIEF",
        brief,
    ]

    return "\n".join(lines)
