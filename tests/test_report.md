# Section 6 — AI Performance Test Report

**Project**: Gymshark Influencer Pipeline · Group 18 · Milestone 04
**Run date**: 2026-06-02
**Test file**: `tests/test_ai_performance.py`
**Judge model**: `api-gpt-oss-120b` via TritonAI
**Workflow model**: `api-llama-4-scout` via TritonAI

---

## Results Table

Each row is one test case run end-to-end: a real LLM call, scored by a second LLM acting as judge.

| Input | AI Answer (preview) | Evidence Check (Faithfulness) | Question Check (Answer Relevancy) | Quality Check (GEval) | Face Validity Check (GEval) | Pass/Fail |
|-------|---------------------|-------------------------------|-----------------------------------|-----------------------|----------------------------|-----------|
| outreach-01: Nano yoga creator, gift seeding, warm tone | "Hi Isabelle, We really enjoy your… it feels like you're really speaking to your practice family…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | −0.40 ✗ Sycophantic opener flagged | **FAIL** |
| outreach-02: Micro fitness creator, affiliate deal, workout vlog | "Hi Will, Your no-cuts training footage is the kind of content that actually shows what hard work looks like…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| outreach-03: Mega bodybuilding creator, brand ambassador (FC-04) | "Hi Chris, Your structured gear breakdowns set a high standard…" (64 words) | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| outreach-04: Nano strength creator, banned phrase check (FC-02) | "Hi Sophie, The consistency in your lifting content is clear…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| outreach-05: Micro HIIT creator, no internal metric leakage (FC-03) | "Hi Kayla, Your try-on approach — showing different sizes and being honest about fit — is exactly the kind of content…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| outreach-06: Nano creator, minimal context, no signals (FC-05) | "Hi Jordan, Your functional fitness content stands out for how practical it is…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| outreach-07: Micro creator, negative signals / competitor history (FC-07) | "Hi Jenni, Your multi-session approach to testing gear is something we respect…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| brand-fit-01: HIGH-GFS, GREEN safety, LOW risk | "Whitney Simmons has a strong brand fit with Gymshark, driven by her authentic 8/10 score…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| brand-fit-02: AMBER safety, HIGH risk creator (FC-06) | "Marcus Reed's brand fit is cautious — a gift-seeding approach may be suitable, though…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | −0.30 ✗ No clear hold/escalate; unsupported claim | **FAIL** |
| brand-fit-03: Minimal-info creator, no-hallucination check (FC-01) | "Alex Rivera shows moderate brand fit based on a 7.0 GFS…" | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | +1.00 ✓ | **PASS** |
| brief-01: Nano yoga creator, gift seeding, ADAPT line | All 5 sections present; CONTENT FORMAT suggests studio/flow video format; relaxed gift-seeding tone | +1.00 ✓ | +1.00 ✓ | +0.70 ✓ | +0.90 ✓ | **PASS** |
| brief-02: Micro strength creator, affiliate deal, LIFTING line (FC-05) | All 5 sections; MUST INCLUDE references affiliate link; strength-specific language | +1.00 ✓ | +1.00 ✓ | +0.80 ✓ | −0.40 ✗ Promo code not referenced; deal-type tone mismatch | **FAIL** |
| brief-03: Minimal-context creator, no-hallucination check (FC-01) | All 5 sections; TRAINING line; no invented audience traits | +1.00 ✓ | +1.00 ✓ | −0.30 ✗ KEY MESSAGE generic — not specific to functional fitness | +0.60 ✓ | **FAIL** |

**Summary**: 9/13 passed · 4/13 failed · All failures on Quality or Face Validity; Faithfulness and Answer Relevancy passed in every case

---

## Before / After Improvement Test

**Weakness identified**: FC-04 — the mega-tier word-count instruction is soft natural language ("Max 200 words"), not enforced.

**Change made**: A `HARD LIMIT` line was appended to the prompt in `_build_prompt_v2_strict_wordcount()`:
> `HARD LIMIT — COUNT YOUR WORDS: Your entire response must be 200 words or fewer. If you reach 200 words, stop. Do not exceed this under any circumstances.`

**Results**:

| Version | Word count | Result |
|---------|-----------|--------|
| BEFORE (standard prompt) | 65 words | PASS — already under 200 |
| AFTER (strict HARD LIMIT) | 75 words | PASS — still under 200 |

**Finding**: FC-04 did not manifest in testing. For the mega-tier creator, the model naturally produced a 64–75 word email — well inside the 200-word limit without the hard constraint. The before/after test confirmed that adding the explicit limit had no measurable effect, because the model was already complying.

This is a useful result: the anticipated failure (word count violation) is lower risk than expected for the brief/direct tone. The hard-limit instruction may still be worth keeping as a guardrail for edge cases, but it is not addressing an active problem in the current dataset.

---

## Failure Pattern Summary

### Pattern 1: Tone sycophancy slips past the phrase filter

