"""
Tests for skills/skill-03-outreach-drafting/outreach_helpers.py
"""

import importlib.util
import os

import pytest

# ---------------------------------------------------------------------------
# Load module
# ---------------------------------------------------------------------------

_spec = importlib.util.spec_from_file_location(
    "outreach_helpers",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "skills",
            "skill-03-outreach-drafting",
            "outreach_helpers.py",
        )
    ),
)
oh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oh)


# ---------------------------------------------------------------------------
# TIER_TONE_GUIDE / get_tone_guide
# ---------------------------------------------------------------------------


def test_get_tone_guide_returns_nano():
    guide = oh.get_tone_guide("nano")
    assert guide["max_words"] == 300
    assert "warm" in guide["tone"]


def test_get_tone_guide_returns_mega():
    guide = oh.get_tone_guide("mega")
    assert guide["max_words"] == 200
    assert "brief" in guide["tone"]


def test_get_tone_guide_case_insensitive():
    assert oh.get_tone_guide("MICRO") == oh.get_tone_guide("micro")


def test_get_tone_guide_unknown_tier_falls_back_to_micro():
    guide = oh.get_tone_guide("unknown_tier")
    assert guide == oh.get_tone_guide("micro")


# ---------------------------------------------------------------------------
# check_banned_phrases
# ---------------------------------------------------------------------------


def test_check_banned_phrases_detects_banned():
    msg = "You are amazing and I love your content!"
    found = oh.check_banned_phrases(msg)
    assert "amazing" in found
    assert "love your content" in found


def test_check_banned_phrases_clean_message():
    msg = "I've been watching your try-on hauls and noticed your honest reviews."
    assert oh.check_banned_phrases(msg) == []


def test_check_banned_phrases_case_insensitive():
    assert oh.check_banned_phrases("You're a HUGE FAN favourite") == ["huge fan"]


def test_check_banned_phrases_all_banned():
    msg = "amazing inspiring love your content huge fan came across your page perfect fit"
    found = oh.check_banned_phrases(msg)
    assert len(found) == 6


# ---------------------------------------------------------------------------
# word_count
# ---------------------------------------------------------------------------


def test_word_count_basic():
    assert oh.word_count("hello world") == 2


def test_word_count_empty():
    assert oh.word_count("") == 0


def test_word_count_multi_space():
    assert oh.word_count("one  two  three") == 3


# ---------------------------------------------------------------------------
# validate_message
# ---------------------------------------------------------------------------


def test_validate_message_no_issues():
    msg = " ".join(["word"] * 100)
    issues = oh.validate_message(msg, "nano")
    assert issues == []


def test_validate_message_too_long():
    msg = " ".join(["word"] * 350)
    issues = oh.validate_message(msg, "nano")
    assert any("Too long" in i for i in issues)


def test_validate_message_banned_phrase():
    msg = "You are amazing, check this out."
    issues = oh.validate_message(msg, "micro")
    assert any("amazing" in i for i in issues)


def test_validate_message_multiple_issues():
    msg = " ".join(["word"] * 350) + " amazing"
    issues = oh.validate_message(msg, "nano")
    assert len(issues) == 2


# ---------------------------------------------------------------------------
# format_outreach_output
# ---------------------------------------------------------------------------


def test_format_outreach_output_basic():
    creator = {
        "name": "Test Creator",
        "youtube_handle": "@testcreator",
        "outreach_channel": "Instagram DM",
        "suggested_deal_type": "gift_seeding",
    }
    result = oh.format_outreach_output(creator, "Hi there, this is the message.")
    assert "Test Creator" in result
    assert "@testcreator" in result
    assert "Instagram DM" in result
    assert "gift_seeding" in result
    assert "Hi there" in result


def test_format_outreach_output_strips_at_from_handle():
    creator = {"name": "A", "youtube_handle": "@myhandle"}
    result = oh.format_outreach_output(creator, "msg")
    assert "@@myhandle" not in result
    assert "@myhandle" in result


def test_format_outreach_output_falls_back_to_handle_column():
    creator = {"name": "A", "handle": "fallback_handle"}
    result = oh.format_outreach_output(creator, "msg")
    assert "fallback_handle" in result


def test_format_outreach_output_includes_review_note():
    creator = {"name": "A", "youtube_handle": "@a"}
    result = oh.format_outreach_output(creator, "msg", review_note="Needs revision")
    assert "Needs revision" in result


def test_format_outreach_output_no_review_note_omitted():
    creator = {"name": "A", "youtube_handle": "@a"}
    result = oh.format_outreach_output(creator, "msg")
    assert "Human review note" not in result


def test_format_outreach_output_shows_word_count():
    creator = {"name": "A", "youtube_handle": "@a"}
    msg = "one two three four five"
    result = oh.format_outreach_output(creator, msg)
    assert "Word count: 5" in result


# ---------------------------------------------------------------------------
# build_outreach_prompt
# ---------------------------------------------------------------------------


def test_build_outreach_prompt_contains_creator_name():
    context = {"name": "Jane Doe", "tier": "nano", "niche": "yoga"}
    prompt = oh.build_outreach_prompt(context)
    assert "Jane Doe" in prompt


def test_build_outreach_prompt_contains_personalisation_anchors():
    context = {
        "name": "Jane",
        "tier": "micro",
        "signals_authentic_pos": "not sponsored",
        "signals_community": "you guys",
    }
    prompt = oh.build_outreach_prompt(context)
    assert "not sponsored" in prompt
    assert "you guys" in prompt


def test_build_outreach_prompt_uses_tier_tone():
    nano_prompt = oh.build_outreach_prompt({"name": "A", "tier": "nano"})
    mega_prompt = oh.build_outreach_prompt({"name": "A", "tier": "mega"})
    assert "warm, peer-level" in nano_prompt
    assert "brief, pitch-led" in mega_prompt


def test_build_outreach_prompt_includes_banned_phrase_rule():
    prompt = oh.build_outreach_prompt({"name": "A", "tier": "micro"})
    assert "amazing" in prompt  # listed in the NEVER USE rule
