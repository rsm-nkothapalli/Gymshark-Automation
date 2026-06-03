# Evidence and Source Use

The AI coworker does not just give an answer — every output is grounded
in structured data, retrieved documents, and deterministic scoring
functions. This file explains exactly what the pipeline uses and how the
user can inspect it.

---

## 1. What data does the AI use?

All structured data lives in `data/`. The pipeline reads the following
files at runtime:

| File | What it contains | Used by |
|------|-----------------|---------|
| `data/creators.csv` | 14 AI-scored creator profiles: subscribers, niche, content style, GFS score, authenticity, engagement, brand safety flag, deal type recommendation | Scoring, Outreach, Profile, Brief screens |
| `data/comment_sentiment.csv` | Per-creator YouTube comment samples labelled positive/negative/neutral, with a computed sentiment percentage and risk level | Sentiment risk scoring (skill-02) |
| `data/crm_records.csv` | Account manager assignment, pipeline stage, proposed next step, follow-up date, outreach channel | Creator Profile, activity feed |
| `data/outreach_responses.csv` | Whether each creator replied to outreach, response date, and notes. Also **written** at runtime when an operator clicks Send — `POST /api/creators/{id}/send-outreach` upserts a row with today's date | Pipeline status badges, activity feed, send-outreach action |
| `data/hypeauditor_intake_log.csv` | Third-party audience quality score, fake-follower %, fraud risk label, Instagram followers, top country | Creator Profile insights panel |
| `data/campaign_performance.csv` | Historical campaign revenue, budget, reach, promo redemptions, ROI, deal type for existing partners | Analytics and Leaderboard screens |
| `data/existing_partners.csv` | Current Gymshark roster — excluded from new discovery shortlist | Filters out already-signed creators |
| YouTube Data API v3 | Live video titles, thumbnails, view counts, publish dates for a creator's channel | Content theater in Creator Profile screen |

---

## 2. What documents does the AI use?

Ten internal policy and reference documents live in `rag/knowledge_base/`
as markdown files. They are chunked by `##` section heading, embedded
with `api-tgpt-embeddings` (TritonAI), and stored in
`rag/index/embedding_index.json`. At query time, the top-k chunks by
cosine similarity are injected into the LLM prompt as grounding context.

| File | Title | What it represents |
|------|-------|--------------------|
| `brand-guidelines.md` | Gymshark Brand Voice & Guidelines | Tone rules, banned phrases, writing style for all creator-facing copy |
| `outreach-playbook.md` | Creator Outreach Playbook | Step-by-step outreach process, warm/professional tone guides, follow-up cadence |
| `creator-tier-guide.md` | Creator Tier Guide & GFS Thresholds | What nano/micro/mid/macro/mega means, minimum GFS score per tier |
| `deal-types.md` | Gymshark Creator Deal Types | Gift seeding vs affiliate vs ambassador vs core athlete — terms and eligibility |
| `affiliate-commission-structure.md` | Affiliate Commission Structure & Tracking Setup | Commission rates, promo code format, UTM tracking requirements |
| `audience-safety-policy.md` | Audience Safety & Brand Risk Policy | GREEN/AMBER/RED flag criteria, what triggers human review, escalation path |
| `campaign-benchmarks.md` | Campaign Performance Benchmarks | Expected ROI, CTR, and redemption rates by tier — used to validate projections |
| `competitor-policy.md` | Competitor & Conflict of Interest Policy | Brands creators must not be affiliated with (Lululemon, Nike, etc.) |
| `content-brief-standards.md` | Creative Content Brief Standards | Mandatory elements in every brief: key message, must-include, avoid list |
| `product-catalog.md` | Gymshark Product Lines Catalog | Current product lines, target audience per line, recommended pairings by niche |

---

## 3. What tools or Python functions does the AI use?

### Skill helpers (deterministic — no LLM)

| Function | File | What it does |
|----------|------|-------------|
| `shortlist_creators()` | `skills/skill-01-creator-scoring/scoring_helpers.py` | Loads `creators.csv`, applies GFS threshold and disqualification rules, returns eligible/ineligible split |
| `is_disqualified()` | same | Returns `(True, reason)` if creator is RED brand safety, below tier floor, or already a partner |
| `calculate_sentiment_metrics()` | `skills/skill-02-sentiment-risk/sentiment_helpers.py` | Computes positive %, negative %, neutral % from raw comment rows |
| `assign_risk_level()` | same | Assigns LOW / MEDIUM / HIGH / UNKNOWN purely from `flagged_pct` thresholds (< 8% → LOW, 8–15% → MEDIUM, > 15% → HIGH, < 50 comments → UNKNOWN). The VADER compound score is not used in risk assignment. |
| `load_creator_context()` | `skills/skill-03-outreach-drafting/outreach_helpers.py` | Joins creator row with CRM record into a single context dict for prompt building |
| `build_outreach_prompt()` | same | Builds the full LLM prompt, embedding RAG chunks and tone guide |
| `check_banned_phrases()` | same | Scans a draft for prohibited words before sending |
| `validate_message()` | same | Checks word count and required elements against tier standards |
| `generate_full_brief()` | `skills/skill-05-product-brief/brief_helpers.py` | Selects product line from catalog by niche, assembles brief with key message and content format |