**What happened**: Case `outreach-01-nano-yoga` failed Face Validity (score 0.40). The draft passed every structural check — correct greeting, correct offer, no banned phrases, under word count — but opened with: *"We really enjoy your content… it feels like you're really speaking to your practice family."* The judge flagged this as a sycophantic opener despite it not triggering any keyword in the `BANNED_PHRASES` list.

**Why it happened**: The prompt rule says "Do NOT use: amazing, inspiring, love your content…" — a literal phrase blacklist. The LLM learned to avoid those exact words but found semantically equivalent praise. The banned-phrase filter is brittle: it prevents specific patterns but not the underlying sycophantic intent.

**What would fix it**: Replace the phrase blacklist with a principle-based instruction — e.g. *"Do NOT open with any statement of admiration, enthusiasm, or praise about the creator. The first observation must be factual and specific, not evaluative."* This shifts the rule from token-matching to intent.

---

### Pattern 2: HIGH-risk analysis lacks a clear directive

**What happened**: Case `brand-fit-02-high-risk` failed Face Validity (score 0.30). The analysis acknowledged the HIGH risk and AMBER safety signals but produced soft language: *"a cautious gift-seeding approach may be suitable, though…"* The judge noted there was no clear proceed / hold / escalate decision and an unsupported content-style claim was inserted.

**Why it happened**: The brand-fit prompt asks the LLM to *"write 3–4 sentences covering risks and deal type"* without specifying that HIGH risk must trigger a specific output format. The model smooths over risk signals by default — it wants to be helpful and constructive, so it hedges rather than firmly recommends "do not proceed."

**What would fix it**: Add a conditional instruction: *"If risk_level is HIGH or brand_safety is not GREEN, your final sentence must begin with: 'Recommendation: Do not proceed without human review.' Do not soften this to a suggestion."*

---

### Pattern 3: Face Validity is the discriminating check — the others are too easy

**What happened**: All 10 cases scored 1.00 on Faithfulness and 1.00 on Answer Relevancy. These metrics are effectively always passing because the workflow model (llama-4-scout) does not hallucinate claims and does stay on topic. Only Face Validity, which requires business judgment, found the real weaknesses.

**Why it happened**: Faithfulness measures whether claims are traceable to the retrieval context. Because the outreach prompt explicitly instructs "do not reference brand safety, GFS scores, or internal metrics," the model omits those, so every claim in the draft *is* traceable to something in context. AnswerRelevancy measures whether the output addresses the task — and drafting an outreach email always addresses the outreach task. Neither check is sensitive enough to catch subtle quality issues like tone register or missing risk directives.

**What would fix it**: Two adjustments: (1) lower the thresholds for Faithfulness and AnswerRelevancy to 0.5 so they serve as floors rather than active filters; (2) add a second GEval check targeting business-specific rules such as tone register, risk language, and format compliance — things that require domain knowledge to evaluate. The current split of one Quality check and one Face Validity check combines too many concerns in a single criterion.

---

### Pattern 4: Product brief KEY MESSAGE defaults to generic fitness language

**What happened**: Cases `brief-02-strength-affiliate` and `brief-03-no-hallucination` both failed on at least one check. In `brief-02`, the Face Validity judge (score 0.40) found the brief did not reference the affiliate promo code in MUST INCLUDE and the overall tone did not clearly distinguish gift seeding from affiliate. In `brief-03`, the Quality check (score 0.30) found the KEY MESSAGE was generic — *"experience the best in athletic wear"* — with no reference to functional fitness despite the niche being explicitly provided.

**Why it happened**: The brief prompt asks for niche-specific language but does not enforce it structurally. The LLM defaults to brand-level language ("experience Gymshark gear") when the niche is abstract (e.g., "Functional Fitness") rather than specific (e.g., "Yoga" or "Powerlifting"). For affiliate vs. gift seeding, the deal-type note in the prompt is one sentence and is easily deprioritized when the model is generating the 5-section format.

**What would fix it**: Two targeted additions: (1) require KEY MESSAGE to use the creator's niche as a noun phrase — e.g., *"KEY MESSAGE must mention {niche} directly, not generic fitness language"*; (2) add a conditional MUST INCLUDE rule: *"If deal_type is affiliate, MUST INCLUDE must reference 'promo code' or 'affiliate link' explicitly."*

---

## Notes on Test Methodology

- **Judge model noise**: Individual GEval scores fluctuate between runs (LLM temperature 0.0 reduces but doesn't eliminate variance). Trends across 8–12 cases are more informative than any single score. The two consistent failures were observed across multiple runs.
- **Test completeness**: These 10 cases cover outreach drafting and brand-fit analysis. Product brief generation (Skill-05) was not tested in this suite; it is the next highest-risk LLM output.
- **When to rerun**: This suite should be rerun whenever `outreach_helpers.py`, `ui/api/main.py` brand-fit prompt, or the RAG knowledge base changes.
