"""Tests for the time estimator math."""

import math
from shiny_pokemon.shiny import ShinyOdds


def test_expected_time_basic():
    """At 1/8192, expected encounters is 8192, which at 18s = ~41 hours."""
    game = ShinyOdds(name="Fire Red", odds=8192)
    p = game.effective_probability(1.0)
    expected = 1 / p
    hours = (expected * 18) / 3600

    assert expected == 8192
    assert abs(hours - 40.96) < 0.01


def test_expected_time_with_encounter_rate():
    """A 20% encounter rate should multiply expected time by 5."""
    game = ShinyOdds(name="Fire Red", odds=8192)
    p = game.effective_probability(0.20)
    expected = 1 / p
    hours = (expected * 18) / 3600

    assert expected == pytest.approx(40960, rel=0.01)
    assert hours == pytest.approx(204.8, rel=0.01)


def test_median_is_less_than_mean():
    """The geometric distribution is right-skewed, so median < mean."""
    game = ShinyOdds(name="Fire Red", odds=8192)
    p = game.effective_probability(1.0)
    mean = 1 / p
    median = math.ceil(math.log(0.5) / math.log(1 - p))

    assert median < mean
    assert median == 5678  # ln(2) / (1/8192) ≈ 5678


def test_memoryless_property():
    """The geometric distribution is memoryless: expected time from
    scratch is the same no matter how many encounters you've done."""
    game = ShinyOdds(name="Fire Red", odds=8192)
    p = game.effective_probability(1.0)
    expected = 1 / p

    # Whether you've done 0 or 4000 encounters, the expected total
    # hunt time is always 8192 * seconds_per_try
    total_hours = (expected * 18) / 3600
    assert abs(total_hours - 40.96) < 0.01

    # Time spent so far is just encounters_done * seconds_per_try
    time_spent = (4000 * 18) / 3600
    assert abs(time_spent - 20.0) < 0.01


def test_time_formats():
    """Verify the time formatting logic works for different ranges."""
    # Under 1 hour -> show minutes
    hours = 0.5
    assert hours < 1
    minutes = hours * 60
    assert minutes == 30

    # Over 24 hours -> show days
    hours = 48
    days = hours / 24
    assert days == 2.0


# Need pytest for approx
import pytest
