# Project Overview

## Goal

Build an AI-powered influencer discovery and outreach pipeline for Gymshark. The system automatically discovers YouTube fitness creators, scores them for brand fit and brand safety, drafts personalised outreach emails, and generates product briefs — replacing a manual research-and-email workflow with a human-in-the-loop AI coworker.

## Architecture

- **Plain HTML/JS/CSS frontend** — single-page app in `ui/frontend/index.html`, no build step
- **FastAPI backend** — `ui/api/main.py` serves the frontend at `/` and exposes all API endpoints
- **TritonAI LLM** — `api-llama-4-scout` (default) via OpenAI-compatible endpoint for outreach drafts, brand-fit analysis, and product briefs
- **RAG retrieval** — 10 Gymshark policy docs embedded with `api-tgpt-embeddings`, cosine similarity search, index cached to `rag/index/embedding_index.json`
- **Static CSVs as the data layer** — `data/creators.csv`, `data/comment_sentiment.csv`, `data/crm_records.csv`, `data/outreach_responses.csv`, `data/campaign_performance.csv`

## Creator Discovery Pipeline

**Script:** `data/collect_creators_gemin_2i.py`
**Re-scorer:** `data/rescore_creators.py` — re-scores existing CSV rows with LLM without re-discovering
**Auth setup:** `data/auth_youtube_oauth.py` — one-time OAuth setup for transcript access

### Pipeline config (current)
| Setting | Value | Effect |
|---|---|---|
| `RESULTS_PER_QUERY` | 25 | Up to 25 results per search query |
| `VIDEOS_PER_CREATOR` | 4 | 4 videos analyzed per creator |
| `TITLES_TO_SCAN` | 30 | 30 recent titles fetched for pre-filter |
| `MIN_BRAND_FIT_SCORE` | 5 | GFS threshold for outreach recommendation |
| `MIN_AUTHENTICITY_SCORE` | 5 | Authenticity threshold |

### Search queries (40 total)
- 10 Gymshark-specific organic mention queries
- 5 hashtag searches (`#GymsharkChallenge`, `#66DayChallenge`, `#TransformationJourney`, `#GymVlog`, `#FitnessVlog`)
- 10 broader activewear/honest-review queries
- 10 gym-lifestyle/training vlog queries (find gym-goers not yet associated with Gymshark)

### Quota usage per run (with playlistItems fix)
- `search().list()`: 100 units × 40 queries = 4,000 units
- `playlistItems().list()`: 1 unit × ~350 unique channels = 350 units
- `commentThreads().list()`: ~840 units
- **Total: ~5,190 / 10,000 daily quota** — fits in one day

### Transcript access
- **Cloud server (this environment):** YouTube blocks transcript API requests from cloud IPs. Scored from titles + comments only.
- **Local machine:** `youtube-transcript-api` works on residential/university IPs. Run `data/collect_creators_gemin_2i.py` locally for transcript-enriched scoring.
- **OAuth method (Option 2):** Use `captions.download` via OAuth 2.0 to bypass IP block:
  1. Download `client_secrets.json` from Google Cloud Console → OAuth 2.0 Client ID (Desktop app)
  2. Place in project root
  3. Run `uv run python data/auth_youtube_oauth.py` once — saves `token.json`
  4. Pipeline auto-uses `token.json` via `_fetch_transcript_oauth()` in `fetch_transcript()`
  - `captions.list` works with API key only; `captions.download` requires OAuth (`401` otherwise)

### Pipeline funnel (test run 2026-06-03 — results NOT in active CSV)
- 531 unique channels discovered → pre-filter → 177 candidates scored → 68 recommended
- Transcripts blocked (cloud IP — YouTube blocks all transcript API calls from cloud provider IPs)
- Results reverted; active CSV restored to original 14 creators pending quota reset + OAuth setup

### When YouTube API quota resets — recommended next steps
1. Set up OAuth for transcript access: `uv run python data/auth_youtube_oauth.py` (needs `client_secrets.json` from Google Cloud Console)
2. Re-run pipeline: `uv run python data/collect_creators_gemin_2i.py` — checkpoint-safe, resumes if interrupted
3. Optionally run `data/rescore_creators.py` to re-score only existing creators without full re-discovery

## Important Decisions

- **Skills 01 and 02 are fully deterministic at runtime** — scores were computed once by LLM during data collection and frozen in CSVs; no LLM is called for scoring or risk classification
- **Skill-02 risk is purely flagged_pct-based** — removed the VADER `low_sentiment_floor: 0.65` gate because VADER misscores fitness slang ("brutal", "destroying") as negative; risk is now `< 8% → LOW`, `8–15% → MEDIUM`, `> 15% → HIGH`, `< 50 comments → UNKNOWN`
- **LLM is called live only for** outreach drafts (`skill-03`), brand-fit analysis, and product briefs (`skill-05`)
- **Single backend** — `ui/api/main.py` is the sole server; `ui/backend/main.py` was deleted during consolidation
- **Send Outreach persists** — `POST /api/creators/{id}/send-outreach` upserts a row in `data/outreach_responses.csv`; approve/reject are browser-only state
- **Default role is `manager`** — `state.userRole` defaults to `'manager'`; the landing page lets the user choose Analyst or Manager on every entry. Role can also be switched mid-session via the popup triggered by the bottom sidebar badge. The sidebar G button always returns to the landing page for re-selection.

