# 5. Time, Cost, and Quality Reasoning

This section presents a before/after estimate of how the Gymshark AI Creator Discovery Pipeline improves efficiency across the five key workflow stages. Estimates are based on the pipeline's implemented scripts and simulated data outputs.

---

## Step-by-Step Time Breakdown

| Process Step | Current Time | AI-Supported Time | Why Might Time Change? | Confidence |
|---|---|---|---|---|
| Creator search & shortlisting | 25–40 min | 3–8 min | AI runs YouTube API queries across 10 search terms simultaneously; rule-based pre-filters (clickbait, existing partner, subscriber floor) auto-disqualify ineligible channels | High |
| Transcript & content analysis | 15–25 min | 2–5 min | `collect_creators_gemini.py` scores authenticity, community, and niche signals from transcripts automatically using keyword dictionaries | High |
| Comment sentiment scoring | 10–20 min | 1–3 min | VADER NLP in `collect_comments.py` classifies all comments and flags purchase intent; previously required manual reading | High |
| Fraud & audience quality check | 10–15 min | 1–2 min | `collect_hypeauditor.py` calls HypeAuditor API and auto-flags high fraud-risk creators; no manual lookup needed | Medium |
| CRM record creation | 10–15 min | <1 min | `simulate_crm.py` auto-generates structured records with priority, account manager, and outreach channel assigned | High |
| Human review & final decision | 10–20 min | 15–25 min | Reviewer now sees scored, ranked candidates with reasoning attached — review is more explicit so time may increase slightly | High |

---

## Summary Table

| Metric | Current Process Estimate | AI-Supported Process Estimate | Expected Change |
|---|---|---|---|
| Total time per case | 80–135 min | 22–44 min | ~60–65% faster |
| Human review time | 10–20 min | 15–25 min | May increase — review is now explicit |
| Number of handoffs | 4 | 2 | Fewer: AI handles search to scoring to CRM in one run |
| Rework risk | Medium | Low to medium | Structured scores and flags reduce subjective inconsistency |
| Stakeholder wait time | 2–3 days | Same day | Pipeline runs end-to-end in minutes; output ready immediately |

---

## Cost Estimate

Using a Partnerships Coordinator rate of £30/hour (reasonable for a UK junior partnerships role):

- **Current process:** 107 min average / 60 × £30 = **£53.50 per creator**
- **AI-supported process:** 33 min average / 60 × £30 = **£16.50 per creator**
- **Estimated labour saving: ~£37 per creator**

At 50 creators screened per month, this amounts to roughly **£1,850/month** in labour savings before accounting for API costs (YouTube Data API: free tier; HypeAuditor: ~£0.10–0.50/call).

---

## Quality Measures

The pipeline improves quality on four dimensions:

1. **More consistent scoring** — every creator is evaluated against the same keyword dictionaries and weighted formula (authenticity 30%, comment sentiment 25%, niche 25%, engagement 20%), eliminating reviewer-to-reviewer variation.
2. **Fewer missed red flags** — brand safety, clickbait, and competitor loyalty checks run automatically on every candidate; manual review tends to miss these under time pressure.
3. **Better prioritisation** — CRM records are ranked by brand-fit score with reasoning attached, so account managers review highest-potential creators first.
4. **Purchase intent visibility** — VADER comment classification surfaces buying signals (e.g. "just ordered", "in my cart") that a manual reviewer would rarely quantify.

---

## Face Validity Check

The direction is correct: AI reduces the repetitive data-gathering steps (search, read, score, log) while human review time stays roughly constant — consistent with how AI augmentation typically works in knowledge workflows. A 60–65% total time reduction is plausible given that the bottleneck shifts from manual lookup to structured review.

Two anchors support this:

5. HypeAuditor's 2025 State of Influencer Marketing report notes that manual creator vetting at scale takes 45–90 minutes per creator for mid-sized brand teams; automated enrichment tools reduce initial screening to under 10 minutes.
6. The simulated pipeline data shows `crm_records.csv` producing 8 fully scored, ranked, and CRM-ready records from a single script run — the end-to-end automated portion takes seconds, not hours.

One caveat: human review time may be slightly underestimated in the AI-supported column. Reviewers seeing detailed AI output (scores, flags, reasoning) tend to engage more carefully than when reviewing thin manual notes — this is a quality improvement, but it does add time. A 20–30% total time reduction would still represent a meaningful efficiency gain even under a conservative scenario.
