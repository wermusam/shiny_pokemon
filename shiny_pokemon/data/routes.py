"""Route and encounter data structures for FR/LG."""

from enum import Enum


class GameVersion(Enum):
    FIRE_RED = "Fire Red"
    LEAF_GREEN = "Leaf Green"


class HuntMethod(Enum):
    RANDOM_ENCOUNTER = "Random Encounter"
    SOFT_RESET = "Soft Reset"


class EncounterType(Enum):
    GRASS = "Grass"
    CAVE = "Cave"
    SURF = "Surf"
    OLD_ROD = "Old Rod"
    GOOD_ROD = "Good Rod"
    SUPER_ROD = "Super Rod"


class EncounterSlot:
    """One entry in a route's encounter table.

    Attributes:
        pokemon_name: Species name (must match a key in POKEMON dict).
        rate: Encounter rate as a decimal (0.0 to 1.0). All slots
              in a route/encounter_type must sum to 1.0.
        level_min: Minimum encounter level.
        level_max: Maximum encounter level.
    """

    def __init__(
        self, pokemon_name: str, rate: float, level_min: int, level_max: int
    ) -> None:
        self.pokemon_name = pokemon_name
        self.rate = rate
        self.level_min = level_min
        self.level_max = level_max

    def __repr__(self) -> str:
        return (
            f"EncounterSlot({self.pokemon_name!r}, {self.rate}, "
            f"lv{self.level_min}-{self.level_max})"
        )


class RouteData:
    """Encounter data for one location in one encounter type.

    Attributes:
        name: Location display name (e.g. "Route 1", "Mt. Moon 1F").
        encounter_type: How the Pokemon is encountered.
        encounter_slots: List of possible encounters with rates.
    """

    def __init__(
        self,
        name: str,
        encounter_type: EncounterType,
        encounter_slots: tuple[EncounterSlot, ...],
    ) -> None:
        self.name = name
        self.encounter_type = encounter_type
        self.encounter_slots = encounter_slots

    def __repr__(self) -> str:
        return f"RouteData({self.name!r}, {self.encounter_type.value}, {len(self.encounter_slots)} slots)"
