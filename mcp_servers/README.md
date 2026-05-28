# Gymshark Pipeline — MCP Servers

Two FastMCP servers expose the pipeline's Python functions and data files to
Claude Code (or any MCP-compatible client).

Registered in `.mcp.json`:

| Server | Module | What it exposes |
|--------|--------|-----------------|
| `gymshark-tools` | `gymshark_mcp_server.py` | Callable tools — runs pipeline steps |
| `gymshark-data` | `data_server.py` | Read-only resources — browse raw data |

---

## Tools server — `gymshark_mcp_server.py`

### Tool 1: `score_creators`

| | |
|---|---|
| **Purpose** | Score and shortlist creator prospects (Skill 01) |
| **Inputs** | None — reads `data/creators.csv` |
| **Returns** | JSON: `eligible_count`, `ineligible_count`, `eligible[]` (creator_id, name, tier, gymshark_brand_fit, recommendation), `ineligible[]` (creator_id, name, disqualification_reason) |
| **Workflow step** | Phase 1 — Creator Sourcing |
| **Underlying function** | `skills/skill-01-creator-scoring/scoring_helpers.py → shortlist_creators()` |

### Tool 2: `check_creator_risk`

| | |
|---|---|
| **Purpose** | Run sentiment and brand-safety analysis for one creator (Skill 02) |
| **Inputs** | `creator_id: str` |
| **Returns** | JSON: `risk_level` (LOW/MEDIUM/HIGH/UNKNOWN), `emoji`, `reason`, `recommendation`, `metrics` (positive_pct, negative_pct, flagged_pct, avg_sentiment, purchase_intent_count) |
| **Workflow step** | Phase 1b — Pre-Outreach Safety Check |
| **Underlying function** | `skills/skill-02-sentiment-risk/sentiment_helpers.py → calculate_sentiment_metrics(), assign_risk_level()` |

### Tool 3: `draft_outreach_message`

| | |
|---|---|
| **Purpose** | Draft a personalised outreach message for an approved creator (Skill 03) |
| **Inputs** | `creator_id: str`, `model: str` (default: `api-llama-4-scout`) |
| **Returns** | Formatted plain-text outreach draft with header (name, channel, deal type, word count) and any validation issues flagged for human review |
| **Workflow step** | Phase 2 — Outreach Drafting |
| **Underlying function** | `skills/skill-03-outreach-drafting/outreach_helpers.py → build_outreach_prompt(), format_outreach_output()` |

### How the model decides which tool to call

The model follows the pipeline sequence:

1. Call `score_creators` → get ranked shortlist
2. For each eligible creator, call `check_creator_risk(creator_id)` → get risk level
3. For creators with `risk_level == "LOW"` (or manually approved MEDIUM), call `draft_outreach_message(creator_id)` → get formatted draft

The `gymshark-tools` server's `instructions` field encodes this order explicitly, so Claude Code surfaces the right tool at each step without needing to re-read the pipeline logic.

---

## Data server — `data_server.py`

Read-only resources the model can browse before or during a pipeline run.

### Resource 1: `creators://all`

| | |
|---|---|
| **Purpose** | Browse all creator prospects |
| **Returns** | JSON array — creator_id, name, tier, subscribers, gymshark_brand_fit, brand_safety, outreach_recommended, suggested_deal_type |
| **Source file** | `data/creators.csv` |

### Resource 2: `creators://{creator_id}`

| | |
|---|---|
| **Purpose** | Full profile for one creator, merged with their CRM record |
| **Returns** | JSON object — all fields from creators.csv + crm_records.csv |
| **Source files** | `data/creators.csv` + `data/crm_records.csv` |

### Resource 3: `campaigns://summary`

| | |
|---|---|
| **Purpose** | Portfolio-level campaign performance for existing partners |
| **Returns** | JSON — total budget/revenue, avg ROI (affiliate + brand_ambassador only), renewal count, breakdown by tier |
| **Source files** | `data/campaign_performance.csv` + `data/existing_partners.csv` |

---

## Testing

```bash
uv run pytest tests/test_mcp_tools.py        # tools server tests
uv run pytest tests/test_data_server.py      # data server tests
```

Inspect a server interactively:

```bash
uv run mcp dev mcp_servers/gymshark_mcp_server.py
uv run mcp dev mcp_servers/data_server.py
```
