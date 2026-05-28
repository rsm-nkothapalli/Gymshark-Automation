"""
pipeline_helpers.py — Skill 06: AI Workflow Orchestrator
---------------------------------------------------------
Chains Skill 01 → 03 → 05 into a pipeline with three human-in-the-loop
gates that display decisions on screen and wait for input before continuing.

Brand risk is evaluated by the LLM during creator scoring (Step 1) and
stored as audience_brand_risk in creators.csv — no separate Skill 02 step needed.

Human Gates
-----------
  Gate 1 (after scoring)     — review shortlist, optionally exclude creators
  Gate 2 (after drafts)      — review each outreach draft before sending
  Gate 3 (after outreach)    — record which creators responded yes → product brief

Intermediate outputs written to outputs/pipeline/:
  01_shortlisted.json        — creators passing Skill 01 thresholds
  04_outreach_drafts/        — one .txt per approved creator (Skill 03)
  05_pipeline_summary.json   — full run summary
  06_product_briefs/         — one .txt per creator who said yes (Skill 05)

Entry point:
  run_pipeline(human_review=True)  — interactive mode (pauses at each gate)
  run_pipeline(human_review=False) — automated mode (no prompts, existing behaviour)
  run_pipeline(draft_outreach=False) — dry run, stops after Step 1

CLI:
  uv run python skills/skills/skill-06-pipeline-workflow/pipeline_helpers.py
"""

import importlib.util
import json
import os
import sys
from datetime import datetime

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------

