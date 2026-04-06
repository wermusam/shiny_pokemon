"""Tests for FR/LG encounter data integrity.

Data sourced from pokefirered decompilation (github.com/pret/pokefirered).
"""

import pytest
from shiny_pokemon.data import (
    ENCOUNTER_TABLES,
    SOFT_RESET_POKEMON,
    POKEMON,
    GameVersion,
)

FR = GameVersion.FIRE_RED
LG = GameVersion.LEAF_GREEN

# Pokemon that appear in FR wild encounters but never in LG, and vice versa.
# This includes version differences across all encounter types (grass, surf, fishing).
FR_EXCLUSIVES = {
    "Ekans", "Arbok", "Oddish", "Gloom", "Growlithe",
    "Scyther", "Electabuzz", "Psyduck", "Golduck",
    "Shellder", "Seadra", "Wooper", "Qwilfish", "Skarmory",
    "Delibird", "Murkrow", "Weezing",
}
LG_EXCLUSIVES = {
    "Sandshrew", "Sandslash", "Bellsprout", "Weepinbell", "Vulpix",
    "Pinsir", "Magmar", "Slowpoke", "Slowbro",
    "Staryu", "Kingler", "Marill", "Remoraid", "Mantine",
    "Muk", "Misdreavus", "Sneasel",
}


class TestEncounterRates:
    """Every route's encounter rates must sum to 1.0."""

    @pytest.mark.parametrize("version", [FR, LG])
    def test_rates_sum_to_one(self, version):
        for route_name, route in ENCOUNTER_TABLES[version].items():
            total = sum(slot.rate for slot in route.encounter_slots)
            assert abs(total - 1.0) < 0.011, (
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
    """Spot-check known encounter data against the decompilation."""

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
        """Abra appears on Route 24 in multiple level slots (Lv8, Lv10, Lv12)."""
        for version in [FR, LG]:
            route = ENCOUNTER_TABLES[version]["Route 24"]
            abra_slots = [s for s in route.encounter_slots if s.pokemon_name == "Abra"]
            assert len(abra_slots) >= 1
            total_rate = sum(s.rate for s in abra_slots)
            assert abs(total_rate - 0.15) < 0.01

    def test_abra_flees(self):
        assert POKEMON["Abra"].flees is True

    def test_no_other_pokemon_flees(self):
        fleeing = [p.name for p in POKEMON.values() if p.flees and p.name != "Abra"]
        assert not fleeing, f"Unexpected fleeing Pokemon: {fleeing}"

    def test_cerulean_cave_has_wobbuffet(self):
        """Wobbuffet is a rare encounter in Cerulean Cave (from decompilation)."""
        route = ENCOUNTER_TABLES[FR]["Cerulean Cave 1F"]
        names = {s.pokemon_name for s in route.encounter_slots}
        assert "Wobbuffet" in names

    def test_surf_encounters_exist(self):
        """Surf encounter tables should exist for water routes."""
        assert "Route 19 (Surf)" in ENCOUNTER_TABLES[FR]
        assert "Pallet Town (Surf)" in ENCOUNTER_TABLES[FR]

    def test_fishing_encounters_exist(self):
        """Fishing encounter tables should exist."""
        assert "Route 4 (Old Rod)" in ENCOUNTER_TABLES[FR]
        assert "Route 4 (Good Rod)" in ENCOUNTER_TABLES[FR]
        assert "Route 4 (Super Rod)" in ENCOUNTER_TABLES[FR]

    def test_safari_zone_super_rod_has_dratini(self):
        """Dratini is catchable via Super Rod in Safari Zone."""
        route = ENCOUNTER_TABLES[FR]["Safari Zone Center (Super Rod)"]
        names = {s.pokemon_name for s in route.encounter_slots}
        assert "Dratini" in names

    def test_sevii_islands_exist(self):
        """Sevii Islands (post-game) locations should be present."""
        for version in [FR, LG]:
            routes = ENCOUNTER_TABLES[version]
            assert "Kindle Road" in routes
            assert "Berry Forest" in routes
            assert "Icefall Cave 1F" in routes
            assert "Lost Cave" in routes
            assert "Pattern Bush" in routes
            assert "Sevault Canyon" in routes
            assert "Mt. Ember Exterior" in routes

    def test_lost_cave_has_ghost_types(self):
        """Lost Cave should have Gastly/Haunter."""
        for version in [FR, LG]:
            route = ENCOUNTER_TABLES[version]["Lost Cave"]
            names = {s.pokemon_name for s in route.encounter_slots}
            assert "Gastly" in names
            assert "Haunter" in names

    def test_tanoby_ruins_has_unown(self):
        """Tanoby Ruins Monean Chamber should have Unown."""
        for version in [FR, LG]:
            route = ENCOUNTER_TABLES[version]["Tanoby Ruins Monean Chamber"]
            names = {s.pokemon_name for s in route.encounter_slots}
            assert names == {"Unown"}

    def test_pattern_bush_has_heracross(self):
        """Heracross is found in Pattern Bush in both versions."""
        for version in [FR, LG]:
            route = ENCOUNTER_TABLES[version]["Pattern Bush"]
            names = {s.pokemon_name for s in route.encounter_slots}
            assert "Heracross" in names

    def test_kindle_road_has_ponyta(self):
        """Ponyta is a common encounter on Kindle Road."""
        route = ENCOUNTER_TABLES[FR]["Kindle Road"]
        names = {s.pokemon_name for s in route.encounter_slots}
        assert "Ponyta" in names


class TestSoftResetPokemon:
    """Soft reset targets must be correctly categorized."""

    def test_starters(self):
        starters = {n for n, d in SOFT_RESET_POKEMON.items() if d["category"] == "Starter"}
        assert starters == {"Bulbasaur", "Charmander", "Squirtle"}

    def test_legendaries(self):
        legends = {n for n, d in SOFT_RESET_POKEMON.items() if d["category"] == "Legendary"}
        assert legends == {"Articuno", "Zapdos", "Moltres", "Mewtwo"}

    def test_roaming_beasts(self):
        roaming = {n for n, d in SOFT_RESET_POKEMON.items() if d["category"] == "Roaming Legendary"}
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


class TestDataCompleteness:
    """Verify we have a reasonable number of locations."""

    @pytest.mark.parametrize("version", [FR, LG])
    def test_minimum_location_count(self, version):
        """We should have at least 200 locations (grass + surf + fishing + Sevii)."""
        count = len(ENCOUNTER_TABLES[version])
        assert count >= 200, f"Only {count} locations for {version.value}"

    @pytest.mark.parametrize("version", [FR, LG])
    def test_has_surf_locations(self, version):
        surf = [k for k in ENCOUNTER_TABLES[version] if "(Surf)" in k]
        assert len(surf) >= 10, f"Only {len(surf)} surf locations"

    @pytest.mark.parametrize("version", [FR, LG])
    def test_has_fishing_locations(self, version):
        fishing = [k for k in ENCOUNTER_TABLES[version]
                   if "(Old Rod)" in k or "(Good Rod)" in k or "(Super Rod)" in k]
        assert len(fishing) >= 20, f"Only {len(fishing)} fishing locations"
