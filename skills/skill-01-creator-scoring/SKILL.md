---
name: skill-01-creator-scoring
description: Rank and shortlist Gymshark influencer candidates from data/creators.csv. Use this skill when a partnership manager asks "who should we contact this month?", when a new batch of creators needs screening, or when comparing creators head-to-head. All scores are pre-computed by data/collect_creators_gemin_2i.py — this skill reads those results and produces a ranked shortlist with justifications.
---

# Skill 01 — Creator Scoring & Shortlisting

**Workflow phase:** Phase 1 — Creator Sourcing  
**Data source:** `data/creators.csv` (produced by `data/collect_creators_gemin_2i.py`)

---

## Goal

Read the pre-scored creator candidates in `data/creators.csv` and produce a ranked shortlist that a Gymshark partnership manager can act on immediately — with a recommendation and a written justification for each creator.

All individual scores (`gymshark_brand_fit`, `authenticity_score`, `community_score`, `niche_alignment_score`, `production_quality`) and safety flags (`brand_safety`, `clickbait_detected`, `competitor_loyalty`, `outreach_recommended`) were calculated by `collect_creators_gemin_2i.py` using transcript analysis, comment scoring, and keyword signals. Do not recalculate them — read them directly from the CSV.

---

## When to Use This Skill

- A partnership manager asks: *"Who should we reach out to this month?"*
- A new batch of creators has been collected and needs to be reviewed
- Comparing two or more creators head-to-head for a specific campaign tier

---

## Step-by-Step Instructions

### Step 1 — Read creators.csv

Load `data/creators.csv`. Each row is one creator. The columns you need are:

| Column | What it means |
|--------|---------------|
| `name` | Creator display name |
| `youtube_handle` | Their @handle |
| `tier` | Size tier: nano / micro / mid / macro / mega |
| `subscribers` | Subscriber count |
| `gymshark_brand_fit` | Composite fit score 1–10 (primary ranking field) |
| `authenticity_score` | Organic/unsponsored feel, 1–10 |
| `community_score` | Audience engagement quality, 1–10 |
| `niche_alignment_score` | Fitness niche relevance, 1–10 |
| `production_quality` | Video production value, 1–10 |
| `brand_safety` | GREEN / AMBER / RED |
| `clickbait_detected` | True / False |
| `competitor_loyalty` | True / False |
| `outreach_recommended` | True / False — set by the collection script |
| `existing_partner` | True / False |
| `suggested_deal_type` | Deal type suggested at collection time |
| `brand_fit_reasoning` | Human-readable explanation of the brand fit score |

### Step 2 — Separate out ineligible creators

Do not score or rank creators who have **any** of these flags set by the collection script:

| Flag | Value | Reason |
|------|-------|--------|
| `brand_safety` | `RED` | Content safety risk |
| `competitor_loyalty` | `True` | Already aligned with a competing brand |
| `clickbait_detected` | `True` | Content quality disqualifier |
| `outreach_recommended` | `False` | Collection script already filtered them out |

List each ineligible creator and which flag disqualified them.

### Step 3 — Rank eligible creators

Sort the remaining creators by `gymshark_brand_fit` descending (highest score first). This is the composite score already computed by `collect_creators_gemin_2i.py` — it combines authenticity, niche alignment, community, production quality, and brand signals into a single 1–10 number.

For tiebreaks, rank the creator with higher `authenticity_score` above the other.

### Step 4 — Apply tier-aware minimum thresholds

Use `gymshark_brand_fit` (1–10 scale) against these tier minimums:

| Tier | Min brand fit | Notes |
|------|--------------|-------|
| Nano (< 10K) | 5.0 | Authenticity matters most |
| Micro (10K–100K) | 5.5 | Core Gymshark sweet spot |
| Mid (100K–500K) | 6.0 | Reach + credibility balance |
| Macro (500K–2M) | 6.5 | Must justify the cost |
| Mega (2M+) | 7.5 | Exceptional alignment only |

Label each ranked creator as one of:

- **Outreach now** — `gymshark_brand_fit` meets or exceeds the tier minimum
- **FLAG: borderline** — within 0.5 below the tier minimum; a human should decide
- **Do not recommend** — more than 0.5 below the tier minimum

Also flag (separately, do not remove from the list):
- `brand_safety = AMBER` → **FLAG: brand safety AMBER — human content review needed**
- `existing_partner = True` → **FLAG: existing partner — check renewal status**

### Step 5 — Write justifications for the top 5

For each of the top 5 ranked creators, write **1–2 sentences** that cite specific column values. Do not write generic praise.

**Good:**
> "Ranked #1 with brand fit 7.0/10. Strong authenticity signals (7/10) and high niche alignment (9/10) in women's fitness content, with no competitor loyalty or brand safety concerns — ideal nano-tier gift seeding candidate."

**Bad:**
> "Great creator, very authentic, highly recommended."

Use `brand_fit_reasoning` from the CSV as source material — it already explains *why* the collection script gave that score.

---

## Output Format

```
GYMSHARK CREATOR SHORTLIST — [Date]
============================================================
Source: data/creators.csv  |  Scored by: collect_creators_gemin_2i.py

INELIGIBLE (not ranked):
  x [name]  — [flag: reason]

RANKED SHORTLIST ([N] eligible creators):
Rank  Name                  Tier   Brand Fit  Recommendation
----  --------------------  -----  ---------  -------------------------
1     [name]                Nano   7.0        Outreach now
2     [name]                Nano   6.8        Outreach now
3     [name]                Micro  5.5        FLAG: brand safety AMBER

TOP 5 JUSTIFICATIONS:
1. [name] ([handle]): [1–2 sentences citing specific field values and brand_fit_reasoning]
...
```

---

## Edge Cases

- If `creators.csv` is empty or missing, stop and ask the user to run `collect_creators_gemin_2i.py` first.
- If all creators are ineligible, report that and suggest expanding the search — do not produce an empty shortlist silently.
- If `brand_fit_reasoning` is blank for a creator, write the justification from the individual score columns instead.
- If `tier` is not one of the five known values, use the micro threshold (5.5) as a safe default.