_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SKILLS_DIR = os.path.join(_PROJECT_ROOT, "skills")

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _load_module(module_name: str, rel_path: str):
    """Load a helper module from a path that may contain hyphens."""
    abs_path = os.path.join(_SKILLS_DIR, rel_path)
    spec = importlib.util.spec_from_file_location(module_name, abs_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_scoring = _load_module("scoring_helpers", "skill-01-creator-scoring/scoring_helpers.py")
_outreach = _load_module("outreach_helpers", "skill-03-outreach-drafting/outreach_helpers.py")
_brief = _load_module("brief_helpers", "skill-05-product-brief/brief_helpers.py")

_DEFAULT_CREATORS = os.path.join(_PROJECT_ROOT, "data", "creators.csv")
_DEFAULT_CRM = os.path.join(_PROJECT_ROOT, "data", "crm_records.csv")
_DEFAULT_INTAKE = os.path.join(_PROJECT_ROOT, "data", "hypeauditor_intake_log.csv")
_DEFAULT_RESPONSES = os.path.join(_PROJECT_ROOT, "data", "outreach_responses.csv")
_DEFAULT_OUTPUT = os.path.join(_PROJECT_ROOT, "outputs", "pipeline")


# ---------------------------------------------------------------------------
# INTERNAL HELPERS
# ---------------------------------------------------------------------------


def _write_json(data: dict | list, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


def _human_prompt(question: str) -> str:
    """Thin wrapper around input() — mockable in tests."""
    return input(question).strip()


def load_simulated_responses(responses_path: str, approved_ids: list[str]) -> list[str]:
    """
    Read outreach_responses.csv and return creator_ids who said yes,
    filtered to those in approved_ids (creators who actually received a draft).

    Returns an empty list if the file is missing — pipeline skips briefs gracefully.
    """
    import csv

    if not os.path.exists(responses_path):
        return []

    yes_ids = []
    with open(responses_path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (
                row.get("responded_yes", "").strip().lower() == "true"
                and row.get("creator_id", "").strip() in approved_ids
            ):
                yes_ids.append(row["creator_id"].strip())
    return yes_ids


def _draft_message_llm(context: dict, model: str = "api-llama-4-scout") -> str:
    """Draft a personalized outreach message via LLM; falls back to template."""
    from utils.connect import ask

    prompt = _outreach.build_outreach_prompt(context)

    try:
        return ask(prompt, model=model)
    except Exception:
        name = context.get("name", "Creator")
        niche = context.get("niche", "fitness")
        deal = context.get("suggested_deal_type", "partnership")
        return (
            f"Hi {name},\n\nI've been following your {niche} content and "
            f"think there's a natural fit with what we're building at Gymshark. "
            f"We'd love to explore a {deal} — would you be open to a quick chat?\n\n"
            f"Best,\nGymshark Partnerships"
        )


# ---------------------------------------------------------------------------
# STEP 1 — SCORING (Skill 01)
# ---------------------------------------------------------------------------


def run_scoring_step(
    creators_path: str = _DEFAULT_CREATORS,
    output_dir: str = _DEFAULT_OUTPUT,
) -> list[dict]:
    """Score creators, write 01_shortlisted.json, return eligible list."""
    eligible, ineligible = _scoring.shortlist_creators(creators_path)
    payload = {
        "step": "01_scoring",
        "run_at": datetime.now().isoformat(),
        "eligible_count": len(eligible),
        "ineligible_count": len(ineligible),
        "eligible": [
            {
                "creator_id": c["creator_id"],
                "name": c["name"],
                "tier": c["tier"],
                "gymshark_brand_fit": c["gymshark_brand_fit"],
                "audience_brand_risk": c.get("audience_brand_risk", "MEDIUM"),
                "recommendation": c.get("recommendation", ""),
            }
            for c in eligible
        ],
        "ineligible": [
            {
                "creator_id": c["creator_id"],
                "name": c["name"],
                "reason": c.get("disqualification_reason", ""),
            }
            for c in ineligible
        ],
    }
    _write_json(payload, os.path.join(output_dir, "01_shortlisted.json"))

    print(f"\n{'=' * 70}")
    print("STEP 1 — CREATOR SCORING  (Skill 01)")
    print(f"{'=' * 70}")
    print()
    print(_scoring.format_shortlist_table(eligible))
    if ineligible:
        print(f"\n  DISQUALIFIED ({len(ineligible)}):")
        print(_scoring.format_ineligible_list(ineligible))
    print(f"\n  → {len(eligible)} eligible, {len(ineligible)} disqualified.\n")
    return eligible


# ---------------------------------------------------------------------------
# STEP 2 — OUTREACH DRAFTING (Skill 03)
# ---------------------------------------------------------------------------


def run_outreach_step(
    approved: list[dict],
    creators_path: str = _DEFAULT_CREATORS,
    crm_path: str = _DEFAULT_CRM,
    output_dir: str = _DEFAULT_OUTPUT,
    model: str = "api-llama-4-scout",
) -> dict:
    """Draft outreach for all approved creators. Write to 04_outreach_drafts/."""
    drafts_dir = os.path.join(output_dir, "04_outreach_drafts")
    os.makedirs(drafts_dir, exist_ok=True)
    results = {}
    for entry in approved:
        cid = entry["creator_id"]
        try:
            context = _outreach.load_creator_context(cid, creators_path, crm_path)
            message = _draft_message_llm(context, model=model)
            issues = _outreach.validate_message(message, context.get("tier", "micro"))
            review_note = "; ".join(issues) if issues else ""
            formatted = _outreach.format_outreach_output(context, message, review_note)
            out_path = os.path.join(drafts_dir, f"{cid}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(formatted)
            results[cid] = {
                "name": entry["name"],
                "file": out_path,
                "validation_issues": issues,
                "status": "drafted",
            }
            status = "⚠ issues" if issues else "✓"
            print(f"[Step 2] {entry['name']}: {status}")
        except Exception as exc:
            results[cid] = {"name": entry["name"], "status": "error", "error": str(exc)}
            print(f"[Step 2] {entry['name']}: ERROR — {exc}")
    return results


# ---------------------------------------------------------------------------
# STEP 3 — PRODUCT BRIEFS (Skill 05)
# ---------------------------------------------------------------------------


def run_brief_step(
    yes_ids: list[str],
    creators_path: str = _DEFAULT_CREATORS,
    crm_path: str = _DEFAULT_CRM,
    output_dir: str = _DEFAULT_OUTPUT,
    intake_path: str = _DEFAULT_INTAKE,
) -> dict:
    """
    Generate product briefs for creators who said yes to outreach (Skill 05).
    Writes to 06_product_briefs/{creator_id}.txt.
    Returns {creator_id: {name, file, product_line, deal_type, status}} dict.
    """
    briefs_dir = os.path.join(output_dir, "06_product_briefs")
    os.makedirs(briefs_dir, exist_ok=True)
    results = {}

    for cid in yes_ids:
        try:
            data = _brief.load_creator_brief_data(cid, creators_path, crm_path, intake_path)
            if data is None:
                results[cid] = {"name": cid, "status": "error", "error": "Creator not found"}
                print(f"[Step 3] {cid}: ERROR — not found")
                continue

            if data["deal_type"] not in ("gift_seeding", "affiliate"):
                results[cid] = {
                    "name": data["creator_name"],
                    "status": "skipped",
                    "reason": f"{data['deal_type']} deals use a separate brief process",
                }
                print(f"[Step 3] {data['creator_name']}: skipped ({data['deal_type']})")
                continue

            product_line = _brief.recommend_product_line(data["niche"], data["gender_male_pct"])
            line_info = _brief.PRODUCT_LINES[product_line]
            brief_text = _brief.generate_creative_brief(data, product_line)

            lines = [
                f"PRODUCT BRIEF — {data['creator_name']}",
                "=" * 55,
                f"Deal type:    {data['deal_type'].replace('_', ' ').upper()}",
                f"Tier:         {data['tier'].capitalize()}",
                f"Niche:        {data['niche']}",
                "",
                "PRODUCT RECOMMENDATION",
                f"  Line:   {product_line.upper()} — {line_info['description']}",
                f"  Send:   {', '.join(line_info['example_items'])}",
            ]
            if data["deal_type"] == "affiliate":
                promo = _brief.generate_promo_code(data["creator_name"])
                lines += [
                    "",
                    "AFFILIATE DETAILS",
                    f"  Promo code:  {promo}",
                    "  Commission:  12% of attributed revenue",
                    "  Tracking:    UTM link + promo code redemptions",
                ]
            lines += ["", "CREATIVE BRIEF", brief_text]

            brief_text_block = "\n".join(lines)

            out_path = os.path.join(briefs_dir, f"{cid}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(brief_text_block)

            print(f"\n{'─' * 55}")
            print(brief_text_block)
            print(f"{'─' * 55}")
            print(f"  Saved → {out_path}\n")

            results[cid] = {
                "name": data["creator_name"],
                "file": out_path,
                "product_line": product_line,
                "deal_type": data["deal_type"],
                "status": "generated",
            }

        except Exception as exc:
            results[cid] = {"name": cid, "status": "error", "error": str(exc)}
            print(f"[Step 3] {cid}: ERROR — {exc}")

    return results


# ---------------------------------------------------------------------------
# HUMAN GATE 1 — After scoring: review shortlist
# ---------------------------------------------------------------------------


def _build_gate1_reasoning(creator: dict) -> str:
    """One-line explanation of what drives the Gate 1 decision for a creator."""
    gfs = float(creator.get("gymshark_brand_fit", 0))
    tier = creator.get("tier", "nano")
    threshold = _scoring.get_tier_threshold(tier)
    auth = float(creator.get("authenticity_score", 0))
    niche = float(creator.get("niche_score", 0))
    signals_pos = creator.get("signals_authentic_pos", "").strip().lower()
    has_transcript_signals = signals_pos not in ("", "none")

    parts = []

    if gfs >= threshold:
        if auth >= 8:
            parts.append(f"auth {auth:.0f}/10 (exceptional)")
        elif auth >= 7:
            parts.append(f"auth {auth:.0f}/10 (strong)")
        else:
            parts.append(f"auth {auth:.0f}/10")
        if niche >= 8:
            parts.append(f"niche fit {niche:.0f}/10")
        if has_transcript_signals:
            parts.append(f'transcript verified: "{creator.get("signals_authentic_pos", "").strip()}"')
        else:
            parts.append("scored from channel stats — no transcript signals")
    else:
        gap = threshold - gfs
        parts.append(f"GFS {gfs:.1f} vs {tier} min {threshold:.1f} — {gap:.1f} pts short")
        if not has_transcript_signals:
            parts.append("no transcript authenticity signals found")
        if auth < 6:
            parts.append(f"auth only {auth:.0f}/10")

    return " · ".join(parts)


def human_gate_scoring(eligible: list[dict]) -> list[dict]:
    """
    Show the scoring shortlist with column headers and per-creator reasoning.
    Human can exclude any creators before outreach drafting.
    Returns the filtered list to proceed with.
    """
    print("\n" + "=" * 70)
    print("HUMAN DECISION — Gate 1: Review Shortlist")
    print("=" * 70)
    print(f"\n{len(eligible)} creators passed scoring:\n")

    hdr = f"  {'#':>2}  {'Name':<28}  {'Tier':<6}  {'GFS':>4}  {'Auth':>4}  {'Niche':>5}  {'Risk':<7}  Decision"
    print(hdr)
    print("  " + "─" * (len(hdr) - 2))

    for i, c in enumerate(eligible, 1):
        gfs = float(c.get("gymshark_brand_fit", 0))
        auth = float(c.get("authenticity_score", 0))
        niche = float(c.get("niche_score", 0))
        risk = c.get("audience_brand_risk", "—")
        rec = c.get("recommendation", "")
        reasoning = _build_gate1_reasoning(c)
        print(f"  {i:>2}. {c['name']:<28}  {c['tier']:<6}  {gfs:>4.1f}  {auth:>4.0f}  {niche:>5.0f}  {risk:<7}  {rec}")
        print(f"       {'':28}  {'':6}  {'':4}  {'':4}  {'':5}  {'':7}  ↳ {reasoning}")

    print(f"\nProceed with all {len(eligible)} creators to outreach drafting?")
    answer = _human_prompt("  [Enter/Y] = Yes, all  |  type IDs to EXCLUDE (e.g. C001,C003): ").upper()

    if not answer or answer == "Y":
        print(f"\n→ Proceeding with all {len(eligible)} creators.\n")
        return eligible

    exclude_ids = {x.strip() for x in answer.split(",")}
    filtered = [c for c in eligible if c["creator_id"] not in exclude_ids]
    for c in eligible:
        if c["creator_id"] in exclude_ids:
            print(f"  ✗ Excluded: {c['name']}")
    print(f"\n→ Proceeding with {len(filtered)} creators.\n")
    return filtered


# ---------------------------------------------------------------------------
# HUMAN GATE 2 — After outreach drafting: review and approve each draft
# ---------------------------------------------------------------------------


def human_gate_outreach(outreach_results: dict, drafts_dir: str) -> list[str]:
    """
    Show each outreach draft. Human approves or marks for revision.
    Returns list of creator_ids whose drafts are approved to send.
    """
    print("\n" + "=" * 60)
    print("HUMAN DECISION — Gate 2: Outreach Draft Review")
    print("=" * 60)

    approved_ids = []
    for cid, result in outreach_results.items():
        if result["status"] != "drafted":
            print(f"\n⚠️  {result.get('name', cid)}: draft failed — skipping.")
            continue

        print(f"\n{'─' * 55}")
        print(f"DRAFT: {result['name']}")
        print(f"{'─' * 55}")

        draft_path = os.path.join(drafts_dir, f"{cid}.txt")
        if os.path.exists(draft_path):
            with open(draft_path, encoding="utf-8") as f:
                print(f.read())

        if result.get("validation_issues"):
            print(f"⚠️  Validation issues: {'; '.join(result['validation_issues'])}")

        answer = _human_prompt("Approve this draft to send? [y/N]: ").upper()
        if answer == "Y":
            print("→ ✅ Approved.")
            approved_ids.append(cid)
        else:
            print("→ ⏭  Marked for revision.")

    print(f"\n→ {len(approved_ids)} draft(s) approved to send.\n")
    return approved_ids


# ---------------------------------------------------------------------------
# HUMAN GATE 3 — After outreach: record who responded yes → product brief
# ---------------------------------------------------------------------------


def human_gate_responses(
    approved_draft_ids: list[str],
    name_map: dict,
) -> list[str]:
    """
    Ask which creators said yes to the outreach offer.
    Returns creator_ids who responded positively (→ triggers product brief).
    """
    if not approved_draft_ids:
        return []

    print("\n" + "=" * 60)
    print("HUMAN DECISION — Gate 3: Outreach Responses")
    print("=" * 60)
    print("\nOutreach was sent to:")
    index_map = {}
    for i, cid in enumerate(approved_draft_ids, 1):
        print(f"  {i}. {name_map.get(cid, cid)}")
        index_map[str(i)] = cid

    print("\nWhich creators responded YES to the partnership offer?")
    answer = _human_prompt("Enter numbers (e.g. 1,3) or press Enter if none yet: ").strip()

    if not answer:
        print("→ No positive responses recorded. Product briefs skipped.")
        return []

    yes_ids = []
    for token in answer.split(","):
        token = token.strip()
        if token in index_map:
            yes_ids.append(index_map[token])
    for cid in yes_ids:
        print(f"  → ✅ {name_map.get(cid, cid)} said YES")
    print(f"\n→ {len(yes_ids)} creator(s) moving to product brief generation.\n")
    return yes_ids


# ---------------------------------------------------------------------------
# MAIN ORCHESTRATOR
# ---------------------------------------------------------------------------


def run_pipeline(
    creators_path: str = _DEFAULT_CREATORS,
    crm_path: str = _DEFAULT_CRM,
    intake_path: str = _DEFAULT_INTAKE,
    responses_path: str = _DEFAULT_RESPONSES,
    output_dir: str = _DEFAULT_OUTPUT,
    model: str = "api-llama-4-scout",
    draft_outreach: bool = True,
    human_review: bool = False,
) -> dict:
    """
    Run the full Gymshark creator pipeline: Score → Outreach → Brief.

    Brand risk is already evaluated by the LLM during scoring and stored
    in creators.csv (audience_brand_risk). No separate risk step needed.

    Parameters
    ----------
    human_review   : if True, pauses at each gate and waits for human input
    draft_outreach : if False, stops after Step 1 (dry run, no LLM calls)
    responses_path : CSV from simulate_outreach_responses.py — used in automated
                     mode to determine which creators said yes (Gate 3 substitute)
    """
    os.makedirs(output_dir, exist_ok=True)
    run_at = datetime.now().isoformat()
    print(f"\n{'=' * 60}")
    print(f"GYMSHARK PIPELINE RUN — {run_at}")
    print(f"Mode: {'INTERACTIVE (human review)' if human_review else 'AUTOMATED'}")
    print(f"{'=' * 60}\n")

    # Step 1 — Scoring
    eligible = run_scoring_step(creators_path, output_dir)

    # Gate 1 — Human reviews shortlist
    if human_review:
        eligible = human_gate_scoring(eligible)

    # All eligible creators proceed to outreach
    approved = eligible

    # Steps 2 & 3 — Outreach + Briefs
    outreach_results = {}
    approved_draft_ids: list[str] = []
    brief_results: dict = {}

    if draft_outreach and approved:
        outreach_results = run_outreach_step(approved, creators_path, crm_path, output_dir, model)

        if human_review:
            # Gate 2 — Human reviews each outreach draft
            drafts_dir = os.path.join(output_dir, "04_outreach_drafts")
            approved_draft_ids = human_gate_outreach(outreach_results, drafts_dir)

            # Gate 3 — Human records who said yes → product brief
            name_map = {r: outreach_results[r]["name"] for r in outreach_results}
            yes_ids = human_gate_responses(approved_draft_ids, name_map)
        else:
            # Automated: all successfully drafted creators are considered sent
            approved_draft_ids = [cid for cid, r in outreach_results.items() if r.get("status") == "drafted"]
            # Gate 3 substitute: read simulated responses from CSV
            yes_ids = load_simulated_responses(responses_path, approved_draft_ids)
            if yes_ids:
                names = [outreach_results[cid]["name"] for cid in yes_ids if cid in outreach_results]
                print(f"[Gate 3 — simulated] {len(yes_ids)} creator(s) said YES: {', '.join(names)}")
            else:
                print("[Gate 3 — simulated] No yes responses found in responses file.")

        # Step 3 — Product briefs for yes-responding creators
        if yes_ids:
            brief_results = run_brief_step(yes_ids, creators_path, crm_path, output_dir, intake_path)

    summary = {
        "run_at": run_at,
        "output_dir": output_dir,
        "human_review": human_review,
        "step1_eligible": len(eligible),
        "step1_ineligible": len(_scoring.load_creators(creators_path)) - len(eligible),
        "step2_drafted": sum(1 for r in outreach_results.values() if r.get("status") == "drafted"),
        "step2_errors": sum(1 for r in outreach_results.values() if r.get("status") == "error"),
        "step2_approved_to_send": len(approved_draft_ids),
        "step3_briefs_generated": sum(1 for r in brief_results.values() if r.get("status") == "generated"),
        "approved_creators": [a["name"] for a in approved],
    }
    _write_json(summary, os.path.join(output_dir, "05_pipeline_summary.json"))

    print(f"\n{'=' * 60}")
    print("PIPELINE COMPLETE")
    print(f"  Scored:   {summary['step1_eligible']} eligible creators")
    print(f"  Drafted:  {summary['step2_drafted']} outreach messages")
    if human_review:
        print(f"  Sent:     {summary['step2_approved_to_send']} approved to send")
    print(f"  Briefs:   {summary['step3_briefs_generated']} product briefs generated")
    if summary["step3_briefs_generated"] == 0 and not human_review:
        print("  ⚠  No briefs generated — check TRITONAI_API_KEY in .env and that")
        print("     data/outreach_responses.csv exists with responded_yes=True rows.")
    print(f"  Output:   {output_dir}")
    print(f"{'=' * 60}\n")

    return summary


# ---------------------------------------------------------------------------
# CLI ENTRY POINT
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gymshark Influencer Pipeline")
    parser.add_argument("--interactive", "-i", action="store_true", help="Enable human-in-the-loop review gates")
    parser.add_argument("--dry-run", action="store_true", help="Stop after Step 1 (no LLM calls)")
    args = parser.parse_args()

    result = run_pipeline(human_review=args.interactive, draft_outreach=not args.dry_run)
    print(json.dumps(result, indent=2))
