"""
sentiment_helpers.py — Skill 02: Sentiment & Brand Risk Analysis
Gymshark GenAI Influencer Pipeline · Group 18

CSV columns used: compound_score, negative_creator_flag (Yes/No), purchase_intent (Yes/No)
"""

import csv


def load_sentiment_data(creator_id, filepath="data/comment_sentiment.csv"):
    """Load all sentiment rows for a given creator_id."""
    rows = []
    with open(filepath, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("creator_id") == creator_id:
                rows.append(row)
    return rows


def load_all_sentiment(filepath="data/comment_sentiment.csv"):
    """Load full sentiment CSV as list of dicts."""
    with open(filepath, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


RISK_THRESHOLDS = {
    "high_flagged_pct": 15.0,  # > 15% negative flags → HIGH
    "medium_flagged_pct": 8.0,  # 8–15% → MEDIUM
    "min_comments": 50,  # fewer → UNKNOWN
}


def calculate_sentiment_metrics(rows):
    """
    Given a list of comment rows for one creator, return a metrics dict.
    Reads compound_score and negative_creator_flag columns from the CSV.
    """
    if not rows:
        return None

    total = len(rows)
    labels = [r.get("sentiment_label", "").upper() for r in rows]

    scores = []
    for r in rows:
        try:
            scores.append(float(r.get("compound_score", 0)))
        except ValueError:
            pass

    flagged_rows = [r for r in rows if r.get("negative_creator_flag", "No") == "Yes"]
    intent_rows = [r for r in rows if r.get("purchase_intent", "No") == "Yes"]

    return {
        "total_comments": total,
        "positive_pct": round(labels.count("POSITIVE") / total * 100, 1),
        "negative_pct": round(labels.count("NEGATIVE") / total * 100, 1),
        "neutral_pct": round(labels.count("NEUTRAL") / total * 100, 1),
        "avg_sentiment": round(sum(scores) / len(scores), 3) if scores else None,
        "flagged_count": len(flagged_rows),
        "flagged_pct": round(len(flagged_rows) / total * 100, 1),
        "purchase_intent_count": len(intent_rows),
    }


def assign_risk_level(metrics):
    """
    Returns (risk_level, emoji, reason) based on metrics dict.
    risk_level: 'HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'
    """
    if metrics is None or metrics["total_comments"] < RISK_THRESHOLDS["min_comments"]:
        return "UNKNOWN", "⚪", "Insufficient data — fewer than 50 comments"

    flagged_pct = metrics["flagged_pct"]

    if flagged_pct > RISK_THRESHOLDS["high_flagged_pct"]:
        return "HIGH", "🔴", f"flagged_pct={flagged_pct}% exceeds {RISK_THRESHOLDS['high_flagged_pct']}% threshold"

    if flagged_pct >= RISK_THRESHOLDS["medium_flagged_pct"]:
        return "MEDIUM", "🟡", f"flagged_pct={flagged_pct}% — human review required"

    return "LOW", "🟢", f"flagged_pct={flagged_pct}% — below 8% threshold, safe to proceed"


def get_example_flagged(rows: list[dict], n: int = 3) -> list[str]:
    """Return up to n anonymized examples of flagged comments (first 5 words + [...])."""
    examples = [
        r.get("comment_text", "")
        for r in rows
        if r.get("negative_creator_flag", "No") == "Yes" and r.get("comment_text", "").strip()
    ]
    truncated = []
    for text in examples[:n]:
        words = text.split()
        truncated.append(" ".join(words[:5]) + " [...]" if len(words) > 5 else text)
    return truncated


def print_risk_report(creator_id, rows, creator_name="", handle=""):
    """Print a full brand risk report to stdout."""
    metrics = calculate_sentiment_metrics(rows)

    print(f"\n{'=' * 62}")
    print(f"BRAND RISK ASSESSMENT  |  {creator_name or creator_id}  (@{handle or '?'})")
    print(f"{'=' * 62}")

    if not metrics:
        print("  Status: ⚪ UNKNOWN — no comment data found")
        print("  Action: Expand comment sample, then re-run Skill 02.")
        print(f"{'=' * 62}")
        return

    risk, emoji, reason = assign_risk_level(metrics)

    print(f"  Risk level : {emoji} {risk}")
    print(f"  Reason     : {reason}")
    print(f"  Comments   : {metrics['total_comments']} analysed (need ≥50 for a score)")

    print(f"\n  {'─' * 56}")
    print(f"  SENTIMENT BREAKDOWN")
    print(f"  {'─' * 56}")
    print(f"  {'Positive':14s}  {metrics['positive_pct']:>5.1f}%   viewers approving / enthusiastic")
    print(f"  {'Negative':14s}  {metrics['negative_pct']:>5.1f}%   dissatisfied or critical")
    print(f"  {'Neutral':14s}  {metrics['neutral_pct']:>5.1f}%   factual / mixed / questions")
    avg = metrics.get("avg_sentiment")
    avg_str = f"{avg:.3f}" if avg is not None else "N/A"
    print(f"  {'Avg compound':14s}  {avg_str:>6}   (VADER -1→+1; above 0.05 = positive tone)")

    print(f"\n  {'─' * 56}")
    print(f"  RISK SIGNALS")
    print(f"  {'─' * 56}")
    print(
        f"  {'Flagged comments':22s}  {metrics['flagged_count']:>3} ({metrics['flagged_pct']:>4.1f}%)   "
        f"threshold: <8% safe · >15% HIGH risk"
    )
    print(
        f"  {'Purchase intent':22s}  {metrics['purchase_intent_count']:>3} signal(s)  "
        f"viewers actively asking to buy / asking for links"
    )

    if risk == "HIGH":
        examples = get_example_flagged(rows)
        if examples:
            print(f"\n  Sample flagged comments:")
            for ex in examples:
                print(f'    → "{ex}"')

    print(f"\n  {'─' * 56}")
    print(f"  RECOMMENDATION  &  NEXT STEP")
    print(f"  {'─' * 56}")
    if risk == "HIGH":
        print("  🚫 Do not proceed — brand safety concern detected")
        print("     Next: escalate to brand safety team; exclude from outreach")
    elif risk == "MEDIUM":
        print("  ⚠️  Human review required before outreach")
        print("     Next: review flagged comments at Gate 2; decide individually")
    elif risk == "LOW":
        print("  ✅ Safe to proceed — no brand safety concerns detected")
        print("     Next: auto-approved at Gate 2 → move to outreach drafting")
    else:
        print("  ⚪ Insufficient data — cannot assign a risk level")
        print("     Next: at Gate 2, human decides individually based on public profile")
    print(f"{'=' * 62}")


def print_all_risk_summary(risk_results: dict) -> None:
    """Print a compact table summarising risk levels for all creators."""
    print(f"\n{'=' * 72}")
    print("SKILL 02 — BRAND RISK SUMMARY")
    print(f"{'=' * 72}")
    hdr = f"  {'Name':<28}  {'Risk':<9}  {'#Cmts':>5}  {'Flag%':>5}  {'AvgCmpd':>7}  {'Intent':>6}"
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))

    for result in risk_results.values():
        name = result["name"]
        risk = result["risk_level"]
        emoji = result.get("emoji", "")
        m = result.get("metrics")
        if m:
            total = m["total_comments"]
            flagged_pct = m["flagged_pct"]
            avg = m.get("avg_sentiment")
            avg_str = f"{avg:.3f}" if avg is not None else "N/A"
            intent = m.get("purchase_intent_count", 0)
        else:
            total, flagged_pct, avg_str, intent = 0, 0.0, "N/A", 0
        print(f"  {name:<28}  {emoji} {risk:<7}  {total:>5}  {flagged_pct:>4.1f}%  {avg_str:>7}  {intent:>6}")

    print(f"  {'─' * (len(hdr) - 2)}")
    low = sum(1 for r in risk_results.values() if r["risk_level"] == "LOW")
    med = sum(1 for r in risk_results.values() if r["risk_level"] == "MEDIUM")
    high = sum(1 for r in risk_results.values() if r["risk_level"] == "HIGH")
    unk = sum(1 for r in risk_results.values() if r["risk_level"] == "UNKNOWN")
    print(f"  🟢 LOW: {low}   🟡 MEDIUM: {med}   🔴 HIGH: {high}   ⚪ UNKNOWN: {unk}")
    print(f"{'=' * 72}\n")


# ── Run standalone ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    all_rows = load_all_sentiment()
    creator_ids = list(dict.fromkeys(r["creator_id"] for r in all_rows))
    print(f"Found {len(creator_ids)} creators in comment_sentiment.csv")
    risk_results = {}
    for cid in creator_ids:
        rows = [r for r in all_rows if r["creator_id"] == cid]
        metrics = calculate_sentiment_metrics(rows)
        risk_level, emoji, reason = assign_risk_level(metrics)
        name = rows[0].get("creator_name", cid) if rows else cid
        risk_results[cid] = {
            "name": name,
            "risk_level": risk_level,
            "emoji": emoji,
            "reason": reason,
            "metrics": metrics,
        }
    print_all_risk_summary(risk_results)
    for cid in creator_ids:
        rows = [r for r in all_rows if r["creator_id"] == cid]
        name = rows[0].get("creator_name", cid) if rows else cid
        handle = rows[0].get("youtube_handle", "") if rows else ""
        print_risk_report(cid, rows, creator_name=name, handle=handle)
