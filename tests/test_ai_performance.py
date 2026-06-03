"""
Section 6 — Testing AI Performance
DeepEval test suite for the Gymshark Influencer Pipeline.

Covers:
  - Outreach drafting (Skill-03 + LLM)         — 7 cases
  - Brand-fit analysis (api/main.py + LLM)     — 3 cases
  - Product brief generation (Skill-05 + LLM)  — 3 cases
  - Before/After improvement test              — 2 additional outreach-03 variants

Judge model: api-gpt-oss-120b via TritonAI (more reliable JSON output for DeepEval).

Run (from repo root):
    uv run pytest -m integration tests/test_ai_performance.py -v -s

Results land in:  tests/results/<date>_ai_perf.jsonl
Report template:  tests/test_report.md
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────


def _load_outreach_helpers():
    spec = importlib.util.spec_from_file_location(
        "outreach_helpers",
        ROOT / "skills/skill-03-outreach-drafting/outreach_helpers.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ask(prompt: str, temperature: float = 0.4) -> str:
    from utils.connect import ask

    return ask(prompt, model="api-llama-4-scout", temperature=temperature) or ""


def _retrieve_context(tier: str, niche: str, deal: str, top_k: int = 3) -> list[str]:
    """Return RAG snippets as plain strings for FaithfulnessMetric."""
    from rag.retrieval import retrieve

    query = f"outreach tone {tier} creator {niche} {deal} banned phrases guidelines"
    results = retrieve(query, top_k=top_k)
    return [f"[{r['title']} › {r['section']}] {r['snippet']}" for r in results]


# ── custom DeepEval judge model (wraps TritonAI) ──────────────────────────────


def _make_judge():
    """Return a DeepEvalBaseLLM that uses TritonAI so no OpenAI key is needed."""
    from deepeval.models.base_model import DeepEvalBaseLLM

    class TritonJudge(DeepEvalBaseLLM):
        def load_model(self):
            return None

        def generate(self, prompt: str, schema=None):
            from utils.connect import ask as _ask_raw

            result = _ask_raw(prompt, model="api-gpt-oss-120b", temperature=0.0) or ""
            if schema is not None:
                try:
                    data = json.loads(result)
                    return schema(**data)
                except Exception:
                    pass
            return result

        async def a_generate(self, prompt: str, schema=None):
            return self.generate(prompt, schema)

        def get_model_name(self) -> str:
            return "api-gpt-oss-120b"

    return TritonJudge()


# ── test cases ────────────────────────────────────────────────────────────────
#
# Each dict must have:
#   id                — unique slug
#   label             — one-line description for the results table
#   creator_context   — dict passed to build_outreach_prompt() (or brand-fit prompt)
#   expected_output   — 1-2 sentences describing what a good answer looks like
#   covers_failure    — failure case ID from failure_cases.md (or None)
#   mode              — "outreach" | "brand_fit"
#   tone              — tone override for outreach (default "warm")
#

OUTREACH_CASES: list[dict] = [
    # ── normal / happy-path cases ─────────────────────────────────────────────
    {
        "id": "outreach-01-nano-yoga",
        "label": "Nano yoga creator, gift seeding, warm tone",
        "mode": "outreach",
        "tone": "warm",
        "covers_failure": None,
        "creator_context": {
            "name": "Isabelle Chen",
            "tier": "nano",
            "niche": "Yoga & Wellness",
            "content_style": "Workout Vlog",
            "suggested_deal_type": "gift_seeding",
            "signals_authentic_pos": "talks to camera without script, mentions how sore she is after class",
            "signals_community": "responds to every comment, calls followers 'practice family'",
            "authenticity_reasoning": "Feels like a genuine practitioner sharing her journey, not a polished influencer.",
            "signals_neg": "",
        },
        "expected_output": (
            "A warm, peer-level email under 300 words that greets Isabelle by first name, "
            "makes one specific observation about her yoga content (not generic praise), "
            "proposes sending her Gymshark gear with no posting obligation, "
            "ends with a simple open-ended ask, and signs off as Gymshark Partnerships Team."
        ),
    },
    {
        "id": "outreach-02-micro-affiliate",
        "label": "Micro general fitness creator, affiliate deal, workout vlog",
        "mode": "outreach",
        "tone": "warm",
        "covers_failure": None,
        "creator_context": {
            "name": "Will Tennyson",
            "tier": "micro",
            "niche": "General Fitness",
            "content_style": "Workout Vlog",
            "suggested_deal_type": "affiliate",
            "signals_authentic_pos": "films real training sessions, no editing cuts mid-set",
            "signals_community": "shoutouts viewers who share their own progress",
            "authenticity_reasoning": "Authentic training content with real effort shown on camera.",
            "signals_neg": "",
        },
        "expected_output": (
            "A warm email under 300 words referencing his workout vlog style, "
            "proposing an affiliate link and promo code setup, "
            "and ending with a clear invitation to discuss."
        ),
    },
    # ── FC-04: word-count compliance (mega tier) ──────────────────────────────
    {
        "id": "outreach-03-mega-word-limit",
        "label": "Mega bodybuilding creator, brand ambassador — word-count compliance (FC-04)",
        "mode": "outreach",
        "tone": "brief",
        "covers_failure": "FC-04",
        "creator_context": {
            "name": "Chris Thompson",
            "tier": "mega",
            "niche": "Bodybuilding",
            "content_style": "Review",
            "suggested_deal_type": "brand_ambassador",
            "signals_authentic_pos": "detailed equipment and gear breakdowns",
            "signals_community": "large, loyal lifting community",
            "authenticity_reasoning": "Well-known in the competitive lifting space with credibility.",
            "signals_neg": "",
        },
        "expected_output": (
            "An ultra-brief pitch (200 words or fewer) in a direct, pitch-led tone "
            "that proposes a brand ambassador discussion and ends with a call-to-action. "
            "No fluff, no pleasantries beyond the greeting."
        ),
    },
    # ── FC-02: banned phrase avoidance ────────────────────────────────────────
    {
        "id": "outreach-04-banned-phrases",
        "label": "Nano strength creator — banned phrase avoidance (FC-02)",
        "mode": "outreach",
        "tone": "warm",
        "covers_failure": "FC-02",
        "creator_context": {
            "name": "Sophie Reid",
            "tier": "nano",
            "niche": "Strength Training",
            "content_style": "Workout Vlog",
            "suggested_deal_type": "gift_seeding",
            "signals_authentic_pos": "raw, unedited gym footage",
            "signals_community": "supportive lifting community",
            "authenticity_reasoning": "Authentic strength content with no sponsor saturation.",
            "signals_neg": "",
        },
        "expected_output": (
            "A warm nano-tier gift-seeding email that contains none of the banned phrases: "
            "'amazing', 'inspiring', 'love your content', 'huge fan', "
            "'came across your page', 'perfect fit'."
        ),
    },
    # ── FC-03: no internal metric leakage ────────────────────────────────────
    {
        "id": "outreach-05-no-metric-leakage",
        "label": "Micro HIIT creator — no internal metric leakage in draft (FC-03)",
        "mode": "outreach",
        "tone": "warm",
        "covers_failure": "FC-03",
        "creator_context": {
            "name": "Kayla Lashae",
            "tier": "micro",
            "niche": "HIIT & Cardio",
            "content_style": "Try-On Haul",
            "suggested_deal_type": "affiliate",
            "signals_authentic_pos": "honest fit feedback, shows multiple sizes",
            "signals_community": "interactive Q&A during try-ons",
            "authenticity_reasoning": "Trusted voice for activewear reviews in the HIIT community.",
            "signals_neg": "",
        },
        "expected_output": (
            "An outreach email that reads like it came from a real person, "
            "with no references to scoring systems, GFS scores, risk levels, "
            "authenticity numbers, or any internal pipeline metrics."
        ),
    },
    # ── FC-05: no generic output when signals are missing ────────────────────
    {
        "id": "outreach-06-minimal-context",
        "label": "Nano creator with no signals — should avoid generic template (FC-05)",
        "mode": "outreach",
        "tone": "warm",
        "covers_failure": "FC-05",
        "creator_context": {
            "name": "Jordan Park",
            "tier": "nano",
            "niche": "Functional Fitness",
            "content_style": "",
            "suggested_deal_type": "gift_seeding",
            "signals_authentic_pos": "",
            "signals_community": "",
            "authenticity_reasoning": "",
            "signals_neg": "",
        },
        "expected_output": (
            "An email that makes at least one specific, non-generic observation tied to "
            "functional fitness content — not a filler compliment like 'love your content'. "
            "Even with no signals provided, the draft should feel targeted rather than templated."
        ),
    },
    # ── FC-07: grounded pitch when negative signals are present ──────────────
    {
        "id": "outreach-07-negative-signals",
        "label": "Micro creator with competitor sponsor history — grounded pitch (FC-07)",
        "mode": "outreach",
        "tone": "warm",
        "covers_failure": "FC-07",
        "creator_context": {
            "name": "Jenni Ducklas",
            "tier": "micro",
            "niche": "General Fitness",
            "content_style": "Review",
            "suggested_deal_type": "gift_seeding",
            "signals_authentic_pos": "thorough gear reviews, testing over multiple sessions",
            "signals_community": "engaged comment section on review videos",
            "authenticity_reasoning": "Strong reviewer credibility, though has worked with several brands before.",
            "signals_neg": "Has promoted competitor activewear brands in past 6 months.",
        },
        "expected_output": (
            "A measured, non-pushy email that does not oversell the partnership, "
            "does not promise exclusivity it cannot deliver, and leaves the door "
            "open without pressuring a response."
        ),
    },
]

BRAND_FIT_CASES: list[dict] = [
    # ── normal: strong creator ────────────────────────────────────────────────
    {
        "id": "brand-fit-01-strong",
        "label": "High-GFS creator, GREEN safety, LOW risk — positive recommendation",
        "mode": "brand_fit",
        "tone": None,
        "covers_failure": None,
        "creator_context": {
            "name": "Whitney Simmons",
            "handle": "@whitneysimmons",
            "tier": "macro",
            "niche": "General Fitness",
            "content_style": "Workout Vlog",
            "subscribers_fmt": "4.0M",
            "country": "US",
            "gfs": "8.5",
            "authenticity_score": "8",
            "niche_score": "8",
            "engagement_score": "7",
            "comment_sentiment_score": "8",
            "risk_level": "LOW",
            "brand_safety": "GREEN",
            "deal_type": "affiliate",
            "outreach_recommended": "True",
            "brand_fit_reasoning": "Highly authentic fitness creator with strong Gymshark audience overlap.",
        },
        "expected_output": (
            "A 3–4 sentence analysis that endorses outreach, explains what the strong scores "
            "reveal about audience quality, cites the LOW risk and GREEN safety as positives, "
            "and recommends an affiliate deal with clear rationale."
        ),
    },
    # ── FC-06: high-risk creator — analysis must flag concerns ───────────────
    {
        "id": "brand-fit-02-high-risk",
        "label": "AMBER safety, HIGH risk creator — analysis must flag concerns (FC-06)",
        "mode": "brand_fit",
        "tone": None,
        "covers_failure": "FC-06",
        "creator_context": {
            "name": "Marcus Reed",
            "handle": "@marcusreed",
            "tier": "micro",
            "niche": "General Fitness",
            "content_style": "Review",
            "subscribers_fmt": "120K",
            "country": "UK",
            "gfs": "6.0",
            "authenticity_score": "5",
            "niche_score": "6",
            "engagement_score": "5",
            "comment_sentiment_score": "4",
            "risk_level": "HIGH",
            "brand_safety": "AMBER",
            "deal_type": "gift_seeding",
            "outreach_recommended": "False",
            "brand_fit_reasoning": "Some brand-trust warnings detected in comment section.",
        },
        "expected_output": (
            "A 3–4 sentence analysis that explicitly acknowledges the HIGH risk level "
            "and AMBER brand safety, explains what the lower scores suggest, and "
            "recommends pausing or human review before proceeding — not a positive endorsement."
        ),
    },
    # ── FC-01: no hallucination — analysis must stay grounded in provided data
    {
        "id": "brand-fit-03-no-hallucination",
        "label": "Minimal-info creator — analysis must not fabricate claims (FC-01)",
        "mode": "brand_fit",
        "tone": None,
        "covers_failure": "FC-01",
        "creator_context": {
            "name": "Alex Rivera",
            "handle": "@alexrivera",
            "tier": "nano",
            "niche": "Functional Fitness",
            "content_style": "Workout Vlog",
            "subscribers_fmt": "8K",
            "country": "US",
            "gfs": "7.0",
            "authenticity_score": "7",
            "niche_score": "6",
            "engagement_score": "7",
            "comment_sentiment_score": "6",
            "risk_level": "UNKNOWN",
            "brand_safety": "GREEN",
            "deal_type": "gift_seeding",
            "outreach_recommended": "True",
            "brand_fit_reasoning": "Limited data — scored from channel stats only, no transcript.",
        },
        "expected_output": (
            "A grounded 3–4 sentence analysis that works only from the data provided. "
            "It should not invent competitor affiliations, audience demographics beyond "
            "what is stated, or specific content examples not in the context. "
            "UNKNOWN risk should be noted as a data gap, not assumed safe."
        ),
    },
]

BRIEF_CASES: list[dict] = [
    # ── normal: yoga gift-seeding — all sections, niche-specific language ────
    {
        "id": "brief-01-yoga-gift",
        "label": "Nano yoga creator, gift seeding — all 5 sections, yoga-specific language",
        "mode": "brief",
        "tone": None,
        "covers_failure": None,
        "product_line": "adapt",
        "product_line_description": "Yoga and studio — leggings, sports bras, and crop tops for low-impact studio work",
        "product_line_items": "Flex High Waist Leggings, Flex Sports Bra, Studio Crop Top",
        "creator_context": {
            "name": "Isabelle Chen",
            "handle": "@isabelle.moves",
            "tier": "nano",
            "niche": "Yoga & Wellness",
            "deal_type": "gift_seeding",
            "audience_female_pct": 78,
            "audience_male_pct": 22,
            "top_country": "US",
        },
        "expected_output": (
            "A product brief with all five sections (KEY MESSAGE, CONTENT FORMAT, MUST INCLUDE, AVOID, POSTING WINDOW), "
            "where KEY MESSAGE speaks to yoga practitioners specifically, "
            "CONTENT FORMAT suggests a studio or flow-based video format, "
            "and the brief reflects a gift seeding deal — no posting obligation, relaxed tone."
        ),
    },
    # ── FC-05: affiliate deal — brief must reference commission, not be generic ─
    {
        "id": "brief-02-strength-affiliate",
        "label": "Micro strength creator, affiliate deal — commission context, niche-specific (FC-05)",
        "mode": "brief",
        "tone": None,
        "covers_failure": "FC-05",
        "product_line": "lifting",
        "product_line_description": "Powerlifting and strength — belt-friendly shorts, knee sleeves, and lifting shoes",
        "product_line_items": "Apex Shorts, Hardcore Lifting Belt, Weightlifting Shoes",
        "creator_context": {
            "name": "Jake Barros",
            "handle": "@jakebarroslifts",
            "tier": "micro",
            "niche": "Strength Training",
            "deal_type": "affiliate",
            "audience_female_pct": 18,
            "audience_male_pct": 82,
            "top_country": "UK",
        },
        "expected_output": (
            "A product brief with all five sections, where KEY MESSAGE is specific to strength training "
            "and lifting performance (not generic fitness), MUST INCLUDE references the promo code or "
            "affiliate link, and POSTING WINDOW is appropriate for a strength-training audience."
        ),
    },
    # ── FC-01: no hallucination — brief must stay grounded in provided context ──
    {
        "id": "brief-03-no-hallucination",
        "label": "Minimal-context creator — brief must not fabricate claims (FC-01)",
        "mode": "brief",
        "tone": None,
        "covers_failure": "FC-01",
        "product_line": "training",
        "product_line_description": "All-purpose gym training — shorts, t-shirts, hoodies, joggers for general gym use",
        "product_line_items": "Arrival Shorts, Rest Day Hoodie, Training Oversized T-Shirt",
        "creator_context": {
            "name": "Casey Morgan",
            "handle": "@caseymorgan",
            "tier": "nano",
            "niche": "Functional Fitness",
            "deal_type": "gift_seeding",
            "audience_female_pct": 50,
            "audience_male_pct": 50,
            "top_country": "US",
        },
        "expected_output": (
            "A grounded brief that works only from the data provided. "
            "It should not invent specific audience traits beyond what is stated, "
            "claim the creator has an established following in a specific vertical not mentioned, "
            "or reference Gymshark product features not in the product line description."
        ),
    },
]

ALL_CASES = OUTREACH_CASES + BRAND_FIT_CASES + BRIEF_CASES


# ── workflow runners ──────────────────────────────────────────────────────────


def _run_outreach(case: dict) -> tuple[str, list[str]]:
    """Generate outreach draft and return (draft, retrieval_context_strings)."""
    oh = _load_outreach_helpers()
    ctx = case["creator_context"]
    tier = ctx.get("tier", "micro")
    deal = ctx.get("suggested_deal_type", "partnership")
    niche = ctx.get("niche", "fitness")

    rag_ctx = _retrieve_context(tier, niche, deal)
    prompt = oh.build_outreach_prompt(ctx, tone_override=case.get("tone"))
    draft = _ask(prompt)
    return draft, rag_ctx


def _run_brand_fit(case: dict) -> tuple[str, list[str]]:
    """Generate brand-fit analysis and return (analysis, retrieval_context_strings)."""
    creator = case["creator_context"]
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
    if creator.get("risk_level") == "HIGH":
        prompt += (
            "\n\nHARD RULE — HIGH RISK CREATOR: Because this creator is flagged HIGH risk, "
            "your analysis must close with this exact sentence on its own line: "
            "'Recommendation: Do not proceed without human review.'"
        )
    analysis = _ask(prompt)
    # retrieval context = the scores / reasoning block sent to the LLM
    context_strings = [
        f"Creator scores: GFS={creator['gfs']}, Authenticity={creator['authenticity_score']}, "
        f"Niche={creator['niche_score']}, Engagement={creator['engagement_score']}, "
        f"Sentiment={creator['comment_sentiment_score']}",
        f"Risk level: {creator['risk_level']}, Brand safety: {creator['brand_safety']}",
        f"Existing reasoning: {creator.get('brand_fit_reasoning', 'None')}",
    ]
    return analysis, context_strings


def _run_brief(case: dict) -> tuple[str, list[str]]:
    """Generate product brief creative section and return (brief, context_strings)."""
    creator = case["creator_context"]
    product_line = case["product_line"]
    line_desc = case["product_line_description"]
    line_items = case["product_line_items"]
    deal_note = (
        "This is a gifted partnership — no posting obligation, but we hope they love the kit."
        if creator["deal_type"] == "gift_seeding"
        else "This is an affiliate partnership — they earn commission on every sale via their promo code."
    )
    prompt = (
        "You are a Gymshark brand partnerships manager writing a creative brief for an influencer.\n\n"
        f"Creator: {creator['name']} (@{creator['handle']})\n"
        f"Tier: {creator['tier']}\n"
        f"Niche: {creator['niche']}\n"
        f"Audience: {creator['audience_female_pct']}% female / {creator['audience_male_pct']}% male, "
        f"top country: {creator['top_country']}\n"
        f"Deal: {creator['deal_type']} — {deal_note}\n"
        f"Product line to feature: {product_line.upper()} — {line_desc}\n"
        f"Suggested items: {line_items}\n\n"
        "Write a creative brief in exactly this format (under 200 words total):\n\n"
        "KEY MESSAGE: [one sentence — what Gymshark wants the audience to feel or do]\n"
        "CONTENT FORMAT: [specific format suggestion e.g. YouTube workout integration, Instagram try-on Reel]\n"
        "MUST INCLUDE: [two brand points they must mention]\n"
        "AVOID: [one thing — tone, claim, or comparison to avoid]\n"
        "POSTING WINDOW: [best time to post based on their niche and audience]\n\n"
        "Be specific to this creator's niche and audience. No generic language."
    )
    brief = _ask(prompt)
    context_strings = [
        f"Creator: {creator['name']}, tier={creator['tier']}, niche={creator['niche']}",
        f"Deal type: {creator['deal_type']}",
        f"Product line: {product_line.upper()} — {line_desc}",
        f"Suggested items: {line_items}",
        f"Audience: {creator['audience_female_pct']}% female, top country: {creator['top_country']}",
    ]
    return brief, context_strings


# ── result recorder ───────────────────────────────────────────────────────────


def _record(case: dict, output: str, metrics: list, tag: str = "") -> None:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    suffix = f"_{tag}" if tag else ""
    path = RESULTS_DIR / f"{stamp}_ai_perf{suffix}.jsonl"
    row = {
        "case_id": case["id"],
        "label": case.get("label", ""),
        "output_preview": output[:300],
        "word_count": len(output.split()),
        "covers_failure": case.get("covers_failure"),
        "metrics": [
            {
                "name": m.__class__.__name__,
                "score": getattr(m, "score", None),
                "passed": getattr(m, "success", None),
                "reason": getattr(m, "reason", None),
            }
            for m in metrics
        ],
    }
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row) + "\n")


# ── shared metric builders ────────────────────────────────────────────────────


def _build_metrics(judge, mode: str):
    from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric, GEval
    from deepeval.test_case import SingleTurnParams

    faithfulness = FaithfulnessMetric(threshold=0.6, model=judge)
    answer_relevancy = AnswerRelevancyMetric(threshold=0.6, model=judge)

    if mode == "outreach":
        quality_rule = GEval(
            name="OutreachQuality",
            criteria=(
                "The outreach email: "
                "(1) greets the creator by first name only, "
                "(2) makes at least one specific non-generic observation about their content or niche "
                "    — not a filler compliment like 'love your content', "
                "(3) clearly states the offer (gift, affiliate, partnership, etc.), "
                "(4) ends with a single simple ask or open question, "
                "(5) signs off as 'Gymshark Partnerships Team' or similar. "
                "Award a high score only if all five are present."
            ),
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            threshold=0.6,
            model=judge,
        )
        face_validity = GEval(
            name="OutreachFaceValidity",
            criteria=(
                "An experienced Gymshark partnerships manager reviewing this email would find it: "
                "professional enough to send without edits, clearly targeted at this specific creator, "
                "and free of red flags (no sycophantic openers, no internal jargon, "
                "no Gymshark product line names like ADAPT/FORM/CBUM/SEAMLESS). "
                "If any red flag is present, score low."
            ),
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            threshold=0.6,
            model=judge,
        )
    elif mode == "brief":
        quality_rule = GEval(
            name="BriefQuality",
            criteria=(
                "The product brief: "
                "(1) contains all five required sections: KEY MESSAGE, CONTENT FORMAT, MUST INCLUDE, AVOID, POSTING WINDOW, "
                "(2) KEY MESSAGE is specific to the creator's niche — not generic fitness language, "
                "(3) CONTENT FORMAT names a concrete video or social format appropriate to the niche, "
                "(4) AVOID names one specific thing relevant to this creator or deal type. "
                "Award a high score only if all four are present."
            ),
            evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
            threshold=0.6,
            model=judge,
        )
        face_validity = GEval(
            name="BriefFaceValidity",
            criteria=(
                "A Gymshark brand partnerships manager would consider this brief ready to send: "
                "the product line aligns with the creator's niche and audience demographics provided in the context, "
                "no product features or audience traits are claimed that are not in the retrieval context, "
                "and the tone matches the deal type (gift seeding: relaxed, no obligation mentioned; "
                "affiliate: commission or promo code referenced)."
            ),
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.RETRIEVAL_CONTEXT,
            ],
            threshold=0.6,
            model=judge,
        )
    else:
        quality_rule = GEval(
            name="BrandFitQuality",
            criteria=(
                "The brand-fit analysis: "
                "(1) cites at least two specific scores from the data (GFS, authenticity, niche, engagement, or sentiment), "
                "(2) explains what those scores imply about audience quality or brand risk, "
                "(3) names at least one concrete risk or standout strength, "
                "(4) recommends a specific deal type with a one-sentence rationale. "
                "Award a high score only if all four are present."
            ),
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.RETRIEVAL_CONTEXT,
            ],
            threshold=0.6,
            model=judge,
        )
        face_validity = GEval(
            name="BrandFitFaceValidity",
            criteria=(
                "A head of influencer partnerships would find this analysis accurate and actionable: "
                "the overall recommendation (proceed / hold / escalate) aligns with the risk and safety signals "
                "provided in the retrieval context, "
                "the magnitude of concern or enthusiasm matches the scores in the context, "
                "and no specific claims are made that are not supported by the retrieval context provided."
            ),
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.RETRIEVAL_CONTEXT,
            ],
            threshold=0.6,
            model=judge,
        )

    return [faithfulness, answer_relevancy, quality_rule, face_validity]


# ── main test: all 10 cases ───────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.parametrize("case", ALL_CASES, ids=[c["id"] for c in ALL_CASES])
def test_ai_performance(case: dict) -> None:
    """Run one case end-to-end and score it with 4 DeepEval metrics.

    Covers: 7 outreach cases, 3 brand-fit cases, 3 product brief cases (13 total).
    """
    from deepeval.test_case import LLMTestCase

    judge = _make_judge()

    if case["mode"] == "outreach":
        actual_output, retrieval_context = _run_outreach(case)
        task_input = (
            f"Draft a {case['tone'] or 'warm'}-tone outreach email for "
            f"{case['creator_context']['name']} "
            f"({case['creator_context']['tier']} {case['creator_context']['niche']} creator, "
            f"{case['creator_context']['suggested_deal_type']} deal)."
        )
    elif case["mode"] == "brief":
        actual_output, retrieval_context = _run_brief(case)
        task_input = (
            f"Write a product brief for {case['creator_context']['name']} "
            f"({case['creator_context']['tier']} {case['creator_context']['niche']} creator, "
            f"{case['creator_context']['deal_type']} deal, {case['product_line'].upper()} product line)."
        )
    else:
        actual_output, retrieval_context = _run_brand_fit(case)
        task_input = (
            f"Analyze brand fit for {case['creator_context']['name']} "
            f"(GFS={case['creator_context']['gfs']}, "
            f"risk={case['creator_context']['risk_level']}, "
            f"safety={case['creator_context']['brand_safety']})."
        )

    test_case = LLMTestCase(
        input=task_input,
        actual_output=actual_output,
        expected_output=case["expected_output"],
        retrieval_context=retrieval_context,
    )

    metrics = _build_metrics(judge, case["mode"])

    # Measure each metric directly so .score/.success are populated on the object,
    # then record, then raise if anything failed.
    for m in metrics:
        m.measure(test_case)

    _record(case, actual_output, metrics)

    failed = [m for m in metrics if not m.success]
    if failed:
        desc = "; ".join(
            f"{m.__class__.__name__}(score={m.score:.2f}, reason={getattr(m, 'reason', '')[:120]})" for m in failed
        )
        raise AssertionError(f"Metrics failed: {desc}")


# ── before / after improvement test (FC-04: mega word count) ─────────────────
#
# Weakness: the word-count instruction for mega-tier is soft natural language.
# Change:   add a HARD LIMIT line after the main rules with an explicit count.
# Expected: "after" version more consistently stays at/below 200 words.


def _build_prompt_v2_strict_wordcount(context: dict, tone_override: str = None) -> str:
    """Outreach prompt with explicit word-count hard limit appended (v2 / 'after')."""
    oh = _load_outreach_helpers()
    base_prompt = oh.build_outreach_prompt(context, tone_override=tone_override)
    guide = oh.get_tone_guide(context.get("tier", "micro"))
    max_words = guide["max_words"]
    hard_limit = (
        f"\nHARD LIMIT — COUNT YOUR WORDS: "
        f"Your entire response must be {max_words} words or fewer. "
        f"If you reach {max_words} words, stop. Do not exceed this under any circumstances."
    )
    return base_prompt + hard_limit


_MEGA_CASE = next(c for c in OUTREACH_CASES if c["id"] == "outreach-03-mega-word-limit")


@pytest.mark.integration
def test_before_improvement_mega_wordcount() -> None:
    """BEFORE: standard prompt for mega creator.

    Word count is a deterministic property — no LLM judge needed.
    We record the draft and assert Python-side that wc <= 200.
    """
    oh = _load_outreach_helpers()
    ctx = _MEGA_CASE["creator_context"]

    prompt = oh.build_outreach_prompt(ctx, tone_override="brief")
    draft = _ask(prompt)
    wc = len(draft.split())

    # Use a lightweight stub metric for recording purposes only
    class _WordCountResult:
        score = 1.0 if wc <= 200 else 0.0
        success = wc <= 200
        reason = f"word count = {wc} (limit = 200)"

    before_case = dict(_MEGA_CASE, id="outreach-03-before")
    _record(before_case, draft, [_WordCountResult()], tag="before")
    print(f"\n[BEFORE] word count = {wc} (limit = 200)")
    assert wc <= 200, f"BEFORE draft exceeds 200-word limit: {wc} words"


@pytest.mark.integration
def test_after_improvement_mega_wordcount() -> None:
    """AFTER: prompt with explicit HARD LIMIT appended.

    Word count is a deterministic property — no LLM judge needed.
    """
    ctx = _MEGA_CASE["creator_context"]

    prompt = _build_prompt_v2_strict_wordcount(ctx, tone_override="brief")
    draft = _ask(prompt)
    wc = len(draft.split())

    class _WordCountResult:
        score = 1.0 if wc <= 200 else 0.0
        success = wc <= 200
        reason = f"word count = {wc} (limit = 200)"

    after_case = dict(_MEGA_CASE, id="outreach-03-after")
    _record(after_case, draft, [_WordCountResult()], tag="after")
    print(f"\n[AFTER]  word count = {wc} (limit = 200)")
    assert wc <= 200, f"AFTER draft exceeds 200-word limit: {wc} words"
