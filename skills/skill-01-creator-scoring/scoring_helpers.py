"""
scoring_helpers.py — Skill 01: Creator Scoring & Shortlisting
--------------------------------------------------------------
Pure Python helpers that read data/creators.csv, apply tier-aware
minimum thresholds, disqualify ineligible creators, and return a
ranked shortlist with per-creator recommendations.

Functions:
  load_creators(path)          — Load creators.csv → list[dict]
  get_tier_threshold(tier)     — Min GFS score for a tier
  is_disqualified(creator)     — True if any hard disqualifier is set
  get_recommendation(creator)  — "Outreach now" / borderline / do not recommend label
  shortlist_creators(path)     — Main entry point: returns (eligible, ineligible)
"""

import csv
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# TIER THRESHOLDS  (gymshark_brand_fit score, 1–10 scale)
# ---------------------------------------------------------------------------

TIER_THRESHOLDS: dict[str, float] = {
    "nano": 5.0,
    "micro": 5.5,
    "mid": 6.0,
    "macro": 6.5,
    "mega": 7.5,
}

BORDERLINE_MARGIN = 0.5  # within this below threshold → "FLAG: borderline"

DEFAULT_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "creators.csv")
DEFAULT_AFFILIATES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "gymshark_creators_affiliates.csv"
)


# ---------------------------------------------------------------------------
# LOAD
# ---------------------------------------------------------------------------


