"""Tests for ShinyOdds class."""

from shiny_pokemon.shiny import ShinyOdds


class TestShinyOdds:
    """Tests for shiny probability calculations."""

    def setup_method(self):
        """Create a Fire Red instance for each test."""
        self.fire_red = ShinyOdds(name="Fire Red", odds=8192)

    def test_single_reset_probability(self):
        """One reset should give roughly 1/8192 chance."""
        result = self.fire_red.cumulative_probability(1)
        assert abs(result - 1 / 8192) < 0.0001

    def test_zero_resets(self):
        """Zero resets should give zero probability."""
        assert self.fire_red.cumulative_probability(0) == 0.0

    def test_probability_increases_with_resets(self):
        """More resets should always mean higher probability."""
        p100 = self.fire_red.cumulative_probability(100)
        p1000 = self.fire_red.cumulative_probability(1000)
        p5000 = self.fire_red.cumulative_probability(5000)
        assert p100 < p1000 < p5000

    def test_50_percent_milestone(self):
        """50% probability should require 5678 resets."""
        assert self.fire_red.resets_for_probability(0.5) == 5678

    def test_resets_for_zero_probability(self):
        """Targeting zero probability should return 0."""
        assert self.fire_red.resets_for_probability(0) == 0

    def test_probability_never_exceeds_one(self):
        """Even after many resets, probability stays below 1."""
        result = self.fire_red.cumulative_probability(100000)
        assert result < 1.0

    def test_modern_odds(self):
        """Modern games (1/4096) should need fewer resets."""
        modern = ShinyOdds(name="Modern", odds=4096)
        fire_red_resets = self.fire_red.resets_for_probability(0.5)
        modern_resets = modern.resets_for_probability(0.5)
        assert modern_resets < fire_red_resets
