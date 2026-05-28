# Gymshark Influencer Marketing Pipeline — Group 18

An end-to-end AI-assisted influencer marketing pipeline that discovers YouTube fitness creators, scores them for brand fit, checks audience safety, drafts outreach messages, generates product briefs for accepted creators, and evaluates campaign performance.

---

## Setup

```bash
uv sync                        # install deps into .venv
cp .env.example .env           # add TRITONAI_API_KEY
```

Run the full test suite:

```bash
uv run pytest
```

---

## Workflow overview

| Phase | Step | Skill | Trigger |
|-------|------|-------|---------|
| 0 | Data setup | Scripts in `data/` | Once, before pipeline starts |
| 1 | Creator scoring | Skill 01 | Monthly |
| 1b | Sentiment & brand risk | Skill 02 | Per shortlisted creator |
| 2 | Outreach drafting | Skill 03 | Per approved creator |
| 3 | Product brief | Skill 05 | Creator says yes to outreach |
| 6 | Campaign analytics | Skill 04 | After campaigns complete |

The full pipeline (Skills 01 → 02 → 03 → 05) is orchestrated by **Skill 06** (`skills/skill-06-pipeline-workflow/pipeline_helpers.py`).

### Run the pipeline interactively

```bash
uv run python scripts/orchestrator.py --mode interactive
```

### Run in automated mode (uses simulated outreach responses)

```bash
uv run python scripts/orchestrator.py --mode automated
```

---

## Skills

| Skill | Folder | What it does |
|-------|--------|-------------|
| 01 — Creator Scoring | `skills/skill-01-creator-scoring/` | Reads `creators.csv`, applies tier GFS thresholds and hard disqualifiers, returns ranked shortlist |
| 02 — Sentiment & Brand Risk | `skills/skill-02-sentiment-risk/` | VADER sentiment on YouTube comments → LOW / MEDIUM / HIGH / UNKNOWN risk label |
| 03 — Outreach Drafting | `skills/skill-03-outreach-drafting/` | LLM-drafted personalized outreach messages per creator using tier-appropriate tone |
| 04 — Campaign Analytics | `skills/skill-04-campaign-analytics/` | ROI, conversion rate, cost-per-click analytics on `campaign_performance.csv` |
| 05 — Product Brief | `skills/skill-05-product-brief/` | LLM-generated product brief + promo code for creators who accepted outreach |
| 06 — Pipeline Workflow | `skills/skill-06-pipeline-workflow/` | Orchestrates Skills 01→02→03→05 with four human review gates |

---

## MCP Tools

Two MCP servers are registered in `.mcp.json`:

### gymshark-tools (`mcp_servers/gymshark_mcp_server.py`)

| Tool | What it does |
|------|-------------|
| `score_creators` | Score and shortlist all creators from `data/creators.csv` |
| `check_creator_risk` | Run sentiment risk analysis for a specific `creator_id` |
| `draft_outreach_message` | Draft a personalized outreach message for an approved creator |

### gymshark-data (`mcp_servers/data_server.py`)

| Resource | URI | What it returns |
|----------|-----|----------------|
| All creators | `creators://all` | Full `creators.csv` as JSON |
| Single creator | `creators://{creator_id}` | One creator's profile |
| Campaign summary | `campaigns://summary` | Portfolio-level campaign metrics |

---

## RAG

Knowledge base in `rag/knowledge_base/` contains Gymshark brand and partnership documents. Retrieval via `rag/retrieval.py` (`retrieve(query, top_k)`).

---

## Data files

| File | Description |
|------|-------------|
| `data/creators.csv` | 8 YouTube fitness prospects — scores, tiers, brand safety flags |
| `data/comment_sentiment.csv` | VADER-scored YouTube comments per creator |
| `data/crm_records.csv` | CRM prospect pipeline records |
| `data/existing_partners.csv` | 9 existing Gymshark partners |
| `data/campaign_performance.csv` | Synthetic campaign results for existing partners |
| `data/outreach_responses.csv` | Simulated yes/no creator responses to outreach |

---

## Tests

```bash
uv run pytest                        # all tests
uv run pytest tests/skills/          # skill tests only
uv run pytest -k pipeline            # pipeline orchestration tests
```

Total: **50+ tests** across all skills and pipeline helpers.

---

## Folder map

| Folder | Contents |
|--------|---------|
| `skills/` | One subfolder per skill — `SKILL.md` + `*_helpers.py` |
| `mcp_servers/` | Two FastMCP servers (tools + data resources) |
| `rag/` | Knowledge base documents + `retrieval.py` |
| `scripts/` | `orchestrator.py` entry point |
| `utils/` | `connect.py` — shared LLM client (`ask`, `ask_json`) |
| `data/` | CSV data files + generation scripts |
| `tests/` | pytest suite mirroring source layout |
