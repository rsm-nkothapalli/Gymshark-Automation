"""
Gymshark Nexus — unified FastAPI backend.
Single instance: serves the frontend, enforces the full skill pipeline,
and exposes every endpoint the UI uses.

Skill integration:
  Skill 01 — shortlist_creators()   filters /api/creators through tier thresholds
  Skill 02 — sentiment_mod          adds live risk_level to every creator
  Skill 03 — outreach_helpers       drives /api/creators/{id}/outreach
  Skill 05 — brief_helpers          drives /api/creators/{id}/brief

Start (from repo root):
    uv run uvicorn ui.api.main:app --host 0.0.0.0 --port 8001 --reload
"""

import csv
import importlib.util
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = Path(__file__).parent.parent.parent
DATA_DIR = ROOT / "data"
sys.path.insert(0, str(ROOT))


# ── skill modules ─────────────────────────────────────────────────────────────


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_skill(folder: str, module_file: str):
    return _load_module(module_file[:-3], ROOT / "skills" / folder / module_file)


scoring = _load_module(
    "scoring_helpers",
    ROOT / "skills/skill-01-creator-scoring/scoring_helpers.py",
)
sentiment_mod = _load_module(
    "sentiment_helpers",
    ROOT / "skills/skill-02-sentiment-risk/sentiment_helpers.py",
)


# ── app ───────────────────────────────────────────────────────────────────────

