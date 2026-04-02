"""Tests for the Monte Carlo simulation engine.

These tests verify that the simulation produces results consistent
with the known mathematical properties of the geometric distribution.
"""

from shiny_pokemon.simulation.monte_carlo import ShinyHuntSimulator, SimulationResult
from shiny_pokemon.shiny import ShinyOdds


class TestSimulationResult:
    """Tests for SimulationResult statistics."""

    def test_empty_result(self):
        """An empty result should have zero stats."""
        result = SimulationResult([])
        assert result.num_completed == 0
        assert result.mean == 0.0
        assert result.median == 0.0

    def test_single_trial(self):
        """A single trial should have mean == median == that value."""
        result = SimulationResult([5000])
        assert result.num_completed == 1
        assert result.mean == 5000.0
        assert result.median == 5000.0

    def test_known_values(self):
        """Test with a known small dataset."""
        result = SimulationResult([1, 2, 3, 4, 5])
        assert result.num_completed == 5
        assert result.mean == 3.0
        assert result.median == 3.0


class TestDeterministicSeeds:
    """Fixed seeds should produce identical results every time."""

    def test_same_seed_same_results(self):
        """Two simulators with the same seed should match."""
        sim1 = ShinyHuntSimulator(1 / 8192, rng_seed=42)
        sim2 = ShinyHuntSimulator(1 / 8192, rng_seed=42)
        r1 = sim1.run(1000)
        r2 = sim2.run(1000)
        assert r1.attempts == r2.attempts

    def test_different_seeds_different_results(self):
        """Different seeds should produce different results."""
        sim1 = ShinyHuntSimulator(1 / 8192, rng_seed=42)
        sim2 = ShinyHuntSimulator(1 / 8192, rng_seed=99)
        r1 = sim1.run(1000)
        r2 = sim2.run(1000)
        assert r1.attempts != r2.attempts


class TestConvergence:
    """With enough trials, simulation stats should approach theory."""

    def test_mean_converges_to_expected_value(self):
        """Mean of 100K trials should be within 5% of 1/p."""
        p = 1 / 8192
        sim = ShinyHuntSimulator(p, rng_seed=12345)
        result = sim.run(100_000)
        theoretical = ShinyHuntSimulator.theoretical_mean(p)
        # Allow 5% tolerance
        assert abs(result.mean - theoretical) / theoretical < 0.05, (
            f"Mean {result.mean:.0f} not close enough to theoretical {theoretical:.0f}"
        )

    def test_median_converges(self):
        """Median of 100K trials should be within 5% of theoretical."""
        p = 1 / 8192
        sim = ShinyHuntSimulator(p, rng_seed=12345)
        result = sim.run(100_000)
        theoretical = ShinyHuntSimulator.theoretical_median(p)
        assert abs(result.median - theoretical) / theoretical < 0.05, (
            f"Median {result.median:.0f} not close enough to theoretical {theoretical:.0f}"
        )

    def test_compound_probability_higher_mean(self):
        """Hunting a specific species (lower p) should need more encounters."""
        p_any = 1 / 8192
        p_pidgey = 0.50 * (1 / 8192)  # Pidgey on Route 1

        sim_any = ShinyHuntSimulator(p_any, rng_seed=42)
        sim_pidgey = ShinyHuntSimulator(p_pidgey, rng_seed=42)

        r_any = sim_any.run(10_000)
        r_pidgey = sim_pidgey.run(10_000)

        assert r_pidgey.mean > r_any.mean, (
            f"Hunting specific species ({r_pidgey.mean:.0f}) "
            f"should take more encounters than any shiny ({r_any.mean:.0f})"
        )

    def test_guaranteed_shiny(self):
        """With probability 1.0, every hunt should take exactly 1 encounter."""
        sim = ShinyHuntSimulator(1.0, rng_seed=42)
        result = sim.run(1000)
        assert all(a == 1 for a in result.attempts)
        assert result.mean == 1.0


class TestIncremental:
    """Tests for the incremental (live-updating) simulation mode."""

    def test_incremental_accumulates(self):
        """Each batch should add to the total count."""
        sim = ShinyHuntSimulator(1 / 100, rng_seed=42)
        results = list(sim.run_incremental(500, batch_size=100))
        # Should have 5 results (500 / 100)
        assert len(results) == 5
        # Each result should have progressively more trials
        counts = [r.num_completed for r in results]
        assert counts == [100, 200, 300, 400, 500]

    def test_incremental_matches_full_run(self):
        """Incremental results should match a single full run with same seed."""
        p = 1 / 100
        sim1 = ShinyHuntSimulator(p, rng_seed=42)
        sim2 = ShinyHuntSimulator(p, rng_seed=42)

        full = sim1.run(500)
        incremental_results = list(sim2.run_incremental(500, batch_size=100))
        final = incremental_results[-1]

        assert final.attempts == full.attempts

    def test_uneven_batches(self):
        """Handles cases where total isn't evenly divisible by batch."""
        sim = ShinyHuntSimulator(1 / 100, rng_seed=42)
        results = list(sim.run_incremental(250, batch_size=100))
        assert len(results) == 3  # 100, 100, 50
        assert results[-1].num_completed == 250


class TestShinyOddsNewMethods:
    """Tests for the new methods added to ShinyOdds."""

    def setup_method(self):
        self.fire_red = ShinyOdds(name="Fire Red", odds=8192)

    def test_effective_probability_base(self):
        """With defaults (rate=1.0, catch=1.0), should be 1/odds."""
        result = self.fire_red.effective_probability()
        assert abs(result - 1 / 8192) < 1e-10

    def test_effective_probability_with_encounter_rate(self):
        """Pidgey at 50% on Route 1 should halve the probability."""
        result = self.fire_red.effective_probability(encounter_rate=0.5)
        assert abs(result - 0.5 / 8192) < 1e-10

    def test_effective_probability_abra(self):
        """Abra: 15% encounter, ~33% catch = much lower effective rate."""
        result = self.fire_red.effective_probability(
            encounter_rate=0.15, catch_rate=0.33
        )
        expected = 0.15 * (1 / 8192) * 0.33
        assert abs(result - expected) < 1e-10

    def test_percentile_rank_zero(self):
        """Zero encounters = 0th percentile."""
        assert self.fire_red.percentile_rank(0) == 0.0

    def test_percentile_rank_at_expected_value(self):
        """At 8192 encounters, should be ~63.2% (1 - 1/e)."""
        result = self.fire_red.percentile_rank(8192)
        assert abs(result - 63.2) < 0.5

    def test_percentile_rank_at_double_expected(self):
        """At 16384 encounters, should be ~86.5%."""
        result = self.fire_red.percentile_rank(16384)
        assert abs(result - 86.5) < 0.5

    def test_percentile_rank_with_encounter_rate(self):
        """Lower effective rate = lower percentile for same encounters."""
        full = self.fire_red.percentile_rank(5000, encounter_rate=1.0)
        half = self.fire_red.percentile_rank(5000, encounter_rate=0.5)
        assert half < full
