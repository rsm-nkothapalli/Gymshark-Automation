"""
simulate_outreach_responses.py
------------------------------
Simulate creator responses to Gymshark outreach messages.

Reads creators.csv (outreach_recommended=True) and assigns a yes/no response
based on realistic tier-specific acceptance rates. Uses a fixed random seed so
results are reproducible across pipeline runs.

Response rate assumptions (influencer marketing benchmarks):
  nano   (gift_seeding) — 65%  low barrier, just free product
  micro  (affiliate)    — 50%  commission deal, moderate interest
  mid    (affiliate)    — 40%
  macro  (brand_ambassador) — 30%
  mega   (co_created_collection / brand_ambassador) — 20%

Output: data/outreach_responses.csv
"""

import csv
import os
import random
from datetime import date, timedelta

RESPONSE_RATES = {
    "nano": 0.65,
    "micro": 0.50,
    "mid": 0.40,
    "macro": 0.30,
    "mega": 0.20,
}

SEED = 42
BASE_DATE = date(2026, 5, 20)  # day outreach was sent

_HERE = os.path.dirname(os.path.abspath(__file__))
_CREATORS_PATH = os.path.join(_HERE, "creators.csv")
_OUT_PATH = os.path.join(_HERE, "outreach_responses.csv")


def simulate_responses(
    creators_path: str = _CREATORS_PATH,
    seed: int = SEED,
) -> list[dict]:
    """
    Load creators who were recommended for outreach and simulate yes/no responses.

    Returns a list of response dicts (one per creator).
    """
    rng = random.Random(seed)

    with open(creators_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    eligible = [
        r
        for r in rows
        if r.get("outreach_recommended", "").strip().lower() == "true"
        and r.get("brand_safety", "").strip().upper() != "RED"
        and r.get("clickbait_detected", "").strip().lower() != "true"
        and r.get("competitor_loyalty", "").strip().lower() != "true"
    ]

    results = []
    for r in eligible:
        tier = r.get("tier", "nano").lower().strip()
        rate = RESPONSE_RATES.get(tier, 0.40)
        responded_yes = rng.random() < rate

        # Responders reply within 1–7 days; non-responders show no reply date
        if responded_yes:
            days_later = rng.randint(1, 7)
            response_date = (BASE_DATE + timedelta(days=days_later)).isoformat()
            notes = _response_note(tier, r.get("suggested_deal_type", ""))
        else:
            response_date = ""
            notes = "No reply within 14-day window"

        results.append(
            {
                "creator_id": r["creator_id"],
                "name": r["name"],
                "tier": tier,
                "deal_type": r.get("suggested_deal_type", ""),
                "outreach_sent_date": BASE_DATE.isoformat(),
                "responded_yes": str(responded_yes),
                "response_date": response_date,
                "response_notes": notes,
            }
        )

    return results


def _response_note(tier: str, deal_type: str) -> str:
    notes = {
        "nano": "Excited about the gifted product — confirmed delivery address",
        "micro": "Interested in affiliate terms — requested commission rate details",
        "mid": "Requested brand deck and exclusivity terms before committing",
        "macro": "Passed to legal for contract review",
        "mega": "Initial interest — flagged for senior partnership team follow-up",
    }
    return notes.get(tier, "Responded positively")


def write_responses(
    creators_path: str = _CREATORS_PATH,
    out_path: str = _OUT_PATH,
    seed: int = SEED,
) -> list[dict]:
    """Simulate responses and write to CSV. Returns the list of response dicts."""
    results = simulate_responses(creators_path, seed)

    if not results:
        print("No eligible creators found — nothing to write.")
        return results

    fieldnames = list(results[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    yes_count = sum(1 for r in results if r["responded_yes"] == "True")
    print(f"Simulated {len(results)} outreach responses → {out_path}")
    print(f"  YES: {yes_count}  |  NO: {len(results) - yes_count}")
    for r in results:
        status = "✅ YES" if r["responded_yes"] == "True" else "❌ NO "
        print(f"  {status}  {r['name']} ({r['tier']}) — {r['deal_type']}")

    return results


if __name__ == "__main__":
    write_responses()