def load_creators(path: str = DEFAULT_DATA_PATH) -> list[dict]:
    """
    Load creators.csv and return all rows as a list of dicts.

    Coerces numeric columns (gymshark_brand_fit, authenticity_score,
    community_score, niche_alignment_score, production_quality, subscribers)
    to float/int so callers can compare them without casting.

    Raises FileNotFoundError if the path does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"creators.csv not found at {path}. Run data/collect_creators_gemin_2i.py first.")

    creators = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # Coerce numeric fields
            for float_col in (
                "gymshark_brand_fit",
                "authenticity_score",
                "niche_score",
                "engagement_score",
            ):
                try:
                    row[float_col] = float(row[float_col])
                except (ValueError, KeyError):
                    row[float_col] = 0.0

            for int_col in ("subscribers", "rank"):
                try:
                    row[int_col] = int(row[int_col])
                except (ValueError, KeyError):
                    row[int_col] = 0

            # Coerce boolean-like string columns
            for bool_col in (
                "clickbait_detected",
                "competitor_loyalty",
                "existing_partner",
                "outreach_recommended",
                "transcript_available",
            ):
                if bool_col in row:
                    row[bool_col] = row[bool_col].strip().lower() in ("true", "yes", "1")

            creators.append(row)

    return creators


def load_affiliates(path: str = DEFAULT_AFFILIATES_PATH) -> set[str]:
    """
    Load gymshark_creators_affiliates.csv and return a set of lowercase
    YouTube handles (without @) for fast membership testing.
    Returns an empty set if the file doesn't exist.
    """
    if not os.path.exists(path):
        return set()
    handles: set[str] = set()
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get("YouTube Handle", "").strip().lstrip("@").lower()
            if raw:
                handles.add(raw)
    return handles


# ---------------------------------------------------------------------------
# THRESHOLD & RECOMMENDATION LOGIC
# ---------------------------------------------------------------------------


def get_tier_threshold(tier: str) -> float:
    """
    Return the minimum gymshark_brand_fit score required for a given tier.

    Falls back to the micro threshold (5.5) for unknown tier values.
    """
    return TIER_THRESHOLDS.get(tier.strip().lower(), 5.5)


def is_disqualified(creator: dict) -> tuple[bool, str]:
    """
    Check whether a creator has any hard disqualifier.

    Disqualifiers (any one is sufficient):
      - brand_safety == "RED"
      - clickbait_detected == True
      - competitor_loyalty == True
      - outreach_recommended == False

    Returns (True, reason_string) if disqualified, else (False, "").
    """
    if creator.get("brand_safety", "").upper() == "RED":
        return True, "brand_safety RED"
    if creator.get("clickbait_detected") is True:
        return True, "clickbait_detected"
    if creator.get("competitor_loyalty") is True:
        return True, "competitor_loyalty"
    if creator.get("outreach_recommended") is False:
        return True, "outreach_recommended=False"
    return False, ""


def get_recommendation(creator: dict) -> str:
    """
    Return a recommendation label for an eligible (non-disqualified) creator.

    Labels:
      "Outreach now"        — GFS meets or exceeds tier minimum
      "FLAG: borderline"    — GFS is within 0.5 below tier minimum
      "Do not recommend"    — GFS is more than 0.5 below tier minimum

    Additional flags appended (does not change core recommendation):
      "FLAG: brand safety AMBER — human content review needed"
      "FLAG: existing partner — check renewal status"
    """
    gfs = creator.get("gymshark_brand_fit", 0.0)
    tier = creator.get("tier", "micro")
    threshold = get_tier_threshold(tier)

    if gfs >= threshold:
        label = f"Outreach now (clears {tier} min {threshold:.1f})"
    elif gfs >= threshold - BORDERLINE_MARGIN:
        label = f"FLAG: borderline (needs {threshold:.1f} for {tier})"
    else:
        label = f"Do not recommend (needs {threshold:.1f} for {tier}, gap {threshold - gfs:.1f})"

    if creator.get("brand_safety", "").upper() == "AMBER":
        notes = creator.get("brand_safety_notes", "").strip()
        amber_flag = "FLAG: brand safety AMBER"
        if notes and notes.lower() not in ("none", "no safety concerns", ""):
            amber_flag += f" (flagged: {notes})"
        amber_flag += " — human review needed"
        label += f" | {amber_flag}"
    if creator.get("existing_partner") is True:
        label += " | FLAG: existing partner — check renewal status"

    return label


# ---------------------------------------------------------------------------
# MAIN ENTRY POINT
# ---------------------------------------------------------------------------


def shortlist_creators(
    path: str = DEFAULT_DATA_PATH,
    affiliates_path: str = DEFAULT_AFFILIATES_PATH,
) -> tuple[list[dict], list[dict]]:
    """
    Load creators.csv, separate ineligible creators, rank eligible ones,
    and attach a recommendation to each.

    Creators whose YouTube handle appears in gymshark_creators_affiliates.csv
    are excluded — they are already Gymshark partners and not discovery targets.

    Returns
    -------
    eligible : list[dict]
        Creators that passed all hard disqualifiers, sorted by
        gymshark_brand_fit descending. Each dict has an added
        "recommendation" key.
    ineligible : list[dict]
        Creators that failed at least one hard disqualifier. Each dict
        has an added "disqualification_reason" key.
    """
    creators = load_creators(path)
    affiliate_handles = load_affiliates(affiliates_path)
    eligible = []
    ineligible = []

    for creator in creators:
        # Exclude known Gymshark affiliates — already partnered, not new prospects
        handle = creator.get("youtube_handle", "").lstrip("@").lower()
        if handle and handle in affiliate_handles:
            creator["disqualification_reason"] = "gymshark_affiliate"
            ineligible.append(creator)
            continue

        disq, reason = is_disqualified(creator)
        if disq:
            creator["disqualification_reason"] = reason
            ineligible.append(creator)
        else:
            creator["recommendation"] = get_recommendation(creator)
            eligible.append(creator)

    # Sort eligible by GFS descending; break ties by authenticity_score
    eligible.sort(
        key=lambda c: (c["gymshark_brand_fit"], c.get("authenticity_score", 0)),
        reverse=True,
    )

    return eligible, ineligible


# ---------------------------------------------------------------------------
# FORMATTING HELPERS (used by Skill 01 SKILL.md output step)
# ---------------------------------------------------------------------------


def format_shortlist_table(eligible: list[dict]) -> str:
    """
    Return a plain-text ranked table of eligible creators.

    Columns: # | Name | Tier | GFS | Auth | Niche | Comm | Recommendation
    """
    if not eligible:
        return "No eligible creators found."

    header = f"  {'#':<4} {'Name':<26} {'Tier':<6} {'GFS':>4} {'Auth':>4} {'Niche':>5} {'Eng':>4}  Recommendation"
    separator = "  " + "-" * 86
    rows = []
    for i, c in enumerate(eligible, 1):
        rows.append(
            f"  {i:<4} {c.get('name', ''):<26} {c.get('tier', ''):<6} "
            f"{c.get('gymshark_brand_fit', 0):>4.1f} "
            f"{c.get('authenticity_score', 0):>4.0f} "
            f"{c.get('niche_score', 0):>5.0f} "
            f"{c.get('engagement_score', 0):>4.0f}  "
            f"{c.get('recommendation', '')}"
        )

    return "\n".join([header, separator] + rows)


def format_ineligible_list(ineligible: list[dict]) -> str:
    """Return a plain-text list of disqualified creators with reasons."""
    if not ineligible:
        return "None."
    lines = [
        f"  ✗ {c.get('name', c.get('creator_id', '?'))} — {c.get('disqualification_reason', '')}" for c in ineligible
    ]
    return "\n".join(lines)
