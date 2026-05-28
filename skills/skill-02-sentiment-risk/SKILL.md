---
name: skill-02-sentiment-risk
description: Analyze comment sentiment and brand risk for a creator before outreach is sent. Use this skill after creator scoring (Skill 01) to check whether a creator's audience is safe for Gymshark to be associated with. Produces a risk level (LOW/MEDIUM/HIGH), sentiment breakdown, and a recommendation to proceed or not.
---

# Skill 02 — Sentiment & Brand Risk Analysis
**Workflow Phase:** Phase 1 — Creator Sourcing (pre-outreach screening)
**Data Required:** `data/comment_sentiment.csv`
**Skill Type:** Analytics (NLP sentiment analysis + risk scoring)

---

## Goal
Analyze the comment sentiment data for one or more creators to assess audience health and brand risk. Produce a risk score per creator and flag any whose audiences show patterns that could harm Gymshark's brand if a partnership went public.

---

## When to Use This Skill
Use this skill when:
- A creator has passed initial scoring (Skill 01) and needs a deeper audience check before outreach is sent
- A manager asks: *"Is [creator]'s audience safe for Gymshark to be associated with?"*
- Bulk pre-screening a cohort of shortlisted creators before the partnership team reviews them

---

## Step-by-Step Instructions

### Step 1 — Load and filter the data
Call `load_sentiment_data(creator_id)` from `sentiment_helpers.py`.  
This loads all rows from `comment_sentiment.csv` for the specified creator.

Check that these columns are present:
- `comment_id`, `creator_id`, `comment_text`, `sentiment_label`, `sentiment_score`, `category`, `flagged`

If `comment_text` is empty for more than 50% of rows, flag as "insufficient data" and stop.

### Step 2 — Calculate baseline sentiment metrics
For the creator's comment pool, compute:

```
positive_pct     = (count where sentiment_label = "POSITIVE") / total × 100
negative_pct     = (count where sentiment_label = "NEGATIVE") / total × 100
neutral_pct      = (count where sentiment_label = "NEUTRAL")  / total × 100
avg_sentiment    = mean of sentiment_score (0–1 scale, higher = more positive)
flagged_pct      = (count where flagged = True) / total × 100
```

Call `calculate_sentiment_metrics(df)` from `sentiment_helpers.py`.

### Step 3 — Categorize flagged comments
Group flagged comments by `category`. The categories used in `comment_sentiment.csv` are:
- `body_image` — comments that promote unhealthy body standards or diet culture
- `toxicity` — hate speech, harassment, or aggressive language
- `spam` — bot-like or promotional comments
- `competitor_mention` — mentions of competing brands
- `negative_product` — complaints about Gymshark products specifically (post-campaign only)

Count occurrences per category. A creator with >5% `body_image` or `toxicity` comments is a material brand risk.

### Step 4 — Assign Brand Risk Level
Use this decision table:

| Condition | Risk Level |
|---|---|
| flagged_pct > 15% OR toxicity > 5% | 🔴 HIGH — Do not proceed |
| body_image > 5% OR flagged_pct 8–15% | 🟡 MEDIUM — Human review required |
| flagged_pct < 8% AND avg_sentiment > 0.65 | 🟢 LOW — Safe to proceed |
| Insufficient data (<50 comments) | ⚪ UNKNOWN — Expand sample |

Call `assign_risk_level(metrics)` from `sentiment_helpers.py`.

### Step 5 — Surface representative examples
For each flagged category present, pull up to **3 example comments** (anonymized — show first 3 words only + "[...]").  
This gives the human reviewer concrete evidence without reproducing full comments.

**Example format:**
> body_image (12 comments): "She looks so...[3 examples shown]"

### Step 6 — Write the risk assessment
Produce a structured report per creator:
- Risk level (with color code)
- Key metrics (positive %, negative %, flagged %)
- Category breakdown of flags
- 3-sentence narrative interpreting the findings
- Recommendation (proceed / human review / do not proceed)

The narrative must reference specific percentages. Do not write vague assessments.

**Good example:**
> "This creator's audience shows strong positive sentiment (78%) with a low flagged rate (4%). The small number of flagged comments are concentrated in spam/bot activity, which is a common and low-risk pattern at this follower count. Recommended to proceed to outreach — no brand safety concerns identified."

**Bad example:**
> "Sentiment looks mostly fine. A few negative comments but nothing too bad."

---

## Output Format
```
BRAND RISK ASSESSMENT — [Creator Name] (@[handle])
===================================================
Risk Level: 🟢 LOW / 🟡 MEDIUM / 🔴 HIGH / ⚪ UNKNOWN
Comments analysed: [N]

SENTIMENT BREAKDOWN
  Positive:  [X]%
  Neutral:   [X]%
  Negative:  [X]%
  Avg score: [X]/1.0
  Flagged:   [X]%

FLAG CATEGORIES
  [category]: [count] comments
  ...

EXAMPLE FLAGS (anonymized)
  [category]: "[first 3 words]...", "[first 3 words]...", "[first 3 words]..."

ASSESSMENT
[3-sentence narrative]

RECOMMENDATION: [Proceed to outreach / Human review required / Do not proceed]
```

---

## Edge Cases
- If a creator has fewer than 50 comments in the dataset, assign UNKNOWN risk and recommend expanding the sample before making a decision.
- Post-campaign context: if `negative_product` category spikes during a campaign period, flag this separately — it may indicate product quality issues, not creator fault.
- Do not reproduce full comment text in the output — show first 3 words + "[...]" only.
- If `sentiment_score` values are all identical (e.g. all 0.5), this may indicate a data quality issue — flag it.
- Body image flags are weighted more heavily than spam for Gymshark specifically — a fitness brand associated with toxic body culture is a significant reputational risk.
