"""Shiny Pokemon probability"""
import math

class ShinyOdds:
    """Represents shiny encounter odds for Pokemon Fire Red"""

    def __init__(self, name: str, odds: int):
        self.name = name
        self.odds = odds

    def cumulative_probability(self, resets: int) -> float:
        """Probability of at least one shiny after n resets."""
        return 1 - ((self.odds - 1) / self.odds) ** resets
    
    def resets_for_probability(self, target: float) -> int:
        """Number of resets needed to reach a target probability."""
        if target <= 0:
            return 0
        if target >= 1:
            return float('inf')
        return int(math.ceil(
            math.log(1 - target) / math.log((self.odds - 1) / self.odds)
        ))

    def effective_probability(
        self, encounter_rate: float = 1.0, catch_rate: float = 1.0
    ) -> float:
        """Per-encounter probability of catching a shiny target.

        Args:
            encounter_rate: Chance this species appears (0.0-1.0).
                For soft resets this is 1.0 (you always see your target).
            catch_rate: Chance of catching once encountered (0.0-1.0).
                Relevant for fleeing Pokemon like Abra. Default 1.0.

        Returns:
            Combined probability as a float between 0.0 and 1.0.
        """
        return encounter_rate * (1 / self.odds) * catch_rate

    def percentile_rank(
        self,
        encounters: int,
        encounter_rate: float = 1.0,
        catch_rate: float = 1.0,
    ) -> float:
        """What percentile is a hunter at after this many encounters?

        Uses the CDF of the geometric distribution. A result of 63.2
        means 63.2% of hunters would have found a shiny by now.

        Args:
            encounters: Number of encounters completed.
            encounter_rate: Chance this species appears per encounter.
            catch_rate: Chance of catching once encountered.

        Returns:
            Percentile as a float from 0.0 to 100.0.
        """
        p = self.effective_probability(encounter_rate, catch_rate)
        if p <= 0:
            return 0.0
        return (1 - (1 - p) ** encounters) * 100