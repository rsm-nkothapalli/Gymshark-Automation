"""
Tests for skills/skills/skill-05-product-brief/brief_helpers.py

LLM calls (generate_creative_brief, generate_full_brief) are not tested here
because they require a live API key. All pure-logic functions are covered.
"""

import importlib.util
import os
import pytest

_spec = importlib.util.spec_from_file_location(
    "brief_helpers",
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "..",
            "skills",
            "skill-05-product-brief",
            "brief_helpers.py",
        )
    ),
)
bh = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bh)


# ── recommend_product_line ────────────────────────────────────────────────────


def test_bodybuilding_gets_cbum():
    assert bh.recommend_product_line("Bodybuilding", 70.0) == "cbum"


def test_powerlifting_gets_lifting():
    assert bh.recommend_product_line("Powerlifting & Strength", 65.0) == "lifting"


def test_strength_gets_lifting():
    assert bh.recommend_product_line("Strength Training", 60.0) == "lifting"


def test_running_niche_gets_running():
    assert bh.recommend_product_line("Running & Cardio", 50.0) == "running"


def test_hiit_gets_hiit():
    assert bh.recommend_product_line("HIIT & Crossfit", 55.0) == "hiit"


def test_crossfit_gets_hiit():
    assert bh.recommend_product_line("Crossfit", 50.0) == "hiit"


def test_yoga_gets_adapt():
    assert bh.recommend_product_line("Yoga & Mindfulness", 20.0) == "adapt"


def test_pilates_gets_adapt():
    assert bh.recommend_product_line("Pilates", 15.0) == "adapt"


def test_physique_gets_form():
    assert bh.recommend_product_line("Physique & Fitness Model", 75.0) == "form"


def test_mostly_female_audience_gets_seamless():
    assert bh.recommend_product_line("General Fitness", 30.0) == "seamless"


def test_mostly_male_audience_gets_training():
    assert bh.recommend_product_line("Gym Lifestyle", 60.0) == "training"


def test_borderline_female_gets_seamless():
    # 44% male = mostly female → seamless
    assert bh.recommend_product_line("General Fitness", 44.0) == "seamless"


def test_borderline_male_gets_training():
    # 45% male = training threshold
    assert bh.recommend_product_line("General Fitness", 45.0) == "training"


# ── generate_promo_code ───────────────────────────────────────────────────────


def test_promo_code_starts_with_gs():
    code = bh.generate_promo_code("Naomi Fitness")
    assert code.startswith("GS")


def test_promo_code_has_digits_at_end():
    code = bh.generate_promo_code("Naomi Fitness")
    assert code[-2:].isdigit()


def test_promo_code_strips_special_chars():
    code = bh.generate_promo_code("Naomi | Fitness")
    assert "|" not in code
    assert " " not in code


def test_promo_code_max_length():
    # GS + 4 letters + 2 digits = 8 chars max
    code = bh.generate_promo_code("Alexander")
    assert len(code) <= 8


def test_promo_code_short_name():
    # Names shorter than 4 letters should still work
    code = bh.generate_promo_code("Ali")
    assert code.startswith("GS")
    assert len(code) >= 5


# ── PRODUCT_LINES structure ───────────────────────────────────────────────────


def test_all_product_lines_have_required_keys():
    required = {"description", "best_for", "example_items"}
    for name, line in bh.PRODUCT_LINES.items():
        assert required.issubset(line.keys()), f"{name} missing keys"


def test_all_product_lines_have_example_items():
    for name, line in bh.PRODUCT_LINES.items():
        assert len(line["example_items"]) >= 1, f"{name} has no example items"
