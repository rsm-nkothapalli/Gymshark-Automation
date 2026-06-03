---
title: "Gymshark AI Influencer Pipeline — Process Explanation"
subtitle: "Milestone 03 · Group 18"
date: "May 2026"
geometry: margin=2.5cm
fontsize: 11pt
linestretch: 1.4
---

## What Changed From the Original Process

Before this pipeline, Gymshark's influencer identification and outreach relied entirely on manual effort — analysts browsing YouTube, evaluating creators by gut feel, writing individual emails from scratch, and tracking responses in spreadsheets. There was no structured scoring, no consistent brand safety check, and no standardized outreach format.

The redesigned pipeline introduces AI at four points: creator scoring, outreach drafting, product brief generation, and campaign analysis. Data collection is now fully automated, producing structured creator records — YouTube stats, VADER comment sentiment, HypeAuditor audience demographics, CRM entries — before any human reviews a creator. The scoring step replaces ad-hoc judgment with a formula-driven Gymshark Fit Score that consistently applies tier thresholds and hard disqualification rules (RED brand safety, competitor loyalty, clickbait). Outreach emails are drafted by an LLM using a RAG-retrieved brand playbook, replacing the blank-page writing task with a review-and-edit task. Campaign performance is calculated automatically rather than assembled manually from platform dashboards.

## Which Steps Should Be Faster or Easier

Creator discovery and enrichment (Phase 0) is now fully automated — what previously took hours of manual YouTube browsing runs in minutes via API. Scoring and ranking (Phase 1) is instant once data exists; the analyst receives an already-ranked, already-filtered leaderboard rather than a raw unsorted list. Outreach drafting (Phase 2) shifts from writing to editing — the analyst reviews a complete, personalized draft rather than composing from scratch, cutting per-creator time significantly. The deal type is also pre-filled from scoring data, so the analyst only needs to confirm or adjust rather than decide from nothing. Product brief generation (Phase 3) eliminates another writing task entirely; the manager reviews rather than authors the brief.

## Which Steps Still Require Human Judgment

AMBER-flagged creators sit in the eligible leaderboard with a warning note — the analyst must read the specific brand safety context and make a call that depends on relationship history and strategic fit, neither of which the AI has access to. The manager approval gates on both outreach and the product brief are genuine judgment checkpoints: tone fit, deal appropriateness, and creator relationship dynamics cannot be evaluated by the model. The renewal decision at the end of Phase 4 is also human — ROI data informs it, but goodwill, long-term partnership value, and audience trajectory are factors the dashboard cannot weigh.

## Which Steps Are Risky If Fully Automated

Outreach approval is the highest-risk step. A poorly worded or factually wrong email sent under the Gymshark brand damages the creator relationship permanently — there is no recall. This step must remain human-gated. Product brief approval carries similar risk: an incorrect promo code or mismatched product line creates fulfilment problems and erodes creator trust before the partnership has started. Creator scoring could technically run fully automated, but removing analyst review would mean AMBER cases and borderline creators get no human consideration, and any systematic error in the scoring formula would propagate unchecked. Campaign renewal decisions should never be fully automated — a low-ROI creator may have strategic or audience value that aggregate numbers do not capture.

## What the AI Coworker Needs From Data, Tools, and Documents

The pipeline depends on several inputs at each stage. For scoring: `creators.csv` containing YouTube stats, sentiment scores, brand safety flags, and tier classification, plus the RAG knowledge base covering tier thresholds, brand guidelines, competitor policy, and audience safety standards. For outreach: creator data merged with `crm_records.csv` (account manager, preferred channel, suggested deal type), and RAG documents covering the outreach playbook, banned phrases, tone guidelines, and deal type definitions. For the product brief: `creators.csv`, HypeAuditor audience demographics (gender split used to select product line), and RAG documents covering the product catalog, brief standards, and affiliate commission structure. For campaign analytics: `campaign_performance.csv` and `existing_partners.csv`. The LLM used throughout is `api-llama-4-scout` via TritonAI. Semantic retrieval uses `api-tgpt-embeddings` to match queries against the knowledge base at runtime.

## What the Final Business Output Is

The pipeline produces three concrete deliverables per creator: a sent outreach email (personalized, brand-compliant, manager-approved), a product brief with recommended product line and unique promo code (for creators who accept the partnership), and a campaign performance entry with ROI, conversion rate, and cost-per-click once the campaign runs. At the portfolio level, the analytics step produces a blended ROI figure, tier and deal-type breakdowns, and a ranked list of top and bottom performers — giving the partnerships team a structured, data-backed basis for budget allocation and creator renewal decisions in the next campaign cycle.