### RAG functions

| Function | File | What it does |
|----------|------|-------------|
| `retrieve(query, top_k)` | `rag/retrieval.py` | Embeds query, computes cosine similarity against index, returns top-k chunks with scores |
| `build_index()` | same | Chunks all KB markdown files, embeds them, writes `rag/index/embedding_index.json` |

### MCP tools (`mcp_servers/gymshark_mcp_server.py`)

| Tool | What it does |
|------|-------------|
| `score_creators()` | Runs the full scoring pipeline and returns a formatted shortlist table |
| `check_creator_risk(creator_id)` | Returns risk level, sentiment metrics, and flagged comment examples for one creator |
| `draft_outreach_message(creator_id)` | Loads context, retrieves RAG chunks, calls LLM, validates draft, returns result |

### MCP resources (`mcp_servers/data_server.py`)

| Resource URI | What it exposes |
|-------------|----------------|
| `creators://all` | Full creators CSV as structured text |
| `creators://{creator_id}` | Single creator row |
| `campaigns://summary` | Aggregated campaign performance stats |

---

## 4. How does the user see the evidence?

Evidence is surfaced in three places in the UI (`ui/frontend/index.html`):

**RAG Evidence screen** (sidebar nav → "Evidence")

The dedicated evidence screen shows:
- An explainer panel describing the three RAG steps: Retrieve → Rank → Ground
- A list of all 10 knowledge base documents that were searched
- The exact query that was run (e.g. `"yoga micro gift_seeding brand guidelines outreach"`)
- Up to 5 retrieved chunks, each displayed as a card containing:
  - Document title and section heading
  - A relevance score (cosine similarity, 0–1) shown as both a number and a colour-coded progress bar: lime (strong match, score > 0.30), amber (moderate, 0.15–0.30), grey (weak, < 0.15)
  - The verbatim text passage that was injected into the LLM prompt, shown in a bordered quote block with a left accent bar coloured by score

The user can re-fetch evidence for any selected creator by clicking "Fetch Evidence", which calls `GET /api/evidence/{creator_id}`.

**Outreach War Room screen** (sidebar nav → "Outreach")

After generating a draft, the panel below the email composer shows:
- The RAG sources that grounded the draft — document title and section for each chunk
- A "LLM Generated" or "Template Draft" tag so the user knows whether the text came from the model or a static fallback

**Creator Profile screen** (sidebar nav → "Profile")

- A "RAG Match" line shows which product line or guideline section most closely matches this creator's niche
- The score and snippet are shown inline so the user can judge relevance without leaving the profile

---

## 5. What happens if the evidence is missing, weak, or conflicting?

| Situation | What happens |
|-----------|-------------|
| **RAG index not built** (`rag/index/embedding_index.json` missing) | `retrieve()` calls `build_index()` automatically on first use. If the embedding API is unreachable, the function returns `[]` and the outreach endpoint proceeds with no RAG context — the LLM still generates a draft but the sources list in the UI is empty, signalling to the user that no documents were used. |
| **Low relevance scores** (all chunks below ~0.15) | The relevance bars render in grey rather than lime, visually flagging a weak match. The user can see the scores and decide whether to trust the draft. |
| **No chunks returned** | The evidence panel displays "No evidence retrieved yet — click Fetch Evidence above." The outreach draft still generates using an inline fallback template in the `except` block of `generate_outreach()`, labelled "Template Draft" in the UI so the user knows the LLM was not involved. |
| **Brand safety flag (AMBER/RED)** | `is_disqualified()` in scoring catches RED creators before they reach outreach. AMBER creators are passed through but the queue badge turns amber and status is set to `"review"`, prompting a human to inspect before sending. |
| **Banned phrase detected** | `check_banned_phrases()` scans the draft before returning it. If a violation is found, a warning is appended to the draft text so the operator sees it in the composer before editing or sending. |
| **LLM API unavailable** | The outreach endpoint catches all LLM exceptions and falls back to an inline template. The UI labels the result "Template Draft" and still shows any RAG sources that were retrieved, so the user knows the output was not AI-generated. |
