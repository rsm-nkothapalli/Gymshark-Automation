"""
outreach_helpers.py — Skill 02: Personalized Outreach Drafting
Gymshark GenAI Influencer Pipeline · Group 18
"""

import csv
import sys
from pathlib import Path

# Allow importing from rag/ regardless of working directory
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from rag.retrieval import retrieve as _rag_retrieve
    _RAG_AVAILABLE = True
except ImportError:
    _RAG_AVAILABLE = False


def _get_rag_context(tier: str, deal: str, niche: str) -> str:
    """Pull relevant brand guidelines and outreach policy for this creator profile."""
    if not _RAG_AVAILABLE:
        return ""
    query = f"outreach tone {tier} creator {niche} {deal} banned phrases guidelines"
    results = _rag_retrieve(query, top_k=3)
    if not results:
        return ""
    lines = []
    for r in results:
        lines.append(f"[{r['title']} › {r['section']}]\n{r['snippet']}")
    return "\n\n".join(lines)


def load_csv(filepath):
    with open(filepath, newline="", encoding="utf-8") as f:
        return {row["creator_id"]: row for row in csv.DictReader(f)}


def load_creator_context(creator_id, creators_path="data/creators.csv", crm_path="data/crm_records.csv"):
    """
    Returns a merged dict of creator profile + CRM record for a given creator_id.
    CRM fields are merged in where available.
    """
    creators = load_csv(creators_path)
    crm = load_csv(crm_path)

    if creator_id not in creators:
        raise ValueError(f"Creator '{creator_id}' not found in creators.csv")

    context = dict(creators[creator_id])

    if creator_id in crm:
        for key, val in crm[creator_id].items():
            if key not in context or not context[key]:
                context[key] = val

    return context


TIER_TONE_GUIDE = {
    "nano": {"max_words": 80, "ask": "gift product with no posting obligation"},
    "micro": {"max_words": 80, "ask": "affiliate partnership with promo code"},
    "mid": {"max_words": 90, "ask": "paid partnership or retainer"},
    "macro": {"max_words": 90, "ask": "formal partnership discussion"},
    "mega": {"max_words": 70, "ask": "direct ask for a call"},
}

BANNED_PHRASES = [
    "amazing",
    "inspiring",
    "love your content",
    "huge fan",
    "came across your page",
    "perfect fit",
]


def get_tone_guide(tier):
    return TIER_TONE_GUIDE.get(tier.lower(), TIER_TONE_GUIDE["micro"])


def check_banned_phrases(message):
    """Returns list of banned phrases found in the message."""
    lower = message.lower()
    return [phrase for phrase in BANNED_PHRASES if phrase in lower]


def word_count(text):
    return len(text.split())


def format_outreach_output(creator, message, review_note=""):
    """
    Wraps a drafted message in the standard output format.
    """
    name = creator.get("name", "Unknown")
    raw_handle = creator.get("youtube_handle", creator.get("handle", "?"))
    handle = raw_handle.lstrip("@") if raw_handle else "?"
    channel = creator.get("outreach_channel", "Not specified")
    deal = creator.get("suggested_deal_type", creator.get("deal_type", "Not specified"))
    wc = word_count(message)

    header = (
        f"OUTREACH DRAFT — {name} (@{handle})\nChannel: {channel}\nDeal type: {deal}\nWord count: {wc}\n{'-' * 50}\n"
    )
    footer = f"\n{'-' * 50}\n"
    if review_note:
        footer += f"Human review note: {review_note}\n"

    return header + message + footer