## Current State

- **Landing page** added as a full-screen fixed overlay (`#landing`, `z-index:1000`). Shown on first load; user selects Analyst or Manager to enter the app. Clicking the sidebar G button returns to it at any time.
- All **5 UI screens** working: Scoring, Creator Profile, Outreach War Room, Product Brief, Analytics. Leaderboard tab has been removed.
- Backend serves frontend at `/` and all API endpoints at `/api/`
- Server runs at port 8001: `uv run uvicorn ui.api.main:app --host 0.0.0.0 --port 8001 --reload`
- 253 unit tests passing, 0 failing; MCP tests skip gracefully when `mcp` package absent
- DeepEval AI performance test suite complete (`tests/test_ai_performance.py`) — 10 cases, 8/10 passing
- `failure_cases.md` and `test_report.md` complete for Section 6 of the milestone
- UI fully restyled at **22px base font** with all panels, sidebar, topbar, and layout boxes scaled proportionally (Gymshark Nexus dark-neon theme preserved)
- **Creator dataset** — `data/creators.csv` restored to the **original 14 creators** (`rule-based titles + comment analysis` scoring, committed state). This is the active production dataset. SpeedUniverse has been identified as irrelevant but remains in the committed CSV — remove before next demo if needed.
- **Shortlist board** has tier filter pills + 15-per-page pagination + HIGH risk auto-filter (toggle available for managers)
- **Two additional UI screens added:** AI Action Log (clock icon, session event timeline) and Flags & Errors (triangle icon, triage view of RED/HIGH/UNKNOWN risk and low-GFS creators)

## UI Styling — Final State (as of 2026-06-03, updated session 4)

### Font Scale
Base font: **22px** (`html, body` in `ui/frontend/css/styles.css`). All other sizes are explicitly set in px across the 5 CSS files — they do NOT use rem/em. Key sizes:
- Panel titles / labels / chips: 15–17px (uppercase, JetBrains Mono)
- Body / value text: 17–20px
- Creator names / handles: 18–20px
- GFS scores / KPI values: 24–39px
- Big scoring number: 78px

### Layout Box Sizes
- `.app` sidebar column: `60px 1fr`
- `.topbar` height: `60px`
- `.workspace` columns: `340px 1fr 370px`
- `.avatar` (creator card): `48×48px`
- `.avatar-sm` (topbar): `32×32px`
- `.sb-btn`: `44×44px`, `.sb-logo`: `37×37px`

### Score Bars
Two bar rendering systems exist:

1. **CSS-class bars** (`.eng-row / .eng-bar / .eng-bar-fill`) — used in the Media Theater panel (panel 02). `.eng-label` has `min-width:130px; flex-shrink:0; white-space:nowrap; font-size:14px; font-family:'JetBrains Mono'` to prevent label clipping. `.eng-bar` has `min-width:0` to allow compression.

2. **Gradient bars** (inline style only) — used in the Scoring right panel and Creator Detail panel (panel 03). Uses:
   ```css
   background: linear-gradient(to right, var(--neon) X%, #232323 X%)
   ```
   Label divs have `min-width:130px; flex-shrink:0; white-space:nowrap` to prevent clipping. Bar track divs have `min-width:0`. Score values shown as `val/10` right of the track.

### Outreach Panel (Personalized Email Draft screen)
The outreach page (`state.currentPage === 'outreach'`) renders as a **standalone full-width page** — the topbar and content div are injected directly as flex children of the outer `.main` element (no inner `height:100vh` wrapper). This ensures the `.outreach` scroll container gets a definite height from the flex chain and scrolls correctly.

Key layout details:
- `.outreach` CSS: `flex:1; min-height:0; overflow-y:auto` — fills the panel and scrolls
- `.panel` in `renderOutreachPanel()` has inline `style="flex:1;min-height:0"` — fills content area
- Textarea (`.email-body`) uses `height:auto; min-height:220px; overflow:hidden` — auto-expands via `autoResizeDraft(ta)` called after every render and on `oninput`
- Email field grid: `grid-template-columns: 80px 1fr` — prevents TO/SUBJECT/DEAL label overlap
- All text uses `font-family:'JetBrains Mono',monospace` throughout (labels, values, buttons, tone pills, ai-meta)
- Red "⚠ Outreach not recommended" banner has been **removed**
- Status banners (amber/green) appear near the top of the panel (below out-meta) for pending/approved/sent states, visible without scrolling

