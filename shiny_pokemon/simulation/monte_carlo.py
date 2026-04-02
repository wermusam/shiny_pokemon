"""Monte Carlo simulation engine for shiny hunting.

How Monte Carlo works here:
    Instead of computing the exact probability with a formula, we
    *simulate* thousands of shiny hunts. Each simulated hunt flips a
    weighted coin over and over until it lands on "shiny". We record
    how many flips it took.

    After thousands of hunts, we have a distribution of results.
    The average should match the theoretical expected value (1/p),
    and the shape of the histogram matches the geometric distribution.

    This is Monte Carlo simulation: answer a probability question by
    running the experiment many times and looking at the results.
"""

import math
from typing import Generator

import numpy as np


class SimulationResult:
    """The outcome of running one or more simulated shiny hunts.

    Attributes:
        attempts: List of integers. Each entry is how many encounters
            one simulated hunt took to find a shiny.
        num_completed: How many hunts have been simulated so far.
        mean: Average encounters across all hunts.
        median: Middle value when hunts are sorted.
        std_dev: Standard deviation (how spread out the results are).
        percentiles: Key percentile values (25th, 50th, 75th, 90th, 95th, 99th).
    """

    def __init__(self, attempts: list[int]) -> None:
        self.attempts = attempts
        self.num_completed = len(attempts)

        if self.num_completed == 0:
            self.mean = 0.0
            self.median = 0.0
            self.std_dev = 0.0
            self.percentiles = {25: 0, 50: 0, 75: 0, 90: 0, 95: 0, 99: 0}
            return

        arr = np.array(attempts)
        self.mean = float(np.mean(arr))
        self.median = float(np.median(arr))
        self.std_dev = float(np.std(arr))
        self.percentiles = {
            p: int(np.percentile(arr, p))
            for p in [25, 50, 75, 90, 95, 99]
        }


class ShinyHuntSimulator:
    """Simulates shiny hunts using Monte Carlo methods.

    The core idea: each encounter has some probability `p` of being
    a shiny of the target species. We draw from a geometric distribution
    to find how many encounters it takes to get the first success.

    The geometric distribution is the mathematical model for:
    "How many coin flips until the first heads?"

    Args:
        effective_probability: Combined probability per encounter.
            For a simple hunt: 1/8192.
            For a specific target: encounter_rate * 1/8192.
            For Abra: encounter_rate * 1/8192 * catch_chance.
        rng_seed: Optional seed for reproducible results.
            If None, results will be different each time (true randomness).
            Set a seed when testing to get repeatable results.
    """

    def __init__(
        self, effective_probability: float, rng_seed: int | None = None
    ) -> None:
        self.effective_probability = effective_probability
        self.rng = np.random.default_rng(rng_seed)

    def run(self, num_trials: int = 10_000) -> SimulationResult:
        """Run all simulated hunts at once.

        Uses numpy's geometric distribution for speed. This is
        mathematically identical to flipping a biased coin in a loop,
        but about 100x faster because numpy does it in bulk.

        Args:
            num_trials: How many shiny hunts to simulate.

        Returns:
            A SimulationResult with the outcomes of all hunts.
        """
        # numpy.geometric(p, size) returns an array of integers.
        # Each integer = number of trials until first success.
        samples = self.rng.geometric(
            p=self.effective_probability, size=num_trials
        )
        return SimulationResult(samples.tolist())

    def run_incremental(
        self, num_trials: int, batch_size: int = 100
    ) -> Generator[SimulationResult, None, None]:
        """Run simulations in batches, yielding progress after each batch.

        This is used by the GUI to update the histogram live as
        simulations run. Each yield gives the cumulative results so far.

        Args:
            num_trials: Total number of hunts to simulate.
            batch_size: How many hunts per batch. Smaller = more
                frequent updates but slightly slower overall.

        Yields:
            SimulationResult with all results accumulated so far.
        """
        all_attempts: list[int] = []
        remaining = num_trials

        while remaining > 0:
            this_batch = min(batch_size, remaining)
            samples = self.rng.geometric(
                p=self.effective_probability, size=this_batch
            )
            all_attempts.extend(samples.tolist())
            remaining -= this_batch
            yield SimulationResult(list(all_attempts))

    @staticmethod
    def theoretical_mean(effective_probability: float) -> float:
        """Expected number of encounters (the mathematical answer).

        For a geometric distribution, the expected value is 1/p.
        For base shiny rate: 1 / (1/8192) = 8192.

        Args:
            effective_probability: Probability per encounter.

        Returns:
            Expected encounters as a float.
        """
        return 1.0 / effective_probability

    @staticmethod
    def theoretical_median(effective_probability: float) -> float:
        """Median encounters (half of hunters find it by this point).

        The median of a geometric distribution is ceil(-1 / log2(1-p)).
        For base shiny rate: this is 5678.

        Args:
            effective_probability: Probability per encounter.

        Returns:
            Median encounters as a float.
        """
        return math.ceil(-1.0 / math.log2(1.0 - effective_probability))
