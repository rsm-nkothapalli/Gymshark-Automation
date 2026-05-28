"""
Gymshark Nexus — FastAPI backend
Exposes the influencer pipeline as REST endpoints for the frontend.
"""

import csv
import importlib.util
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def _load_skill(folder: str, module_file: str):
    path = ROOT / "skills" / folder / module_file
    spec = importlib.util.spec_from_file_location(module_file[:-3], path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

app = FastAPI(title="Gymshark Nexus API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _read_csv(path: str) -> list[dict]:
    full = ROOT / path
    if not full.exists():
        return []
    with open(full, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _gfs_tier(score: float) -> str:
    if score >= 7.0:
        return "high"
    if score >= 5.5:
        return "mid"
    return "low"


def _fmt_subs(n: int) -> str:
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(n)


# ── creators ──────────────────────────────────────────────────────────────────

def _existing_partner_handles() -> set[str]:
    """Return lowercase YouTube handles of all existing partners."""
    return {
        r.get("youtube_handle", "").lstrip("@").lower()
        for r in _read_csv("data/existing_partners.csv")
    }


@app.get("/api/creators")
def get_creators():
    rows = _read_csv("data/creators.csv")
    existing = _existing_partner_handles()
    result = []
    for r in rows:
        # Skip anyone already in existing_partners
        handle_clean = r.get("youtube_handle", "").lstrip("@").lower()
        if handle_clean in existing:
            continue

        try:
            gfs = float(r.get("gymshark_brand_fit") or 0)
        except ValueError:
            gfs = 0.0
        try:
            subs = int(r.get("subscribers") or 0)
        except ValueError:
            subs = 0

        niche = r.get("niche", "")
        content_style = r.get("content_style", "")
        tags = [t for t in [niche, content_style] if t]

        result.append({
            "id": r.get("creator_id", ""),
            "name": r.get("name", ""),
            "handle": r.get("youtube_handle", ""),
            "tier": r.get("tier", ""),
            "deal_type": r.get("suggested_deal_type", ""),
            "niche": niche,
            "content_style": content_style,
            "subscribers": subs,
            "subscribers_fmt": _fmt_subs(subs),
            "gfs": round(gfs, 1),
            "gfs_tier": _gfs_tier(gfs),
            "brand_safety": r.get("brand_safety", "GREEN"),
            "outreach_recommended": r.get("outreach_recommended", "False") == "True",
            "country": r.get("country", ""),
            "tags": tags,
            "authenticity_score": r.get("authenticity_score", ""),
            "niche_score": r.get("niche_score", ""),
            "engagement_score": r.get("engagement_score", ""),
            "brand_fit_reasoning": r.get("brand_fit_reasoning", ""),
            "comment_sentiment_score": r.get("comment_sentiment_score", ""),
        })
    return result


@app.get("/api/creators/{creator_id}")
def get_creator(creator_id: str):
    creators = get_creators()
    for c in creators:
        if c["id"] == creator_id:
            return c
    raise HTTPException(status_code=404, detail="Creator not found")


# ── outreach ──────────────────────────────────────────────────────────────────

class OutreachRequest(BaseModel):
    tone: str = "warm"
    deal_type: str = ""


@app.post("/api/creators/{creator_id}/outreach")
def generate_outreach(creator_id: str, req: OutreachRequest):
    creator = get_creator(creator_id)
    # Always compute RAG sources so the frontend can show them regardless of LLM status
    from rag.retrieval import retrieve as rag_retrieve
    tier = creator.get("tier", "micro")
    deal = req.deal_type or creator.get("deal_type", "")
    niche = creator.get("niche", "")
    rag_query = f"outreach tone {tier} creator {niche} {deal} banned phrases guidelines"
    rag_sources = rag_retrieve(rag_query, top_k=3)

    try:
        oh = _load_skill("skill-03-outreach-drafting", "outreach_helpers.py")
        from utils.connect import ask

        ctx = oh.load_creator_context(
            creator_id,
            creators_path=str(ROOT / "data/creators.csv"),
            crm_path=str(ROOT / "data/crm_records.csv"),
        )
        if ctx is None:
            raise HTTPException(status_code=404, detail="Creator not found in CRM")

        if req.deal_type:
            ctx["suggested_deal_type"] = req.deal_type

        prompt = oh.build_outreach_prompt(ctx, tone_override=req.tone)
        draft = ask(prompt, model="api-llama-4-scout")
        return {"draft": draft, "creator": ctx, "rag_sources": rag_sources}
    except Exception as e:
        draft = (
            f"Hi {creator['name'].split()[0]},\n\n"
            f"I came across your channel and loved how authentically you share your "
            f"{creator['niche'].lower()} journey with your community.\n\n"
            f"We'd love to send you some pieces from our latest collection to try out — "
            f"no obligations, just a gift from us to you.\n\n"
            f"Would you be open to a quick chat?\n\nBest,\nGymshark Partnerships"
        )
        return {"draft": draft, "creator": creator, "rag_sources": rag_sources}


# ── rag evidence ─────────────────────────────────────────────────────────────

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
    niche = creator.get("niche", "")
    tier = creator.get("tier", "")
    query = f"{niche} {tier} product line Gymshark partnership"
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

    prompt = f"""You are a Gymshark influencer marketing analyst. Write a detailed brand fit analysis for this creator prospect.

Creator: {creator['name']} ({creator['handle']})
Tier: {creator['tier']} | Subscribers: {creator['subscribers_fmt']}
Niche: {creator['niche']} | Content style: {creator['content_style']}
Country: {creator['country']}

Scores (out of 10):
- Gymshark Fit Score (GFS): {creator['gfs']}
- Authenticity: {creator['authenticity_score']}
- Niche alignment: {creator['niche_score']}
- Engagement: {creator['engagement_score']}
- Comment sentiment: {creator['comment_sentiment_score']}

Brand safety: {creator['brand_safety']}
Deal type: {creator['deal_type']}
Outreach recommended: {creator['outreach_recommended']}
Existing reasoning: {creator.get('brand_fit_reasoning', 'None')}

Write 3–4 sentences covering: why this creator fits (or doesn't fit) the Gymshark brand, what their scores reveal about audience quality, any risks or standout strengths, and what deal type makes sense and why. Be specific and analytical, not generic."""

    analysis = ask(prompt, model="api-llama-4-scout")
    return {"analysis": analysis}


# ── product brief ─────────────────────────────────────────────────────────────

@app.post("/api/creators/{creator_id}/brief")
def generate_brief(creator_id: str):
    try:
        bh = _load_skill("skill-05-product-brief", "brief_helpers.py")
        brief = bh.generate_full_brief(creator_id)
        return {"brief": brief}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── resolve real youtube handle from name ─────────────────────────────────────

@app.post("/api/creators/{creator_id}/resolve-handle")
def resolve_handle(creator_id: str):
    """Search YouTube by creator name, return the real handle, and update creators.csv."""
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key or "Paste" in api_key:
        raise HTTPException(status_code=503, detail="YOUTUBE_API_KEY not configured")

    creator = get_creator(creator_id)
    name = creator["name"]

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)

        resp = youtube.search().list(
            q=name, part="snippet", type="channel", maxResults=5
        ).execute()
        items = resp.get("items", [])
        if not items:
            return {"resolved": False, "message": "No channels found"}

        # Fetch full channel details to get real handles
        channel_ids = [i["snippet"]["channelId"] for i in items]
        ch_resp = youtube.channels().list(
            id=",".join(channel_ids), part="snippet,statistics"
        ).execute()

        candidates = []
        for ch in ch_resp.get("items", []):
            snip = ch["snippet"]
            handle = snip.get("customUrl", "")  # this is the real @handle
            candidates.append({
                "channel_id": ch["id"],
                "title": snip.get("title", ""),
                "handle": handle,
                "subscribers": int(ch.get("statistics", {}).get("subscriberCount", 0)),
                "thumbnail": snip.get("thumbnails", {}).get("default", {}).get("url", ""),
            })

        # Best match: channel whose title most closely matches creator name
        name_lower = name.lower().replace(" ", "")
        best = sorted(candidates, key=lambda c: (
            name_lower not in c["title"].lower().replace(" ", ""),
            -c["subscribers"]
        ))[0]

        # Update creators.csv with the resolved handle
        if best["handle"]:
            csv_path = ROOT / "data/creators.csv"
            with open(csv_path, "r", encoding="utf-8") as f:
                content = f.read()
            old_handle = creator["handle"]
            new_handle = best["handle"] if best["handle"].startswith("@") else f"@{best['handle']}"
            updated = content.replace(f",{old_handle},", f",{new_handle},")
            with open(csv_path, "w", encoding="utf-8") as f:
                f.write(updated)

        return {
            "resolved": True,
            "candidates": candidates,
            "best": best,
            "old_handle": creator["handle"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── youtube videos ───────────────────────────────────────────────────────────

@app.get("/api/creators/{creator_id}/videos")
def get_creator_videos(creator_id: str):
    api_key = os.getenv("YOUTUBE_API_KEY", "")
    if not api_key or "Paste" in api_key:
        raise HTTPException(status_code=503, detail="YOUTUBE_API_KEY not configured")

    creator = get_creator(creator_id)
    handle = creator["handle"].lstrip("@")
    name = creator["name"]

    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)

        # Strip special chars that are invalid in YouTube handles
        clean_handle = "".join(c for c in handle if c.isalnum() or c in "_.")

        channel_id = None
        if clean_handle:
            resp = youtube.channels().list(
                forHandle=clean_handle, part="id,snippet"
            ).execute()
            items = resp.get("items", [])
            if items:
                channel_id = items[0]["id"]

        # No name-search fallback — it finds wrong creators for common names
        if not channel_id:
            return {"videos": [], "channel_id": None, "handle": clean_handle}

        search_resp = youtube.search().list(
            channelId=channel_id, part="snippet", order="date",
            type="video", maxResults=6
        ).execute()

        video_ids = [i["id"]["videoId"] for i in search_resp.get("items", [])]
        snippets = {i["id"]["videoId"]: i["snippet"] for i in search_resp.get("items", [])}

        if not video_ids:
            return {"videos": [], "channel_id": channel_id}

        stats_resp = youtube.videos().list(
            part="statistics,contentDetails", id=",".join(video_ids)
        ).execute()

        videos = []
        for item in stats_resp.get("items", []):
            vid = item["id"]
            snip = snippets.get(vid, {})
            stats = item.get("statistics", {})
            duration = item.get("contentDetails", {}).get("duration", "")
            thumb = (snip.get("thumbnails", {}).get("medium") or
                     snip.get("thumbnails", {}).get("default") or {}).get("url", "")
            videos.append({
                "video_id": vid,
                "title": snip.get("title", ""),
                "thumbnail": thumb,
                "views": int(stats.get("viewCount", 0)),
                "likes": int(stats.get("likeCount", 0)),
                "published_at": snip.get("publishedAt", "")[:10],
                "duration": duration,
                "url": f"https://www.youtube.com/watch?v={vid}",
            })

        return {"videos": videos, "channel_id": channel_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── analytics ─────────────────────────────────────────────────────────────────

@app.get("/api/analytics")
def get_analytics():
    campaigns = _read_csv("data/campaign_performance.csv")
    partners = {r["creator_id"]: r for r in _read_csv("data/existing_partners.csv")}

    total_revenue = 0.0
    total_budget = 0.0
    total_reach = 0
    campaign_count = len(campaigns)
    by_tier: dict[str, dict] = {}
    by_deal: dict[str, dict] = {}
    creator_summary: list[dict] = []

    seen_creators: dict[str, dict] = {}

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

        if tier not in by_tier:
            by_tier[tier] = {"revenue": 0, "budget": 0, "count": 0, "roi_sum": 0}
        by_tier[tier]["revenue"] += rev
        by_tier[tier]["budget"] += budget
        by_tier[tier]["count"] += 1
        by_tier[tier]["roi_sum"] += roi

        if deal not in by_deal:
            by_deal[deal] = {"revenue": 0, "budget": 0, "count": 0}
        by_deal[deal]["revenue"] += rev
        by_deal[deal]["budget"] += budget
        by_deal[deal]["count"] += 1

        cid = c.get("creator_id", "")
        if cid not in seen_creators:
            p = partners.get(cid, {})
            seen_creators[cid] = {
                "id": cid,
                "name": c.get("creator_name", p.get("name", cid)),
                "handle": p.get("youtube_handle", ""),
                "tier": tier,
                "deal_type": deal,
                "niche": p.get("niche", ""),
                "revenue": 0, "budget": 0, "roi_sum": 0,
                "clicks": 0, "redemptions": 0, "count": 0,
            }
        sc = seen_creators[cid]
        sc["revenue"] += rev
        sc["budget"] += budget
        sc["roi_sum"] += roi
        sc["clicks"] += clicks
        sc["redemptions"] += redemptions
        sc["count"] += 1

    for cid, sc in seen_creators.items():
        n = sc["count"]
        avg_roi = round(sc["roi_sum"] / n, 2) if n else 0
        conv = round(sc["redemptions"] / sc["clicks"], 3) if sc["clicks"] > 0 else None
        creator_summary.append({
            "id": sc["id"],
            "name": sc["name"],
            "handle": sc["handle"],
            "tier": sc["tier"],
            "deal_type": sc["deal_type"],
            "niche": sc["niche"],
            "revenue": round(sc["revenue"], 0),
            "budget": round(sc["budget"], 0),
            "avg_roi_x": avg_roi,
            "conversion_rate": conv,
            "campaigns": n,
            "renewal": "Yes",
        })

    creator_summary.sort(key=lambda x: x["avg_roi_x"], reverse=True)

    overall_roi = round(total_revenue / total_budget, 2) if total_budget else 0

    tier_data = [
        {"tier": t, "avg_roi": round(v["roi_sum"] / v["count"], 2),
         "revenue": round(v["revenue"], 0), "count": v["count"]}
        for t, v in by_tier.items()
    ]

    deal_data = [
        {"deal_type": d, "revenue": round(v["revenue"], 0),
         "budget": round(v["budget"], 0), "count": v["count"]}
        for d, v in by_deal.items()
    ]

    return {
        "summary": {
            "total_revenue": round(total_revenue, 0),
            "total_budget": round(total_budget, 0),
            "overall_roi_x": overall_roi,
            "total_reach": total_reach,
            "campaign_count": campaign_count,
            "partner_count": len(seen_creators),
        },
        "by_tier": tier_data,
        "by_deal": deal_data,
        "creators": creator_summary,
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


# ── serve frontend ────────────────────────────────────────────────────────────

frontend = ROOT / "frontend"
if frontend.exists():
    app.mount("/css", StaticFiles(directory=str(frontend / "css")), name="css")

    @app.get("/")
    def serve_index():
        return FileResponse(str(frontend / "index.html"))
