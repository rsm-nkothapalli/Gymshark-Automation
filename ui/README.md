# `ui/`

**GymsharkNexus** — internal operations console for the Gymshark AI influencer pipeline.

Built with plain HTML/JS + CSS served by FastAPI. No build step required.

---

## Structure

```
ui/
├── frontend/               ← Single-page app (plain HTML/JS/CSS)
│   ├── index.html          ← All screens rendered client-side via JS
│   └── css/
│       ├── styles.css           ← Design tokens, base reset
│       ├── styles-layout.css    ← Sidebar, topbar, shell
│       ├── styles-pages.css     ← Page-level layout
│       ├── styles-outreach.css  ← Outreach 3-panel layout
│       └── styles-theater.css   ← Content theater (video panel)
├── api/
│   ├── __init__.py
│   └── main.py             ← FastAPI — all data endpoints, serves frontend at /
├── backend/
│   ├── main.py             ← FastAPI — richer endpoints with full skill integration
│   └── start.sh            ← Quick start: uvicorn ui.backend.main:app --port 8000
├── design-system-reference/ ← Next.js reference prototype (not production)
├── DESIGN.md               ← Design system spec (colours, typography, components)
└── README.md               ← This file
```

---

## Screens

All six screens live in `frontend/index.html` and are rendered client-side by a `render()` dispatch function. Navigation is handled by `nav(page)`.

| Screen | `page` key | Description |
|--------|-----------|-------------|
| **Scoring** | `scoring` | Creator shortlist table — AI scores, brand safety, deal type, outreach flag |
| **Creator Profile** | `profile` | Full profile: GFS score, sentiment breakdown, RAG match, brand-fit analysis, YouTube video theater |
| **Outreach War Room** | `outreach` | 3-panel: creator queue · data dossier · email composer with LLM-generated draft + RAG sources |
| **Product Brief** | `brief` | AI-generated product brief for the selected creator |
| **Analytics** | `analytics` | Campaign performance: revenue, ROI by tier, deal type breakdown, top-performer table |
| **Leaderboard** | `leaderboard` | Ranked existing partners by ROI with renewal recommendations |

---

## How it connects to the pipeline

| Frontend call | Backend endpoint | Skill / data source |
|---------------|-----------------|---------------------|
| `GET /api/creators` | `api/main.py` or `backend/main.py` | `data/creators.csv` + scoring helpers |
| `POST /api/creators/:id/outreach` | `api/main.py` | `skill-03-outreach-drafting` + TritonAI LLM + RAG |
| `GET /api/creators/:id/rag-match` | `api/main.py` | `rag/retrieval.py` |
| `GET /api/evidence/:id` | `api/main.py` | `rag/retrieval.py` |
| `POST /api/creators/:id/brand-fit` | `api/main.py` | TritonAI LLM (`api-llama-4-scout`) |
| `POST /api/creators/:id/brief` | `api/main.py` | `skill-05-product-brief` |
| `GET /api/creators/:id/videos` | `api/main.py` | YouTube Data API v3 |
| `GET /api/analytics` | `api/main.py` or `backend/main.py` | `data/campaign_performance.csv` |
| `GET /api/kpis` | `backend/main.py` | Aggregated from all CSVs |

---

## Running

```bash
# Serve frontend + api (port 8001, from repo root)
uv run uvicorn ui.api.main:app --host 0.0.0.0 --port 8001 --reload

# Or richer backend only (port 8000, no frontend served)
bash ui/backend/start.sh
```

Open `http://localhost:8001` for the full app.

Requires `TRITONAI_API_KEY` in `.env` for LLM features (outreach drafts, brand-fit analysis). YouTube video features require `YOUTUBE_API_KEY`.
