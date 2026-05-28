"""
simulate_campaigns.py
---------------------
Generates realistic campaign performance data for existing Gymshark partners
defined in data/existing_partners.csv.

Partners are real Gymshark creators across tiers. Gift seeding is excluded —
only trackable deal types (affiliate, paid_creative_partnership, brand_ambassador)
are simulated so that ROI and revenue attribution are meaningful.

Benchmark sources:
- Influencer Marketing Hub UK Report 2025
- HypeAuditor State of Influencer Marketing 2025
- Creator IQ UK Fitness Niche Rate Card 2025

Output: data/campaign_performance.csv
"""

import csv
import random
import uuid
from datetime import datetime, timedelta

random.seed(42)

AFFILIATE_COMMISSION_RATE = 0.12  # 12% of attributed revenue

# ── Realistic revenue ranges by (tier, deal_type) ────────────────────────────
# Based on UK fitness influencer market benchmarks at Gymshark's scale
REVENUE_RANGES = {
    ("mega", "brand_ambassador"): (150_000, 500_000),
    ("macro", "brand_ambassador"): (60_000, 200_000),
    ("mid", "brand_ambassador"): (25_000, 80_000),
    ("mega", "paid_creative_partnership"): (40_000, 180_000),
    ("macro", "paid_creative_partnership"): (20_000, 80_000),
    ("mid", "paid_creative_partnership"): (12_000, 50_000),
    ("micro", "paid_creative_partnership"): (5_000, 20_000),
    ("micro", "affiliate"): (5_000, 25_000),
    ("nano", "affiliate"): (1_000, 6_000),
}

# ── Budget ranges by deal type and tier (GBP) ────────────────────────────────
BUDGET_RANGES = {
    ("mega", "brand_ambassador"): (30_000, 80_000),
    ("macro", "brand_ambassador"): (12_000, 35_000),
    ("mid", "brand_ambassador"): (5_000, 15_000),
    ("mega", "paid_creative_partnership"): (8_000, 25_000),
    ("macro", "paid_creative_partnership"): (4_000, 12_000),
    ("mid", "paid_creative_partnership"): (2_000, 8_000),
    ("micro", "paid_creative_partnership"): (500, 3_000),
    ("micro", "affiliate"): (0, 0),  # commission only
    ("nano", "affiliate"): (0, 0),
}

# ── Reach rates and conversion by tier ───────────────────────────────────────
YOUTUBE_REACH_RATE = 0.35

CONVERSION_RATES = {
    "nano": (0.04, 0.08),
    "micro": (0.03, 0.06),
    "mid": (0.02, 0.04),
    "macro": (0.015, 0.035),
    "mega": (0.01, 0.025),
}

# Campaign duration by deal type
CAMPAIGN_DURATIONS = {
    "brand_ambassador": (90, 180),
    "paid_creative_partnership": (14, 45),
    "affiliate": (30, 75),
}

CAMPAIGN_STATUSES = ["completed", "completed", "completed", "live", "paused"]


