"""Tests for FR/LG encounter data integrity."""

import pytest
from shiny_pokemon.data import (
    ENCOUNTER_TABLES,
    SOFT_RESET_POKEMON,
    POKEMON,
    GameVersion,
)

FR = GameVersion.FIRE_RED
LG = GameVersion.LEAF_GREEN

# Pokemon that are truly exclusive to one version (never appear in the other).
# Oddish/Gloom are FR-exclusive; Bellsprout/Weepinbell are LG-exclusive.
FR_EXCLUSIVES = {"Ekans", "Arbok", "Oddish", "Gloom", "Growlithe", "Scyther", "Electabuzz"}
LG_EXCLUSIVES = {"Sandshrew", "Sandslash", "Bellsprout", "Weepinbell", "Vulpix", "Pinsir", "Magmar"}


class TestEncounterRates:
    """Every route's encounter rates must sum to 1.0."""

    @pytest.mark.parametrize("version", [FR, LG])
    def test_rates_sum_to_one(self, version):
        for route_name, route in ENCOUNTER_TABLES[version].items():
            total = sum(slot.rate for slot in route.encounter_slots)
            assert abs(total - 1.0) < 0.001, (
                f"{version.value} {route_name}: rates sum to {total}, expected 1.0"
            )


class TestPokemonReferences:
    """Every pokemon_name in encounter slots must exist in POKEMON dict."""

    @pytest.mark.parametrize("version", [FR, LG])
    def test_all_pokemon_exist(self, version):
        missing = []
        for route_name, route in ENCOUNTER_TABLES[version].items():
            for slot in route.encounter_slots:
                if slot.pokemon_name not in POKEMON:
                    missing.append(f"{route_name}: {slot.pokemon_name}")
        assert not missing, f"Unknown Pokemon in {version.value}: {missing}"

    def test_soft_reset_pokemon_exist(self):
        for name in SOFT_RESET_POKEMON:
            assert name in POKEMON, f"Soft reset Pokemon '{name}' not in POKEMON dict"


class TestVersionExclusives:
    """Version-exclusive Pokemon must not appear in the wrong version."""

    def test_fr_exclusives_not_in_lg(self):
        violations = []
        for route_name, route in ENCOUNTER_TABLES[LG].items():
            for slot in route.encounter_slots:
                if slot.pokemon_name in FR_EXCLUSIVES:
                    violations.append(f"{route_name}: {slot.pokemon_name}")
        assert not violations, f"FR exclusives found in LG: {violations}"

    def test_lg_exclusives_not_in_fr(self):
        violations = []
        for route_name, route in ENCOUNTER_TABLES[FR].items():
            for slot in route.encounter_slots:
                if slot.pokemon_name in LG_EXCLUSIVES:
                    violations.append(f"{route_name}: {slot.pokemon_name}")
        assert not violations, f"LG exclusives found in FR: {violations}"


class TestSpecificRoutes:
    """Spot-check known encounter data."""

    def test_route_1_both_versions(self):
        for version in [FR, LG]:
            route = ENCOUNTER_TABLES[version]["Route 1"]
            names = {s.pokemon_name for s in route.encounter_slots}
            assert names == {"Pidgey", "Rattata"}

    def test_route_4_fr_has_ekans(self):
        route = ENCOUNTER_TABLES[FR]["Route 4"]
        names = {s.pokemon_name for s in route.encounter_slots}
        assert "Ekans" in names

    def test_route_4_lg_has_sandshrew(self):
        route = ENCOUNTER_TABLES[LG]["Route 4"]
        names = {s.pokemon_name for s in route.encounter_slots}
        assert "Sandshrew" in names

    def test_abra_on_route_24(self):
        for version in [FR, LG]:
            route = ENCOUNTER_TABLES[version]["Route 24"]
            abra_slots = [s for s in route.encounter_slots if s.pokemon_name == "Abra"]
            assert len(abra_slots) == 1
            assert abra_slots[0].rate == 0.15

    def test_abra_flees(self):
        assert POKEMON["Abra"].flees is True

    def test_no_other_pokemon_flees(self):
        fleeing = [p.name for p in POKEMON.values() if p.flees and p.name != "Abra"]
        assert not fleeing, f"Unexpected fleeing Pokemon: {fleeing}"


class TestSoftResetPokemon:
    """Soft reset targets must be correctly categorized."""

    def test_starters(self):
        starters = {n for n, d in SOFT_RESET_POKEMON.items() if d["category"] == "Starter"}
        assert starters == {"Bulbasaur", "Charmander", "Squirtle"}

    def test_legendaries(self):
        legends = {n for n, d in SOFT_RESET_POKEMON.items() if d["category"] == "Legendary"}
        assert legends == {"Articuno", "Zapdos", "Moltres", "Mewtwo"}

    def test_roaming_beasts(self):
        roaming = {n for n, d in SOFT_RESET_POKEMON.items() if d["category"] == "Roaming"}
        assert roaming == {"Raikou", "Entei", "Suicune"}

    def test_both_versions_have_same_routes(self):
        """FR and LG should have the same set of route names."""
        fr_routes = set(ENCOUNTER_TABLES[FR].keys())
        lg_routes = set(ENCOUNTER_TABLES[LG].keys())
        assert fr_routes == lg_routes, (
            f"Routes differ between versions.\n"
            f"FR only: {fr_routes - lg_routes}\n"
            f"LG only: {lg_routes - fr_routes}"
        )


class TestLevelRanges:
    """Encounter levels must be sensible."""

    @pytest.mark.parametrize("version", [FR, LG])
    def test_min_not_greater_than_max(self, version):
        violations = []
        for route_name, route in ENCOUNTER_TABLES[version].items():
            for slot in route.encounter_slots:
                if slot.level_min > slot.level_max:
                    violations.append(
                        f"{route_name}: {slot.pokemon_name} "
                        f"level_min={slot.level_min} > level_max={slot.level_max}"
                    )
        assert not violations, f"Invalid level ranges: {violations}"
