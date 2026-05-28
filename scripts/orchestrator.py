"""Gymshark Influencer Pipeline Orchestrator — Milestone 03

Chains Skill 01 → 02 → 03 → 05 with optional human-in-the-loop gates.
Delegates all step logic to skills/skill-06-pipeline-workflow/pipeline_helpers.py.

Usage::

    # Interactive mode (pauses at each human gate)
    uv run python scripts/orchestrator.py --interactive

    # Automated mode (no prompts — all LOW-risk creators auto-drafted)
    uv run python scripts/orchestrator.py

    # Dry run (scoring + risk only, no LLM calls)
    uv run python scripts/orchestrator.py --dry-run
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


def _load_pipeline():
    spec = importlib.util.spec_from_file_location(
        "pipeline_helpers",
        os.path.join(REPO_ROOT, "skills", "skill-06-pipeline-workflow", "pipeline_helpers.py"),
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    parser = argparse.ArgumentParser(description="Gymshark Influencer Pipeline")
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Enable human-in-the-loop review gates at each step"
    )
    parser.add_argument("--dry-run", action="store_true", help="Stop after Step 3 (scoring + risk only, no LLM calls)")
    args = parser.parse_args()

    ph = _load_pipeline()
    summary = ph.run_pipeline(
        human_review=args.interactive,
        draft_outreach=not args.dry_run,
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