def random_date_range(deal_type, days_ago_max=400):
    min_dur, max_dur = CAMPAIGN_DURATIONS.get(deal_type, (30, 60))
    start_offset = random.randint(min_dur + 30, days_ago_max)
    start = datetime.today() - timedelta(days=start_offset)
    duration = random.randint(min_dur, max_dur)
    end = start + timedelta(days=duration)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def generate_campaign(partner: dict) -> dict:
    tier = partner["tier"]
    deal_type = partner["deal_type"]
    subs = int(partner["subscribers"])
    er = float(partner.get("estimated_er_pct", 6.0))

    # Reach and engagement
    reach = int(subs * YOUTUBE_REACH_RATE * random.uniform(0.7, 1.3))
    impressions = int(reach * random.uniform(1.5, 2.8))
    engagements = int(subs * (er / 100) * random.uniform(0.85, 1.15))

    # UTM clicks (meaningful for affiliate and paid creative)
    utm_clicks = int(reach * random.uniform(0.025, 0.07))

    # Promo redemptions
    conv_lo, conv_hi = CONVERSION_RATES.get(tier, (0.02, 0.04))
    redemptions = int(reach * random.uniform(conv_lo, conv_hi))

    # Revenue
    rev_lo, rev_hi = REVENUE_RANGES.get(
        (tier, deal_type),
        REVENUE_RANGES.get(("micro", deal_type), (5_000, 20_000)),
    )
    revenue_gbp = round(random.uniform(rev_lo, rev_hi), 2)

    # Budget
    if deal_type == "affiliate":
        budget_gbp = round(revenue_gbp * AFFILIATE_COMMISSION_RATE, 2)
    else:
        b_lo, b_hi = BUDGET_RANGES.get(
            (tier, deal_type),
            BUDGET_RANGES.get(("micro", deal_type), (500, 5_000)),
        )
        budget_gbp = round(random.uniform(b_lo, b_hi), 2)

    roi_x = round(revenue_gbp / budget_gbp, 2) if budget_gbp > 0 else None
    aov = round(revenue_gbp / redemptions, 2) if redemptions > 0 else round(random.uniform(48, 82), 2)
    start_date, end_date = random_date_range(deal_type)
    status = random.choice(CAMPAIGN_STATUSES)
    promo_code = f"GS{partner['name'].replace(' ', '').upper()[:4]}{random.randint(10, 99)}"

    return {
        "campaign_id": str(uuid.uuid4())[:8].upper(),
        "creator_id": partner["creator_id"],
        "creator_name": partner["name"],
        "tier": tier,
        "deal_type": deal_type,
        "platform": "YouTube",
        "campaign_start": start_date,
        "campaign_end": end_date,
        "status": status,
        "promo_code": promo_code,
        "budget_gbp": budget_gbp,
        "reach": reach,
        "impressions": impressions,
        "total_engagements": engagements,
        "utm_clicks": utm_clicks,
        "promo_redemptions": redemptions,
        "revenue_attributed_gbp": revenue_gbp,
        "roi_x": roi_x,
        "avg_order_value_gbp": aov,
        "renewal_recommended": "Yes" if (roi_x and roi_x >= 2.5) else "No",
    }


# ── Load partners ─────────────────────────────────────────────────────────────
input_path = "data/existing_partners.csv"
with open(input_path, newline="", encoding="utf-8") as f:
    partners = list(csv.DictReader(f))

print(f"Loaded {len(partners)} existing partners from {input_path}")

# Validate no gift_seeding slipped through
trackable = [p for p in partners if p["deal_type"] != "gift_seeding"]
skipped = len(partners) - len(trackable)
if skipped:
    print(f"  Skipped {skipped} gift_seeding partner(s) — no trackable revenue")

campaigns = []
for partner in trackable:
    # Brand ambassadors typically have 2 campaign periods; others have 1
    num_campaigns = 2 if partner["deal_type"] == "brand_ambassador" else random.choices([1, 2], weights=[60, 40])[0]
    for _ in range(num_campaigns):
        campaigns.append(generate_campaign(partner))

# ── Write CSV ─────────────────────────────────────────────────────────────────
FIELDS = [
    "campaign_id",
    "creator_id",
    "creator_name",
    "tier",
    "deal_type",
    "platform",
    "campaign_start",
    "campaign_end",
    "status",
    "promo_code",
    "budget_gbp",
    "reach",
    "impressions",
    "total_engagements",
    "utm_clicks",
    "promo_redemptions",
    "revenue_attributed_gbp",
    "roi_x",
    "avg_order_value_gbp",
    "renewal_recommended",
]

output_path = "data/campaign_performance.csv"
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(campaigns)

total_rev = sum(c["revenue_attributed_gbp"] for c in campaigns)
total_budget = sum(c["budget_gbp"] for c in campaigns)

print(f"\n✓  {len(campaigns)} campaign records written to {output_path}")
print(f"   Total revenue:  £{total_rev:,.0f}")
print(f"   Total spend:    £{total_budget:,.0f}")
print(f"   Portfolio ROI:  {total_rev / total_budget:.1f}x" if total_budget > 0 else "   Portfolio ROI: N/A")
print()
for p in trackable:
    count = sum(1 for c in campaigns if c["creator_id"] == p["creator_id"])
    rev = sum(c["revenue_attributed_gbp"] for c in campaigns if c["creator_id"] == p["creator_id"])
    print(f"   {p['name']:25s} {p['deal_type']:30s} {count} campaign(s)  £{rev:>12,.0f} revenue")
