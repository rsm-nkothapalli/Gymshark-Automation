---
name: skill-06-pipeline-workflow
description: >
  Run the full Gymshark influencer pipeline end-to-end: score creators (Skill 01),
  check audience risk (Skill 02), draft outreach messages (Skill 03), and generate
  product briefs for accepted creators (Skill 05) — all in one chained workflow with
  human decision gates at each transition. Use when a partnership manager wants to
  run the monthly batch, process all creators at once, or see a full pipeline summary.
---

# Skill 06 — AI Workflow Orchestrator

**Workflow phase:** Full pipeline (Phases 1 → 1b → 2 → 3)
**Chains:** Skill 01 → Skill 02 → Skill 03 → Skill 05
**Helper:** `pipeline_helpers.py`

---

## When to Use

Trigger this skill when the user says any of:
- "Run the monthly pipeline"
- "Process all creators end-to-end"
- "Run the full workflow"
- "Score, check risk, and draft outreach for everyone"
- "Who's approved for outreach this month?"
- "Run the batch"
- "Run the interactive pipeline"

Do NOT use for single-creator requests — those should use the individual skills directly.

---

## What It Does

Chains four skills with four human decision gates between them:

```
Step 1 — Score (Skill 01)
  Reads:  data/creators.csv
  Applies tier thresholds + disqualifiers
  Writes: outputs/pipeline/01_shortlisted.json

       ↓

HUMAN GATE 1 — Review Shortlist
  Shows all eligible creators with GFS scores
  Human confirms list or types IDs to exclude any creators
  Pipeline continues with confirmed list

       ↓

Step 2 — Risk Check (Skill 02)
  Reads:  data/comment_sentiment.csv
  Runs sentiment analysis for every confirmed creator
  Writes: outputs/pipeline/02_risk_assessment.json

       ↓

Step 3 — Decision Gate (automated)
  ✅ LOW risk   → auto-approved
  ⚠️ MEDIUM/UNKNOWN → held for human review
  🚫 HIGH risk  → auto-skipped

       ↓

HUMAN GATE 2 — Risk Review
  Shows auto-approved (LOW) and auto-skipped (HIGH) — no action needed
  For each MEDIUM/UNKNOWN creator: shows risk reason, asks approve or skip
  Final approved list = LOW + any manually approved creators

       ↓

Step 4 — Outreach Drafting (Skill 03)
  Generates LLM draft for each approved creator
  Writes: outputs/pipeline/04_outreach_drafts/{creator_id}.txt

       ↓

HUMAN GATE 3 — Draft Review
  Displays each outreach draft in full
  Human approves or marks for revision, one by one
  Only approved drafts move forward

       ↓

HUMAN GATE 4 — Outreach Responses
  Human enters which creators responded YES to the offer
  These creators move to product brief generation

       ↓

Step 5 — Product Brief (Skill 05)
  For each creator who said yes: recommends product line, generates creative brief
  Assigns promo code for affiliate deals
  Writes: outputs/pipeline/06_product_briefs/{creator_id}.txt

       ↓

Writes: outputs/pipeline/05_pipeline_summary.json
```

---

## Step-by-Step Instructions

### Step 1 — Run the pipeline

Always run using one of these exact bash commands from the project root. Do NOT attempt to import or load helpers manually — folder names contain hyphens that break standard Python imports.

**Interactive mode (with human gates):**
```bash
uv run python skills/skills/skill-06-pipeline-workflow/pipeline_helpers.py --interactive
```

**Automated mode (no prompts):**
```bash
uv run python skills/skills/skill-06-pipeline-workflow/pipeline_helpers.py
```

**Dry run (stops after Step 3, no LLM calls):**
```bash
uv run python skills/skills/skill-06-pipeline-workflow/pipeline_helpers.py --dry-run
```

### Step 2 — Human gates (interactive mode only)

The pipeline pauses at four gates and waits for input before continuing:

| Gate | When | What human decides |
|------|------|--------------------|
| Gate 1 | After scoring | Confirm shortlist or exclude any creators |
| Gate 2 | After risk check | Approve or skip each MEDIUM/UNKNOWN creator |
| Gate 3 | After outreach drafts | Approve each draft or mark for revision |
| Gate 4 | After outreach sent | Record which creators said yes → triggers product brief |

### Step 3 — Read the summary

After the pipeline completes, present results in this format:

```
PIPELINE SUMMARY — [run_at]
============================================================
Step 1 (Scoring)    [N] eligible  |  [N] disqualified
Step 2 (Risk)       [N] checked
Step 3 (Decision)   [N] approved  |  [N] flagged  |  [N] skipped
Step 4 (Outreach)   [N] drafts written  |  [N] approved to send
Step 5 (Briefs)     [N] product briefs generated

APPROVED FOR OUTREACH:
  ✅ [Creator Name] ([tier])

FLAGGED FOR HUMAN REVIEW (Gate 2):
  ⚠️  [Creator Name] — [risk reason]

SKIPPED (HIGH RISK):
  🚫 [Creator Name] — [risk reason]

Outreach drafts:  outputs/pipeline/04_outreach_drafts/
Product briefs:   outputs/pipeline/06_product_briefs/
Full results:     outputs/pipeline/05_pipeline_summary.json
```

### Step 4 — Handle follow-up requests

After presenting the summary, offer:
- **"Show me the outreach draft for [name]"** → read the relevant `.txt` file from `outputs/pipeline/04_outreach_drafts/`
- **"Show me the product brief for [name]"** → read the relevant `.txt` file from `outputs/pipeline/06_product_briefs/`
- **"Check risk details for [name]"** → read `02_risk_assessment.json` for that creator's metrics

---

## Decision Gate Rules

| Risk Level | Automated Action | Human Gate 2 |
|------------|-----------------|--------------|
| 🟢 LOW | Approved | Shown for info — no action needed |
| 🟡 MEDIUM | Held | Human decides: approve or skip |
| ⚪ UNKNOWN | Held | Human decides: approve or skip |
| 🔴 HIGH | Skipped | Shown for info — no action needed |

---

## Intermediate Output Files

| File | Contains |
|------|---------|
| `outputs/pipeline/01_shortlisted.json` | Eligible + ineligible creators from scoring |
| `outputs/pipeline/02_risk_assessment.json` | Risk level + sentiment metrics per creator |
| `outputs/pipeline/03_decision.json` | Approved / flagged / skipped breakdown |
| `outputs/pipeline/04_outreach_drafts/{id}.txt` | Draft message per approved creator |
| `outputs/pipeline/05_pipeline_summary.json` | Full run summary |
| `outputs/pipeline/06_product_briefs/{id}.txt` | Product brief per creator who said yes |

---

## Edge Cases

- **`creators.csv` missing** → stop and ask user to run `data/collect_creators_gemin_2i.py` first
- **No creators pass scoring** → report all disqualification reasons; suggest expanding search
- **All risk checks return UNKNOWN** → comment data is too sparse; all held at Gate 2 for human decision
- **LLM call fails for outreach** → pipeline writes a fallback template draft and flags with a review note
- **No creators approved at Gate 3** → Gate 4 skipped; no product briefs generated
- **Dry run (no LLM)** → pass `--dry-run` flag or call `run_pipeline(draft_outreach=False)` to stop after Step 3
- **Automated mode** → pass no flags or call `run_pipeline(human_review=False)`; gates are skipped, all LOW-risk creators auto-drafted