app = FastAPI(title="Gymshark Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── helpers ───────────────────────────────────────────────────────────────────


def _read_csv(rel: str) -> list[dict]:
    p = ROOT / rel
    if not p.exists():
        return []
    with open(p, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _fmt_subs(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K"
    return str(n)


def _gfs_tier(score: float) -> str:
    if score >= 7.0:
        return "high"
    if score >= 5.5:
        return "mid"
    return "low"


# ── in-memory caches (reset on restart, fine for demo) ────────────────────────

_SENTIMENT_CACHE: dict | None = None
_CRM_CACHE: dict | None = None
_HYPEAUDITOR_CACHE: dict | None = None
_OUTREACH_CACHE: dict | None = None


def _get_sentiment_map() -> dict:
    global _SENTIMENT_CACHE
    if _SENTIMENT_CACHE is not None:
        return _SENTIMENT_CACHE
    path = DATA_DIR / "comment_sentiment.csv"
    if not path.exists():
        _SENTIMENT_CACHE = {}
        return _SENTIMENT_CACHE
    rows = sentiment_mod.load_all_sentiment(str(path))
    by_creator: dict[str, list] = {}
    for row in rows:
        by_creator.setdefault(row.get("creator_id", ""), []).append(row)
    result = {}
    for cid, crows in by_creator.items():
        metrics = sentiment_mod.calculate_sentiment_metrics(crows)
        risk_level, emoji, reason = sentiment_mod.assign_risk_level(metrics)
        result[cid] = {
            "metrics": metrics or {},
            "risk_level": risk_level,
            "emoji": emoji,
            "reason": reason,
        }
    _SENTIMENT_CACHE = result
    return result


def _get_crm() -> dict:
    global _CRM_CACHE
    if _CRM_CACHE is None:
        path = DATA_DIR / "crm_records.csv"
        _CRM_CACHE = {}
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                _CRM_CACHE = {r["creator_id"]: r for r in csv.DictReader(f)}
    return _CRM_CACHE


def _get_hypeauditor() -> dict:
    global _HYPEAUDITOR_CACHE
    if _HYPEAUDITOR_CACHE is None:
        path = DATA_DIR / "hypeauditor_intake_log.csv"
        _HYPEAUDITOR_CACHE = {}
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                _HYPEAUDITOR_CACHE = {r["creator_id"]: r for r in csv.DictReader(f)}
    return _HYPEAUDITOR_CACHE


def _get_outreach_responses() -> dict:
    global _OUTREACH_CACHE
    if _OUTREACH_CACHE is None:
        path = DATA_DIR / "outreach_responses.csv"
        _OUTREACH_CACHE = {}
        if path.exists():
            with open(path, newline="", encoding="utf-8") as f:
                _OUTREACH_CACHE = {r["creator_id"]: r for r in csv.DictReader(f)}
    return _OUTREACH_CACHE


def _load_campaigns() -> list[dict]:
    path = DATA_DIR / "campaign_performance.csv"
    if not path.exists():
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ── creator serializer ────────────────────────────────────────────────────────


def _serialize_creator(raw: dict) -> dict:
    """
    Build the creator object the frontend expects.
    All field names are preserved from the original api/main.py contract.
    Skill-02 live sentiment enriches risk_level and sentiment_reason.
    """
    cid = raw.get("creator_id", "")
    s = _get_sentiment_map().get(cid, {})
    m = s.get("metrics", {}) or {}

    try:
        gfs = float(raw.get("gymshark_brand_fit") or 0)
    except (ValueError, TypeError):
        gfs = 0.0
    try:
        subs = int(raw.get("subscribers") or 0)
    except (ValueError, TypeError):
        subs = 0

    niche = raw.get("niche", "")
    content_style = raw.get("content_style", "")

    return {
        # ── identity ──────────────────────────────────────────────────────
        "id": cid,
        "name": raw.get("name", ""),
        "handle": raw.get("youtube_handle", ""),
        "tier": raw.get("tier", ""),
        "niche": niche,
        "content_style": content_style,
        "country": raw.get("country", ""),
        "tags": [t for t in [niche, content_style] if t],
        # ── reach ─────────────────────────────────────────────────────────
        "subscribers": subs,
        "subscribers_fmt": _fmt_subs(subs),  # frontend reads c.subscribers_fmt
        # ── GFS ───────────────────────────────────────────────────────────
        "gfs": round(gfs, 1),
        "gfs_tier": _gfs_tier(gfs),
        # ── deal ──────────────────────────────────────────────────────────
        "deal_type": raw.get("suggested_deal_type", ""),
        "outreach_recommended": bool(raw.get("outreach_recommended", False)),
        # ── safety ────────────────────────────────────────────────────────
        "brand_safety": raw.get("brand_safety", "GREEN"),
        "audience_brand_risk": raw.get("audience_brand_risk", "UNKNOWN"),
        # ── scores (strings — frontend renders directly) ───────────────────
        "authenticity_score": raw.get("authenticity_score", ""),
        "niche_score": raw.get("niche_score", ""),
        "engagement_score": raw.get("engagement_score", ""),
        "brand_fit_reasoning": raw.get("brand_fit_reasoning", ""),
        "comment_sentiment_score": raw.get("comment_sentiment_score", ""),
        # ── skill-02 live enrichment (additive — does not replace above) ───
        "risk_level": s.get("risk_level", "UNKNOWN"),
        "sentiment_reason": s.get("reason", ""),
        "sentiment_positive_pct": round(m.get("positive_pct", 0), 1),
    }


# ── creators ──────────────────────────────────────────────────────────────────


@app.get("/api/creators")
def get_creators():
    """Skill-01 filtered shortlist — applies tier thresholds and hard disqualifiers."""
    eligible, _ = scoring.shortlist_creators(str(DATA_DIR / "creators.csv"))
    return [_serialize_creator(c) for c in eligible]


@app.get("/api/creators/{creator_id}")
def get_creator(creator_id: str):
    all_creators = scoring.load_creators(str(DATA_DIR / "creators.csv"))
    raw = next((c for c in all_creators if c.get("creator_id") == creator_id), None)
    if not raw:
        raise HTTPException(status_code=404, detail="Creator not found")
    return _serialize_creator(raw)


# ── outreach ──────────────────────────────────────────────────────────────────


class OutreachRequest(BaseModel):
    tone: str = "warm"
    deal_type: str = ""
    tier: str = ""


def _fallback_outreach_draft(
    creator: dict, *, tone: str = "warm", deal_type: str = ""
) -> str:
    first = creator.get("name", "Creator").split()[0]
    niche = creator.get("niche", "fitness")
    deal_label = deal_type or creator.get("deal_type", "gift_seeding")
    greeting = "Hi" if first else "Hello"
    if tone.lower() == "concise":
        return (
            f"{greeting} {first},\n\n"
            f"I’ve been following your {niche.lower()} content and love the way you connect with your community.\n\n"
            f"We’d love to send you a few pieces from our latest drop for your review and would be grateful to hear if a quick call could be of interest.\n\n"
            f"We can shape the collaboration around {deal_label.replace('_', ' ')} and a fit that feels natural for your audience.\n\n"
            "Best,\nGymshark Partnerships"
        )
    return (
        f"{greeting} {first},\n\n"
        f"I came across your channel and loved how authentically you share your {niche.lower()} journey with your community.\n\n"
        f"We'd love to send you some pieces from our latest collection to try out — no obligations, just a gift from us to you.\n\n"
        f"This feels like a strong fit for a {deal_label.replace('_', ' ')} collaboration, and I’d be excited to explore a partnership that feels natural for your audience.\n\n"
        f"Would you be open to a quick chat?\n\nBest,\nGymshark Partnerships"
    )


def _generate_outreach_payload(creator_id: str, req: OutreachRequest):
    creator = get_creator(creator_id)
    try:
        from rag.retrieval import retrieve as rag_retrieve

        tier = req.tier or creator.get("tier", "micro")
        deal = req.deal_type or creator.get("deal_type", "")
        niche = creator.get("niche", "")
        rag_query = (
            f"outreach tone {tier} creator {niche} {deal} banned phrases guidelines"
        )
        rag_sources = rag_retrieve(rag_query, top_k=3)
    except Exception:
        rag_sources = []

    tier = req.tier or creator.get("tier", "micro")
    deal = req.deal_type or creator.get("deal_type", "")
    niche = creator.get("niche", "")

    try:
        oh = _load_skill("skill-03-outreach-drafting", "outreach_helpers.py")
        from utils.connect import ask

        ctx = oh.load_creator_context(
            creator_id,
            creators_path=str(DATA_DIR / "creators.csv"),
            crm_path=str(DATA_DIR / "crm_records.csv"),
        )
        if ctx is None:
            raise HTTPException(status_code=404, detail="Creator not found in CRM")
        if req.deal_type:
            ctx["suggested_deal_type"] = req.deal_type

        draft = ask(
            oh.build_outreach_prompt(ctx, tone_override=req.tone),
            model="api-llama-4-scout",
        )
        return {
            "draft": draft,
            "word_count": len(draft.split()),
            "tier": tier,
            "label": "AI Draft",
            "type": deal or "gift_seeding",
            "llm_generated": True,
            "creator": ctx,
            "rag_sources": rag_sources,
        }
    except Exception:
        draft = _fallback_outreach_draft(creator, tone=req.tone, deal_type=deal)
        return {
            "draft": draft,
            "word_count": len(draft.split()),
            "tier": tier,
            "label": "Fallback Draft",
            "type": deal or "gift_seeding",
            "llm_generated": False,
            "creator": creator,
            "rag_sources": rag_sources,
        }


@app.post("/api/creators/{creator_id}/outreach")
def generate_outreach(creator_id: str, req: OutreachRequest):
    return _generate_outreach_payload(creator_id, req)


@app.post("/api/creators/{creator_id}/draft")
def generate_draft(creator_id: str, req: OutreachRequest):
    payload = _generate_outreach_payload(creator_id, req)
    return {
        "draft": payload["draft"],
        "word_count": payload["word_count"],
        "tier": payload["tier"],
        "label": payload["label"],
        "type": payload["type"],
        "llm_generated": payload["llm_generated"],
    }


# ── send outreach (persist to outreach_responses.csv) ────────────────────────


class SendOutreachRequest(BaseModel):
    draft: str = ""


@app.post("/api/creators/{creator_id}/send-outreach")
def send_outreach(creator_id: str, req: SendOutreachRequest):
    """Record that outreach was sent. Writes a row to outreach_responses.csv."""
    from datetime import date

    creator = get_creator(creator_id)
    today = date.today().isoformat()
    path = DATA_DIR / "outreach_responses.csv"

    fieldnames = [
        "creator_id",
        "name",
        "tier",
        "deal_type",
        "outreach_sent_date",
        "responded_yes",
        "response_date",
        "response_notes",
    ]

    existing = {}
    if path.exists():
        with open(path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                existing[row["creator_id"]] = row

    existing[creator_id] = {
        "creator_id": creator_id,
        "name": creator["name"],
        "tier": creator["tier"],
        "deal_type": creator["deal_type"],
        "outreach_sent_date": today,
        "responded_yes": "",
        "response_date": "",
        "response_notes": "",
    }

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(existing.values())

    # Invalidate cache so activity feed and KPIs reflect the new row immediately
    global _OUTREACH_CACHE
    _OUTREACH_CACHE = None

    return {"ok": True, "creator": creator["name"], "sent_date": today}


# ── rag evidence ──────────────────────────────────────────────────────────────


@app.get("/api/evidence/{creator_id}")
def get_evidence(creator_id: str):
    creator = get_creator(creator_id)
    from rag.retrieval import retrieve as rag_retrieve

    query = f"{creator['niche']} {creator['tier']} {creator['deal_type']} brand guidelines outreach"
    chunks = rag_retrieve(query, top_k=5)
    return {
        "creator": creator["name"],
        "query": query,
        "chunks": [
            {
                "title": c["title"],
                "section": c["section"],
                "score": round(c["score"], 3),
                "snippet": c["snippet"][:300],
                "source": c.get("doc_id", ""),
            }
            for c in chunks
        ],
    }


@app.get("/api/creators/{creator_id}/rag-match")
def get_rag_match(creator_id: str):
    creator = get_creator(creator_id)
    from rag.retrieval import retrieve as rag_retrieve

    query = f"{creator.get('niche', '')} {creator.get('tier', '')} product line Gymshark partnership"
    chunks = rag_retrieve(query, top_k=2)
    if not chunks:
        return {"match": None}
    top = chunks[0]
    return {
        "match": top["title"],
        "section": top["section"],
        "score": round(top["score"], 3),
        "snippet": top["snippet"][:200],
    }


# ── brand fit analysis ────────────────────────────────────────────────────────


@app.post("/api/creators/{creator_id}/brand-fit")
def generate_brand_fit(creator_id: str):
    creator = get_creator(creator_id)
    from utils.connect import ask

    prompt = (
        "You are a Gymshark influencer marketing analyst. "
        "Write a detailed brand fit analysis for this creator prospect.\n\n"
        f"Creator: {creator['name']} ({creator['handle']})\n"
        f"Tier: {creator['tier']} | Subscribers: {creator['subscribers_fmt']}\n"
        f"Niche: {creator['niche']} | Content style: {creator['content_style']}\n"
        f"Country: {creator['country']}\n\n"
        "Scores (out of 10):\n"
        f"- Gymshark Fit Score (GFS): {creator['gfs']}\n"
        f"- Authenticity: {creator['authenticity_score']}\n"
        f"- Niche alignment: {creator['niche_score']}\n"
        f"- Engagement: {creator['engagement_score']}\n"
        f"- Comment sentiment: {creator['comment_sentiment_score']}\n"
        f"- Live risk level (skill-02): {creator['risk_level']}\n\n"
        f"Brand safety: {creator['brand_safety']}\n"
        f"Deal type: {creator['deal_type']}\n"
        f"Outreach recommended: {creator['outreach_recommended']}\n"
        f"Existing reasoning: {creator.get('brand_fit_reasoning', 'None')}\n\n"
        "Write 3–4 sentences covering: why this creator fits (or doesn't fit) "
        "the Gymshark brand, what their scores reveal about audience quality, "
        "any risks or standout strengths, and what deal type makes sense and why. "
        "Be specific and analytical, not generic."
    )
    return {"analysis": ask(prompt, model="api-llama-4-scout")}


# ── product brief ─────────────────────────────────────────────────────────────


@app.post("/api/creators/{creator_id}/brief")
def generate_brief(creator_id: str):
    try:
        bh = _load_skill("skill-05-product-brief", "brief_helpers.py")
        return {"brief": bh.generate_full_brief(creator_id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── resolve youtube handle ────────────────────────────────────────────────────


@app.post("/api/creators/{creator_id}/resolve-handle")
def resolve_handle(creator_id: str):
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key or "Paste" in api_key:
        raise HTTPException(status_code=503, detail="YOUTUBE_API_KEY not configured")

    creator = get_creator(creator_id)
    name = creator["name"]
    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=api_key)
        resp = (
            youtube.search()
            .list(q=name, part="snippet", type="channel", maxResults=5)
            .execute()
        )
        items = resp.get("items", [])
        if not items:
            return {"resolved": False, "message": "No channels found"}

        channel_ids = [i["snippet"]["channelId"] for i in items]
        ch_resp = (
            youtube.channels()
            .list(id=",".join(channel_ids), part="snippet,statistics")
            .execute()
        )

        candidates = []
        for ch in ch_resp.get("items", []):
            snip = ch["snippet"]
            candidates.append(
                {
                    "channel_id": ch["id"],
                    "title": snip.get("title", ""),
                    "handle": snip.get("customUrl", ""),
                    "subscribers": int(
                        ch.get("statistics", {}).get("subscriberCount", 0)
                    ),
                    "thumbnail": snip.get("thumbnails", {})
                    .get("default", {})
                    .get("url", ""),
                }
            )

        name_lower = name.lower().replace(" ", "")
        best = sorted(
            candidates,
            key=lambda c: (
                name_lower not in c["title"].lower().replace(" ", ""),
                -c["subscribers"],
            ),
        )[0]

        if best["handle"]:
            csv_path = DATA_DIR / "creators.csv"
            content = csv_path.read_text(encoding="utf-8")
            old = creator["handle"]
            new = (
                best["handle"]
                if best["handle"].startswith("@")
                else f"@{best['handle']}"
            )
            csv_path.write_text(
                content.replace(f",{old},", f",{new},"), encoding="utf-8"
            )

        return {
            "resolved": True,
            "candidates": candidates,
            "best": best,
            "old_handle": creator["handle"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── youtube videos ────────────────────────────────────────────────────────────


@app.get("/api/creators/{creator_id}/videos")
def get_creator_videos(creator_id: str):
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key or "Paste" in api_key:
        raise HTTPException(status_code=503, detail="YOUTUBE_API_KEY not configured")

    creator = get_creator(creator_id)
    handle = creator["handle"].lstrip("@")

    try:
        from googleapiclient.discovery import build

        youtube = build("youtube", "v3", developerKey=api_key)
        clean = "".join(c for c in handle if c.isalnum() or c in "_.")

        channel_id = None
        if clean:
            resp = youtube.channels().list(forHandle=clean, part="id,snippet").execute()
            items = resp.get("items", [])
            if items:
                channel_id = items[0]["id"]

        if not channel_id:
            return {"videos": [], "channel_id": None, "handle": clean}

        search_resp = (
            youtube.search()
            .list(
                channelId=channel_id,
                part="snippet",
                order="date",
                type="video",
                maxResults=6,
            )
            .execute()
        )
        video_ids = [i["id"]["videoId"] for i in search_resp.get("items", [])]
        snippets = {
            i["id"]["videoId"]: i["snippet"] for i in search_resp.get("items", [])
        }

        if not video_ids:
            return {"videos": [], "channel_id": channel_id}

        stats_resp = (
            youtube.videos()
            .list(part="statistics,contentDetails", id=",".join(video_ids))
            .execute()
        )
        videos = []
        for item in stats_resp.get("items", []):
            vid = item["id"]
            snip = snippets.get(vid, {})
            stats = item.get("statistics", {})
            thumb = (
                snip.get("thumbnails", {}).get("medium")
                or snip.get("thumbnails", {}).get("default")
                or {}
            ).get("url", "")
            videos.append(
                {
                    "video_id": vid,
                    "title": snip.get("title", ""),
                    "thumbnail": thumb,
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "published_at": snip.get("publishedAt", "")[:10],
                    "duration": item.get("contentDetails", {}).get("duration", ""),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                }
            )
        return {"videos": videos, "channel_id": channel_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── analytics ─────────────────────────────────────────────────────────────────


@app.get("/api/analytics")
def get_analytics():
    campaigns = _read_csv("data/campaign_performance.csv")
    partners = {r["creator_id"]: r for r in _read_csv("data/existing_partners.csv")}

    total_revenue = total_budget = total_reach = 0.0
    by_tier: dict[str, dict] = {}
    by_deal: dict[str, dict] = {}
    seen: dict[str, dict] = {}

    for c in campaigns:
        try:
            rev = float(c.get("revenue_attributed_gbp") or 0)
            budget = float(c.get("budget_gbp") or 0)
            reach = int(c.get("reach") or 0)
            roi = float(c.get("roi_x") or 0)
            clicks = int(c.get("utm_clicks") or 0)
            redemptions = int(c.get("promo_redemptions") or 0)
        except (ValueError, TypeError):
            continue

        total_revenue += rev
        total_budget += budget
        total_reach += reach
        tier = c.get("tier", "unknown")
        deal = c.get("deal_type", "unknown")

        bt = by_tier.setdefault(
            tier, {"revenue": 0, "budget": 0, "count": 0, "roi_sum": 0}
        )
        bt["revenue"] += rev
        bt["budget"] += budget
        bt["count"] += 1
        bt["roi_sum"] += roi

        bd = by_deal.setdefault(deal, {"revenue": 0, "budget": 0, "count": 0})
        bd["revenue"] += rev
        bd["budget"] += budget
        bd["count"] += 1

        cid = c.get("creator_id", "")
        p = partners.get(cid, {})
        sc = seen.setdefault(
            cid,
            {
                "id": cid,
                "name": c.get("creator_name", p.get("name", cid)),
                "handle": p.get("youtube_handle", ""),
                "tier": tier,
                "deal_type": deal,
                "niche": p.get("niche", ""),
                "revenue": 0,
                "budget": 0,
                "roi_sum": 0,
                "clicks": 0,
                "redemptions": 0,
                "count": 0,
            },
        )
        sc["revenue"] += rev
        sc["budget"] += budget
        sc["roi_sum"] += roi
        sc["clicks"] += clicks
        sc["redemptions"] += redemptions
        sc["count"] += 1

    creator_summary = []
    for sc in seen.values():
        n = sc["count"]
        creator_summary.append(
            {
                "id": sc["id"],
                "name": sc["name"],
                "handle": sc["handle"],
                "tier": sc["tier"],
                "deal_type": sc["deal_type"],
                "niche": sc["niche"],
                "revenue": round(sc["revenue"], 0),
                "budget": round(sc["budget"], 0),
                "avg_roi_x": round(sc["roi_sum"] / n, 2) if n else 0,
                "conversion_rate": round(sc["redemptions"] / sc["clicks"], 3)
                if sc["clicks"] > 0
                else None,
                "campaigns": n,
                "renewal": "Yes",
            }
        )
    creator_summary.sort(key=lambda x: x["avg_roi_x"], reverse=True)

    overall_roi = round(total_revenue / total_budget, 2) if total_budget else 0
    tier_breakdown = [
        {
            "tier": t,
            "roi_fmt": f"{round(v['roi_sum'] / v['count'], 2):.2f}x",
            "revenue_fmt": f"£{round(v['revenue'], 0):,.0f}",
            "campaigns": v["count"],
        }
        for t, v in by_tier.items()
    ]
    top_performers = []
    for item in creator_summary[:10]:
        conv = item.get("conversion_rate")
        top_performers.append(
            {
                "name": item["name"],
                "niche": item["niche"] or "General Fitness",
                "tier": item["tier"],
                "deal_type": item["deal_type"],
                "roi": item["avg_roi_x"],
                "roi_fmt": f"{item['avg_roi_x']:.2f}x",
                "revenue_fmt": f"£{item['revenue']:,.0f}",
                "conv_fmt": f"{conv * 100:.0f}%"
                if isinstance(conv, (int, float)) and conv is not None
                else "—",
                "renewal": "Yes" if item.get("renewal") == "Yes" else "No",
            }
        )

    return {
        "summary": {
            "total_revenue": f"£{round(total_revenue, 0):,.0f}",
            "overall_roi": f"{overall_roi:.2f}x",
            "total_reach": f"{int(total_reach):,}",
            "active_partners": len(seen),
            "total_campaigns": len(campaigns),
        },
        "top_performers": top_performers,
        "tier_breakdown": tier_breakdown,
    }


# ── kpis ──────────────────────────────────────────────────────────────────────


@app.get("/api/kpis")
def get_kpis():
    try:
        eligible, ineligible = scoring.shortlist_creators(
            str(DATA_DIR / "creators.csv")
        )
    except Exception:
        eligible, ineligible = [], []
    campaigns = _load_campaigns()
    roi_values = []
    for c in campaigns:
        try:
            roi_values.append(float(c.get("roi_x") or 0))
        except (ValueError, TypeError):
            pass
    outreach = _get_outreach_responses()
    responded = sum(1 for r in outreach.values() if r.get("responded_yes") == "True")
    all_creators = scoring.load_creators(str(DATA_DIR / "creators.csv"))
    return {
        "creators_discovered": len(all_creators),
        "active_outreach": len(outreach) or len(eligible),
        "avg_roi": round(sum(roi_values) / len(roi_values), 1) if roi_values else 4.2,
        "eligible_count": len(eligible),
        "ineligible_count": len(ineligible),
        "responded_count": responded,
    }


# ── activity feed ─────────────────────────────────────────────────────────────


@app.get("/api/activity")
def get_activity():
    outreach = _get_outreach_responses()
    crm = _get_crm()
    events = []

    for cid, rec in outreach.items():
        crm_rec = crm.get(cid, {})
        handle = crm_rec.get("youtube_handle", f"@{cid[:8]}")
        manager = crm_rec.get("account_manager", "System")
        if rec.get("responded_yes") == "True":
            events.append(
                {
                    "user": manager,
                    "action": "received reply from",
                    "target": handle,
                    "destination": rec.get("response_notes", "Confirmed interest")[:60],
                    "status": "live",
                    "date": rec.get("response_date", ""),
                }
            )
        else:
            events.append(
                {
                    "user": "System",
                    "action": "no reply from",
                    "target": handle,
                    "destination": "14-day window elapsed — follow-up recommended",
                    "status": "warning",
                    "date": "",
                }
            )

    for cid, rec in crm.items():
        if cid in outreach:
            continue
        events.append(
            {
                "user": "System",
                "action": "discovered",
                "target": rec.get("youtube_handle", f"@{cid[:8]}"),
                "destination": f"{rec.get('niche', 'fitness')} · GFS {rec.get('gymshark_brand_fit', '?')}",
                "status": "system",
                "date": "",
            }
        )

    return events[:8]


# ── product briefs ────────────────────────────────────────────────────────────

BRIEFS_DIR = ROOT / "outputs" / "pipeline" / "06_product_briefs"


def _parse_brief_txt(content: str) -> dict:
    brief: dict = {}
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("PRODUCT BRIEF — "):
            brief["creator_name"] = line.removeprefix("PRODUCT BRIEF — ").strip()
        elif line.startswith("Deal type:"):
            brief["deal_type"] = line.split(":", 1)[1].strip()
        elif line.startswith("Tier:"):
            brief["tier"] = line.split(":", 1)[1].strip()
        elif line.startswith("Niche:"):
            brief["niche"] = line.split(":", 1)[1].strip()
        elif line.startswith("Line:"):
            raw = line.split(":", 1)[1].strip()
            parts = raw.split(" — ", 1)
            brief["product_line"] = parts[0].strip()
            brief["product_line_desc"] = parts[1].strip() if len(parts) > 1 else ""
        elif line.startswith("Send:"):
            brief["items"] = [i.strip() for i in line.split(":", 1)[1].split(",")]
        elif line.startswith("KEY MESSAGE:"):
            brief["key_message"] = line.split(":", 1)[1].strip()
        elif line.startswith("CONTENT FORMAT:"):
            brief["content_format"] = line.split(":", 1)[1].strip()
        elif line.startswith("MUST INCLUDE:"):
            brief["must_include"] = line.split(":", 1)[1].strip()
        elif line.startswith("AVOID:"):
            brief["avoid"] = line.split(":", 1)[1].strip()
        elif line.startswith("POSTING WINDOW:"):
            brief["posting_window"] = line.split(":", 1)[1].strip()
        elif line.startswith("Promo code:"):
            brief["promo_code"] = line.split(":", 1)[1].strip()
        elif line.startswith("Commission:"):
            brief["commission"] = line.split(":", 1)[1].strip()
    return brief


@app.get("/api/product-briefs")
def get_product_briefs():
    if not BRIEFS_DIR.exists():
        return {
            "briefs": [],
            "product_lines": [],
            "cohorts": [],
            "summary": {"total": 0},
        }

    creators_by_name: dict[str, dict] = {}
    try:
        for c in scoring.load_creators(str(DATA_DIR / "creators.csv")):
            name = c.get("name", "")
            if name:
                creators_by_name[name.lower()] = c
    except Exception:
        pass

    briefs = []
    for path in sorted(BRIEFS_DIR.glob("*.txt")):
        b = _parse_brief_txt(path.read_text(encoding="utf-8"))
        if not b.get("creator_name"):
            continue
        creator = creators_by_name.get(b["creator_name"].lower(), {})
        cid = creator.get("creator_id", path.stem)
        subs = int(creator.get("subscribers", 0))
        b.update(
            {
                "creator_id": cid,
                "handle": creator.get("youtube_handle") or b["creator_name"],
                "subscribers": subs,
                "followers": _fmt_subs(subs) if subs else "—",
                "brief_id": path.stem,
            }
        )
        briefs.append(b)

    product_lines: dict[str, dict] = {}
    for b in briefs:
        line = b.get("product_line", "OTHER")
        pl = product_lines.setdefault(
            line,
            {
                "id": line,
                "desc": b.get("product_line_desc", ""),
                "items": b.get("items", []),
                "creator_count": 0,
            },
        )
        pl["creator_count"] += 1

    cohorts: dict[str, dict] = {}
    for b in briefs:
        niche = b.get("niche", "Other")
        co = cohorts.setdefault(niche, {"name": niche, "count": 0, "reach": 0})
        co["count"] += 1
        co["reach"] += b.get("subscribers", 0)

    total_reach = sum(b.get("subscribers", 0) for b in briefs)
    affiliate_count = sum(
        1 for b in briefs if b.get("deal_type", "").upper() == "AFFILIATE"
    )

    return {
        "briefs": briefs,
        "product_lines": list(product_lines.values()),
        "cohorts": list(cohorts.values()),
        "summary": {
            "total": len(briefs),
            "gift_seeding": len(briefs) - affiliate_count,
            "affiliate": affiliate_count,
            "total_reach": total_reach,
            "reach_fmt": _fmt_subs(total_reach),
        },
    }


# ── top performer profile ─────────────────────────────────────────────────────


@app.get("/api/profile")
def get_profile():
    p = ROOT / "data/top_performer_profile.json"
    if not p.exists():
        return {"exists": False}
    with open(p) as f:
        data = json.load(f)
    return {"exists": True, **data}


# ── health ────────────────────────────────────────────────────────────────────


@app.get("/health")
def health():
    return {"status": "ok", "data_dir": str(DATA_DIR), "data_exists": DATA_DIR.exists()}


# ── serve frontend ────────────────────────────────────────────────────────────

_frontend = ROOT / "ui" / "frontend"
if _frontend.exists():
    app.mount("/css", StaticFiles(directory=str(_frontend / "css")), name="css")

    @app.get("/")
    def serve_index():
        return FileResponse(str(_frontend / "index.html"))
