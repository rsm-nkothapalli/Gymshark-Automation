---
name: skill-03-outreach-drafting
description: Draft a personalized outreach message for a shortlisted Gymshark creator. Use after Skill 01 (scoring) and Skill 02 (sentiment check) confirm the creator is worth contacting. Adapts tone, length, and ask to the creator's tier and deal type.
---

# Skill 03 — Personalized Outreach Drafting
**Workflow Phase:** Phase 2 — Creator Outreach
**Data Required:** `data/creators.csv`, `data/crm_records.csv`

---

## Goal
Draft a personalized outreach message for a specific creator. The message must feel hand-written, reference something specific about the creator's content, and propose the right partnership tier. It must not sound templated or generic.

---

## When to Use This Skill
Use this skill when:
- A creator has been shortlisted (GFS ≥ tier minimum from Skill 01) and is ready for first contact
- A partnership manager says: *"Draft an outreach message for [creator name]"*
- Bulk drafting is needed for a cohort of approved creators

---

## Step-by-Step Instructions

### Step 1 — Load creator context
Call `load_creator_context(creator_id)` from `outreach_helpers.py`.  
This returns a merged dict of the creator's row from `creators.csv` + their `crm_records.csv` row (if one exists).

Key fields to extract before writing:
- `name` — their real name (not handle)
- `handle` — YouTube/Instagram handle
- `tier` — determines tone and ask
- `niche` — what they actually post about
- `ai_discovery_notes` — AI's summary of their content style
- `gymshark_brand_fit` — score to confirm they're worth contacting
- `suggested_deal_type` — from CRM (affiliate / seeding / paid / ambassador)
- `proposed_next_step` — from CRM (e.g. "Send gifted product + follow up")
- `outreach_channel` — where to reach them (Instagram DM / Email / YouTube)

### Step 2 — Select tone based on tier

| Tier | Tone | Length | Ask |
|---|---|---|---|
| Nano | Warm, peer-level | 3–4 short paragraphs | Gift product + collab interest |
| Micro | Professional but friendly | 3–4 paragraphs | Affiliate or paid post |
| Mid | Professional | 4 paragraphs | Paid partnership or retainer |
| Macro | Concise, respectful of their time | 3 tight paragraphs | Formal partnership discussion |
| Mega | Brief, pitch-led | 2–3 paragraphs | Direct ask for a call |

### Step 3 — Write the message using this structure

**Paragraph 1 — The specific hook (MOST IMPORTANT)**  
Reference something real and specific from `ai_discovery_notes` or the creator's known content. Do NOT open with "I came across your page" or "We love your content." Instead, name something specific:
- A topic they cover frequently
- Their content style or format
- Their community's energy

**Paragraph 2 — The Gymshark connection**  
Explain why Gymshark is a natural fit for them — not the other way around. Connect their audience and values to Gymshark's brand positioning (performance-first, community-driven, non-intimidating gym culture).

**Paragraph 3 — The ask**  
Based on `suggested_deal_type`:
- **Seeding** → offer to send product, no commitment
- **Affiliate** → mention commission structure, no upfront cost to them
- **Paid** → mention "paid partnership" without quoting figures in first message
- **Ambassador** → reference longer-term relationship, invite a conversation

**Paragraph 4 (optional, nano/micro only) — The close**  
Keep it low pressure. End with an open question or soft CTA, not a deadline.

### Step 4 — Personalization checklist
Before finalizing, confirm:
- [ ] Does the message name something specific about their content? (not just their niche)
- [ ] Is the tone right for their tier?
- [ ] Does it avoid the words: "amazing", "inspiring", "love your content", "huge fan"?
- [ ] Is the ask one clear thing — not multiple asks in one message?
- [ ] Is it under 200 words for macro/mega, under 300 for nano/micro?

If any box is unchecked, revise before outputting.

### Step 5 — Output
Produce the message ready to copy-paste, followed by a brief metadata block:

```
OUTREACH DRAFT — [Creator Name] (@[handle])
Channel: [outreach_channel]
Deal type: [suggested_deal_type]
Word count: [N]
---
[Message body]
---
Human review note: [Any flag — e.g. "brand safety AMBER, confirm before sending"]
```

---

## Edge Cases
- If `ai_discovery_notes` is empty or "N/A", do not fabricate content details — instead write a slightly more general hook and add a review note: *"Transcript data unavailable — recommend human to add specific content reference before sending."*
- If `existing_partner = True`, do not draft a cold outreach — instead draft a renewal/check-in message that acknowledges the existing relationship.
- If `outreach_channel` = Email, add a subject line at the top.
- Never mention competitor brands (Alphalete, Lululemon, YoungLA) in the message, even to compare favorably.
- Never quote pricing or rates in a first-contact message.

---

## What Good vs Bad Looks Like

**BAD outreach:**
> "Hi Sarah! We love your content and think you'd be perfect for Gymshark. We'd love to collaborate! Let us know if you're interested 😊"

**GOOD outreach:**
> "Hi Sarah — I've been watching your push/pull/legs series and the way you break down progressive overload for beginners is exactly the kind of training content Gymshark's community gravitates toward. We work with a lot of coaches who prioritize education over aesthetics, and your approach fits that perfectly. I'd love to send you some kit from our new training line — no commitment, just want you to try it. Would that be something you'd be open to?"
