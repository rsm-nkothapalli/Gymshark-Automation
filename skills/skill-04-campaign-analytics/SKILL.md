---
name: skill-04-campaign-analytics
description: Analyze Gymshark influencer campaign performance for existing partners. Use after campaigns have run to surface ROI by creator, tier, and deal type, identify who to renew or drop, and generate visualizations. Runs against data/campaign_performance.csv and data/existing_partners.csv — not the prospect list in creators.csv.
---

# Skill 04 — Campaign Performance Analytics
**Workflow Phase:** Phase 6 — Campaign Evaluation
**Data Required:** `data/campaign_performance.csv`, `data/existing_partners.csv`
**Skill Type:** Analytics (data visualization + statistical analysis)

---

## Goal
Analyze Gymshark's influencer campaign data to surface ROI by creator, tier, and deal type. Produce a clear performance summary with visualizations that a partnership manager can use to decide who to renew, who to drop, and where to invest next.

---

## When to Use This Skill
Use this skill when:
- A campaign cycle has ended and results need to be reviewed
- A manager asks: *"How did our influencer campaigns perform this quarter?"*
- The team needs to decide which creators to renew contracts with
- Budget allocation decisions for the next campaign cycle are being made

---

## Step-by-Step Instructions

### Step 1 — Load and merge the data
Call `load_campaign_data()` from `analytics_helpers.py`.  
This loads `campaign_performance.csv` and merges it with `creators.csv` on `creator_id`.

Confirm these columns are present in `campaign_performance.csv`:
- `campaign_id`, `creator_id`, `campaign_name`, `start_date`, `end_date`
- `total_cost_gbp`, `revenue_attributed_gbp`, `promo_redemptions`
- `utm_clicks`, `reach`, `impressions`, `deal_type`

If any column is missing, report it and stop.

### Step 2 — Calculate per-campaign metrics
For each campaign row, compute:

```
ROI (%)         = ((revenue_attributed_gbp - total_cost_gbp) / total_cost_gbp) × 100
Cost per Click  = total_cost_gbp / utm_clicks          (skip if utm_clicks = 0)
Conversion Rate = promo_redemptions / utm_clicks × 100 (skip if utm_clicks = 0)
Revenue per £1  = revenue_attributed_gbp / total_cost_gbp
```

Call `calculate_campaign_metrics(df)` from `analytics_helpers.py`.

### Step 3 — Aggregate by tier
Group by creator tier and calculate:
- Average ROI per tier
- Total revenue generated per tier
- Total spend per tier
- Average conversion rate per tier

This tells the team which tier is delivering the best return overall — not just which individual creators performed.

### Step 4 — Aggregate by deal type
Group by `deal_type` (affiliate, paid, seeding, ambassador) and calculate:
- Average ROI per deal type
- Average conversion rate per deal type
- Count of campaigns per deal type

This helps Gymshark understand which commercial structure drives the best returns.

### Step 5 — Identify top and bottom performers
**Top performers:** creators with ROI > 150% AND conversion rate > 3%  
**Bottom performers:** creators with ROI < 20% OR negative ROI  
**Borderline:** ROI between 20–80% — flag for review

For top performers: recommend renewal.  
For bottom performers: recommend dropping or renegotiating terms.

### Step 6 — Generate visualizations
Call `generate_charts(df, metrics_df)` from `analytics_helpers.py` to produce:

1. **Bar chart** — Average ROI by creator tier
2. **Scatter plot** — Total cost vs. revenue attributed (one dot per campaign, colored by tier)
3. **Bar chart** — Average ROI by deal type
4. **Ranked table** — Top 10 creators by ROI with tier and deal type columns

Charts are saved to `outputs/campaign_charts/`.

### Step 7 — Write the performance summary
Produce a written narrative covering:
1. Overall portfolio performance (total spend, total revenue, blended ROI)
2. Which tier outperformed — and why (reference specific metrics)
3. Which deal type delivered the best ROI
4. Top 3 creators to renew (with evidence)
5. Bottom 3 creators to drop or renegotiate (with evidence)
6. One strategic recommendation for the next campaign cycle

The narrative must cite specific numbers. Do not write vague summaries.

**Good example:**
> "Micro-tier creators delivered the highest average ROI at 187%, outperforming macro-tier by 62 percentage points. Affiliate deals consistently outperformed paid posts (avg 203% vs 141% ROI), suggesting Gymshark should shift more budget into affiliate structures for Q3."

**Bad example:**
> "Some creators did well. Micro influencers seem to be performing better than others."

---

## Output Format
```
GYMSHARK CAMPAIGN PERFORMANCE REPORT — [Date Range]
====================================================

PORTFOLIO SUMMARY
Total campaigns analysed: [N]
Total spend:              £[X]
Total revenue attributed: £[X]
Blended ROI:              [X]%

PERFORMANCE BY TIER
[Table: tier | avg_roi | total_revenue | total_spend | avg_conversion]

PERFORMANCE BY DEAL TYPE
[Table: deal_type | avg_roi | avg_conversion | campaign_count]

TOP PERFORMERS (recommend renewal)
[List with ROI and key metric]

BOTTOM PERFORMERS (recommend drop/renegotiate)
[List with ROI and reason]

STRATEGIC NARRATIVE
[4–6 sentence written summary with specific numbers]

CHARTS SAVED TO: outputs/campaign_charts/
```

---

## Edge Cases
- If a campaign has `total_cost_gbp = 0` (gifted/seeding), exclude it from ROI calculations but still report reach and redemptions.
- If a creator has only one campaign in the data, note that single-campaign conclusions are less reliable.
- If `revenue_attributed_gbp` is missing for any campaign, flag those rows and exclude them from ROI calculations — do not assume zero revenue.
- Campaigns shorter than 7 days may undercount redemptions — flag these as "potentially incomplete."