### Outreach Button Flow (role-aware state machine)
The `out-footer` section is driven by a single IIFE that owns all button rendering. Logic:

**Analyst role (`state.userRole === 'analyst'`):**
- No draft → Generate button only
- Draft ready (`status=null`) → Generate + Copy row · full-width neon "SUBMIT FOR APPROVAL" button
- Submitted (`status=pending`) → Generate + Copy row (dimmed, `opacity:0.4; pointer-events:none`) · muted "⏳ AWAITING APPROVAL — Waiting for a manager to approve" bar

**Manager/Director role:**
- No draft → Generate button only
- Draft ready (`status=null` or `pending`) → Generate + Copy row · muted "⏳ AWAITING APPROVAL — Review the draft…" bar · Reject (red outline) + Approve (green outline) buttons side-by-side
- After Approve (`status=approved`) → Generate + Copy row · green "✓ Approved — ready to send" bar · neon "SEND OUTREACH & SYNC CRM" button
- After Reject → resets `status=null` (back to initial)

**Shared terminal states:**
- `sending` — all buttons dimmed + spinner bar
- `sent` — success confirmation with creator name + Generate button (to re-draft)

### Product Brief Panel
"How it works" right-hand card: body text bumped from `12px` to `17px` with `font-family:'JetBrains Mono'`; green code block (product lines) bumped from `11px` to `16px` with `color:var(--neon)`.

### CSS Files
All 6 files under `ui/frontend/css/`:
- `styles.css` — base, sidebar, topbar, toast. `.sb-logo` is a `<button>` with `cursor:pointer` and hover opacity; clicking it calls `returnToLanding()`.
- `styles-layout.css` — workspace panels, creator cards, avatars
- `styles-pages.css` — KPIs, tables, brief, scoring (`.factor-bar` uses `flex:1; min-width:60px`)
- `styles-theater.css` — video, stats, engagement bars (`.eng-label` fixed for label clipping; `.eng-bar` has `min-width:0`)
- `styles-outreach.css` — email compose panel (font sizes, grid layout, textarea auto-expand, tone pills, buttons)
- `styles-landing.css` — landing overlay only. Full-screen fixed overlay with scanlines (`::before` repeating gradient), edge vignette (`::after`), hero title, description, profile label with blinking cursor, two operator cards with hover lift + top lime accent bar, bottom metadata strip. All non-hero text at **22px**. Cards stack vertically on screens ≤900px.

### Landing Page — Key Implementation Details
- HTML: `<div id="landing" class="landing-overlay">` placed before `<div id="root">` in `index.html`
- `selectOperator(role)` — sets `state.userRole`, adds `.hidden` to `#landing`, calls `updateRoleBadge()` + `render()`
- `returnToLanding()` — removes `.hidden` from `#landing`; overlay covers the full app shell (z-index 1000), no shell manipulation needed
- `updateRoleBadge()` — writes `ANALYST` or `MANAGER` to `#profile-avatar` (the bottom sidebar badge); called on operator select, role switch via popup, and page init
- Bottom sidebar role badge: inline-styled `<div id="profile-avatar">` replacing the old lime "N" circle — JetBrains Mono 8px, uppercase, lime background, black text, pill shape, max-width 52px
- Default `state.userRole` is still `'manager'`; badge initialises to `MANAGER` on page load

## Next Tasks

1. Address the two failing DeepEval cases:
   - `outreach-01`: replace literal banned-phrase blacklist with a principle-based tone instruction
   - `brand-fit-02`: add conditional hard rule — HIGH risk must end with "Recommendation: Do not proceed without human review"
2. Extend DeepEval suite to cover product brief generation (Skill-05 — currently untested)
3. Run the full integration test suite against any future skill or prompt changes

## Known Issues

- `brand-fit-02-high-risk` DeepEval test fails (score 0.30) — brand-fit analysis for HIGH-risk creators softens the language instead of giving a clear hold/escalate directive
- `outreach-01-nano-yoga` DeepEval test fails (score 0.40) — LLM avoids the literal banned phrases but still opens with sycophantic language ("We really enjoy your…")
- `negative_creator_flag` in `comment_sentiment.csv` still relies on VADER compound ≤ 0.0 at data-collection time (`collect_comments.py`) — VADER is indirectly present even though it no longer affects risk scoring
- 4 creators have fewer than 50 comments and resolve to UNKNOWN risk — human decides individually
- CSS-class bars (`.eng-bar-fill { width:X% }`) inside a `flex:1` (flex-basis:0) parent can render as 0-width in some browsers. Only affects panel 02 theater bars — those happen to be wide enough that the invisible fill is less noticeable. Panel 03 bars were migrated to gradient-based rendering to fix this definitively.
