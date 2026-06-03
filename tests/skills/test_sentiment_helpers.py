"""
Tests for skills/skill-02-sentiment-risk/sentiment_helpers.py
"""

import importlib.util
import os

import pytest

# ---------------------------------------------------------------------------
# Load module
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "sentiment_helpers",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "skills",
            "skill-02-sentiment-risk",
            "sentiment_helpers.py",
        )
    ),
)
sh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sh)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _row(**overrides) -> dict:
    base = {
        "creator_id": "C001",
        "comment_id": "CMT001",
        "comment_text": "Great workout video!",
        "sentiment_label": "POSITIVE",
        "compound_score": "0.8",
        "negative_creator_flag": "No",
        "purchase_intent": "No",
    }
    base.update(overrides)
    return base


def _make_rows(n: int, flagged_pct: float = 0.0, avg_compound: float = 0.8) -> list[dict]:
    """Generate n rows with a given flagged % and compound score."""
    n_flagged = int(n * flagged_pct / 100)
    rows = []
    for i in range(n):
        rows.append(
            _row(
                comment_id=f"CMT{i:03d}",
                compound_score=str(avg_compound),
                negative_creator_flag="Yes" if i < n_flagged else "No",
            )
        )
    return rows


# ---------------------------------------------------------------------------
# calculate_sentiment_metrics
# ---------------------------------------------------------------------------


def test_metrics_returns_none_for_empty():
    assert sh.calculate_sentiment_metrics([]) is None


def test_metrics_counts_totals():
    rows = _make_rows(10)
    m = sh.calculate_sentiment_metrics(rows)
    assert m["total_comments"] == 10


def test_metrics_positive_pct():
    rows = [_row(sentiment_label="POSITIVE")] * 7 + [_row(sentiment_label="NEGATIVE")] * 3
    m = sh.calculate_sentiment_metrics(rows)
    assert m["positive_pct"] == 70.0
    assert m["negative_pct"] == 30.0


def test_metrics_avg_sentiment():
    rows = [_row(compound_score="0.6")] * 4 + [_row(compound_score="0.8")] * 6
    m = sh.calculate_sentiment_metrics(rows)
    assert abs(m["avg_sentiment"] - 0.72) < 0.01


def test_metrics_flagged_count_and_pct():
    rows = _make_rows(50, flagged_pct=10.0)
    m = sh.calculate_sentiment_metrics(rows)
    assert m["flagged_count"] == 5
    assert m["flagged_pct"] == 10.0


def test_metrics_purchase_intent_count():
    rows = [_row(purchase_intent="Yes")] * 3 + [_row(purchase_intent="No")] * 7
    m = sh.calculate_sentiment_metrics(rows)
    assert m["purchase_intent_count"] == 3


def test_metrics_ignores_bad_compound_score():
    rows = [_row(compound_score="not_a_number"), _row(compound_score="0.5")]
    m = sh.calculate_sentiment_metrics(rows)
    assert m["avg_sentiment"] == 0.5


# ---------------------------------------------------------------------------
# assign_risk_level
# ---------------------------------------------------------------------------


def test_risk_unknown_for_fewer_than_50_comments():
    rows = _make_rows(30)
    m = sh.calculate_sentiment_metrics(rows)
    level, emoji, _ = sh.assign_risk_level(m)
    assert level == "UNKNOWN"
    assert emoji == "⚪"


def test_risk_unknown_for_none_metrics():
    level, _, _ = sh.assign_risk_level(None)
    assert level == "UNKNOWN"


def test_risk_high_when_flagged_pct_exceeds_15():
    rows = _make_rows(50, flagged_pct=20.0)
    m = sh.calculate_sentiment_metrics(rows)
    level, emoji, _ = sh.assign_risk_level(m)
    assert level == "HIGH"
    assert emoji == "🔴"


def test_risk_medium_when_flagged_pct_between_8_and_15():
    rows = _make_rows(50, flagged_pct=10.0)
    m = sh.calculate_sentiment_metrics(rows)
    level, emoji, _ = sh.assign_risk_level(m)
    assert level == "MEDIUM"
    assert emoji == "🟡"


def test_risk_low_when_flagged_below_8_and_sentiment_above_floor():
    rows = _make_rows(50, flagged_pct=2.0, avg_compound=0.8)
    m = sh.calculate_sentiment_metrics(rows)
    level, emoji, _ = sh.assign_risk_level(m)
    assert level == "LOW"
    assert emoji == "🟢"


def test_risk_low_when_no_flags_regardless_of_compound():
    # avg_compound is no longer used — 0% flagged always resolves to LOW
    rows = _make_rows(50, flagged_pct=0.0, avg_compound=0.1)
    m = sh.calculate_sentiment_metrics(rows)
    level, _, _ = sh.assign_risk_level(m)
    assert level == "LOW"


def test_risk_reason_contains_flagged_pct():
    rows = _make_rows(50, flagged_pct=20.0)
    m = sh.calculate_sentiment_metrics(rows)
    _, _, reason = sh.assign_risk_level(m)
    assert "flagged_pct" in reason


# ---------------------------------------------------------------------------
# get_example_flagged
# ---------------------------------------------------------------------------


def test_get_example_flagged_returns_only_flagged():
    rows = [
        _row(comment_text="This is fine", negative_creator_flag="No"),
        _row(comment_text="Bad comment here today", negative_creator_flag="Yes"),
    ]
    examples = sh.get_example_flagged(rows)
    assert len(examples) == 1
    assert "Bad comment" in examples[0]


def test_get_example_flagged_truncates_long_comments():
    long_text = "word1 word2 word3 word4 word5 word6 word7"
    rows = [_row(comment_text=long_text, negative_creator_flag="Yes")]
    examples = sh.get_example_flagged(rows)
    assert "[...]" in examples[0]


def test_get_example_flagged_respects_n_limit():
    rows = [_row(comment_text=f"bad comment {i}", negative_creator_flag="Yes") for i in range(10)]
    examples = sh.get_example_flagged(rows, n=3)
    assert len(examples) == 3


def test_get_example_flagged_empty_when_no_flags():
    rows = [_row(negative_creator_flag="No") for _ in range(5)]
    assert sh.get_example_flagged(rows) == []


# ---------------------------------------------------------------------------
# print_all_risk_summary (smoke test — checks it runs without error)
# ---------------------------------------------------------------------------


def test_print_all_risk_summary_runs(capsys):
    risk_results = {
        "C001": {
            "name": "Creator One",
            "risk_level": "LOW",
            "emoji": "🟢",
            "reason": "safe",
            "metrics": {
                "total_comments": 50,
                "flagged_pct": 2.0,
                "avg_sentiment": 0.75,
                "purchase_intent_count": 3,
            },
        },
        "C002": {
            "name": "Creator Two",
            "risk_level": "UNKNOWN",
            "emoji": "⚪",
            "reason": "not enough data",
            "metrics": None,
        },
    }
    sh.print_all_risk_summary(risk_results)
    out = capsys.readouterr().out
    assert "Creator One" in out
    assert "LOW" in out
    assert "UNKNOWN" in out
