---
title: Affiliate Commission Structure & Tracking Setup
category: Finance
last_reviewed: 2026-05-01
audience: partnerships, finance
---

# Affiliate Commission Structure & Tracking Setup

## Commission Rate

- **Standard affiliate rate:** 12% of all revenue directly attributed to the creator's promo code or UTM link
- **Ambassador rate:** Negotiated per contract — typically 8–15% depending on tier and exclusivity
- **Trial period rate (first 90 days):** 12% standard — no reduced trial rate

## Promo Code Format

All affiliate promo codes follow this format:

```
GS + [first 4 letters of creator name, uppercase] + [2 random digits]
```

Examples:
- Creator: Naomi Williams → Code: GSNAOM47
- Creator: Alex Chen → Code: GSALEXC83
- Creator: Jo → Code: GSJOXXX12 (short names padded with X)

Codes must be:
- Unique — check against existing codes before assigning
- Valid for 12 months from campaign start date
- Single-use per customer (tracked at checkout)

## Tracking Setup

Every affiliate deal requires BOTH:
1. **Promo code** — applied at checkout, tracked in Shopify
2. **UTM link** — unique URL with `utm_source=creator_name&utm_medium=affiliate&utm_campaign=campaign_id`

Having only one of the two is insufficient — some customers use the link without the code and vice versa. Attribution requires both to be set up.

## Payment Schedule

- Commissions calculated monthly (1st of each month)
- Payment processed within 15 business days
- Minimum payout threshold: £50 (commissions below £50 roll to next month)
- Payment method: Bank transfer or PayPal (creator's choice at onboarding)

## Attribution Window

- **Cookie window:** 30 days from link click
- **Promo code window:** Valid for 12 months (no attribution window — any use of code is attributed)
- **Last-click model:** If a customer uses both a UTM link and another channel, the promo code takes precedence

## What Counts as Attributed Revenue

- Full order value at checkout when promo code is applied
- Full order value when UTM link led to purchase within 30-day window
- Excludes: shipping, taxes, refunded orders

## Dispute Resolution

If a creator disputes their commission report:
1. Creator raises dispute in writing within 30 days of statement
2. Finance team reviews Shopify transaction logs within 5 business days
3. If discrepancy confirmed, correction applied to following month's payment