def build_outreach_prompt(context: dict, tone_override: str = None) -> str:
    """Build a personalised outreach prompt. tone_override: 'warm' | 'direct' | 'brief'."""
    tier = context.get("tier", "micro")
    guide = get_tone_guide(tier)
    tone = tone_override or "warm"

    name = context.get("name", "Creator")
    first_name = name.split()[0]
    niche = context.get("niche", "fitness")
    content_style = context.get("content_style", "")
    deal = context.get("suggested_deal_type", "partnership")

    signals_pos = (context.get("signals_authentic_pos") or "").strip()
    signals_community = (context.get("signals_community") or "").strip()
    signals_neg = (context.get("signals_neg") or "").strip()
    auth_reasoning = (context.get("authenticity_reasoning") or "").strip()

    # Build background context for the LLM — these are writing angles, NOT phrases to quote
    context_notes = []
    if signals_pos and signals_pos.lower() != "none":
        context_notes.append(f"- This creator values authenticity and is known for unsponsored, honest content. Let this inform your angle — do NOT quote their phrases or reference 'not sponsored' directly.")
    if signals_community and signals_community.lower() != "none":
        context_notes.append(f"- They have a close, personal relationship with their audience. Match that energy.")
    if content_style:
        style_hints = {
            "Try-On Haul": "Their content focuses on real fit and how gear feels on the body — angle the pitch around product quality and honest testing.",
            "Review": "They do structured, honest product breakdowns — angle the pitch around Gymshark's product specifics (material, construction, performance).",
            "Workout Vlog": "They film real training sessions — angle the pitch around how Gymshark gear actually performs under real gym conditions.",
        }
        context_notes.append(f"- {style_hints.get(content_style, f'Content style is {content_style} — match the pitch to how they create.')}")
    if auth_reasoning:
        context_notes.append(f"- Background: {auth_reasoning}")
    if signals_neg and signals_neg.lower() != "none":
        context_notes.append(f"- Do not oversell or make big promises — keep the pitch grounded.")

    rag_context = _get_rag_context(tier, deal, niche)
    rag_section = f"\nBrand policy context (use to stay compliant):\n{rag_context}\n" if rag_context else ""

    never_use = "amazing, inspiring, love your content, huge fan, came across your page, perfect fit, I'm [name], My name is"

    offer = {
        "gift_seeding": "send you some Gymshark gear as a gift — no strings attached",
        "affiliate": "set you up with an affiliate link and promo code to share with your audience",
        "paid_creative_partnership": "discuss a paid content partnership",
        "brand_ambassador": "discuss a brand ambassador role",
        "co_created_collection": "collaborate on a co-created collection",
    }.get(deal, "explore a partnership")

    brevity = {
        "brief": "2 sentences max after the greeting. Ultra short.",
        "direct": f"3-4 sentences max. No fluff. Max {guide['max_words']} words.",
        "warm":   f"4-5 natural sentences. Friendly but not over the top. Max {guide['max_words']} words.",
    }[tone]

    return f"""Write a short outreach email from the Gymshark Partnerships Team to {first_name}, a {niche} creator on YouTube.

Length: {brevity}

Structure:
- Greeting: Hi {first_name},
- Line 1: say we like their content and give ONE specific reason why (their niche, content style, or what makes them stand out). Keep it natural — not a compliment, just a genuine observation.
- Line 2-3: propose the offer — we'd like to {offer}.
- Closing: one simple ask (e.g. would they be open to it / let us know if interested).
- Sign off: Gymshark Partnerships Team

Rules:
- Sound like a real person wrote this, not a marketing bot.
- Do NOT reference "authenticity signals", "brand safety", "GFS scores" or any internal metrics.
- Do NOT use: {never_use}.
- Do NOT mention specific Gymshark product line names (ADAPT, FORM, TRAINING, LIFTING, RUNNING, CBUM, etc.) — just say "our gear" or "our latest collection".
- Write as "we". No fake names.
{rag_section}
Output only the email. No subject line, no markdown."""


def validate_message(message, tier):
    """
    Run checklist on a drafted message. Returns list of issues found.
    """
    issues = []
    banned = check_banned_phrases(message)
    if banned:
        issues.append(f"Banned phrases detected: {banned}")

    guide = get_tone_guide(tier)
    wc = word_count(message)
    if wc > guide["max_words"]:
        issues.append(f"Too long: {wc} words (max {guide['max_words']} for {tier})")

    return issues


# ── Demo: print context for first creator in CSV ───────────────────────────────
if __name__ == "__main__":
    import sys

    try:
        creators_path = "data/creators.csv"
        with open(creators_path, newline="", encoding="utf-8") as f:
            first_id = next(csv.DictReader(f))["creator_id"]
        ctx = load_creator_context(first_id)
        print(f"Context loaded for: {ctx.get('name')} ({first_id})")
        print(f"  Tier: {ctx.get('tier')}")
        print(f"  Deal type: {ctx.get('suggested_deal_type') or ctx.get('deal_type')}")
        print(f"  Discovery notes: {ctx.get('ai_discovery_notes', 'N/A')[:120]}...")
        tone = get_tone_guide(ctx.get("tier", "micro"))
        print(f"  Tone guide: {tone}")
    except FileNotFoundError as e:
        print(f"Run from project root with data/ folder present. ({e})")
