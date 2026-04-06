"""Generate encounters.py from the pokefirered decompilation data.

This reads wild_encounters.json (from github.com/pret/pokefirered)
and outputs a complete, accurate encounters.py file.

Run: python generate_encounters.py
"""

import json
from pathlib import Path

SOURCE = Path("wild_encounters.json")
OUTPUT = Path("shiny_pokemon/data/encounters.py")

# Gen 3 encounter slot rates (hardcoded in the GBA engine)
LAND_RATES = [0.20, 0.20, 0.10, 0.10, 0.10, 0.10, 0.05, 0.05, 0.04, 0.04, 0.01, 0.01]
SURF_RATES = [0.60, 0.30, 0.05, 0.04, 0.01]
ROCK_RATES = [0.60, 0.30, 0.05, 0.04, 0.01]
# Fishing: indices 0-1 = Old Rod, 2-4 = Good Rod, 5-9 = Super Rod
OLD_ROD_RATES = [0.70, 0.30]
GOOD_ROD_RATES = [0.60, 0.20, 0.20]
SUPER_ROD_RATES = [0.40, 0.40, 0.15, 0.04, 0.01]

# Friendly names for the decompilation map constants
MAP_NAMES = {
    "MAP_ROUTE1": "Route 1",
    "MAP_ROUTE2": "Route 2",
    "MAP_ROUTE3": "Route 3",
    "MAP_ROUTE4": "Route 4",
    "MAP_ROUTE5": "Route 5",
    "MAP_ROUTE6": "Route 6",
    "MAP_ROUTE7": "Route 7",
    "MAP_ROUTE8": "Route 8",
    "MAP_ROUTE9": "Route 9",
    "MAP_ROUTE10": "Route 10",
    "MAP_ROUTE11": "Route 11",
    "MAP_ROUTE12": "Route 12",
    "MAP_ROUTE13": "Route 13",
    "MAP_ROUTE14": "Route 14",
    "MAP_ROUTE15": "Route 15",
    "MAP_ROUTE16": "Route 16",
    "MAP_ROUTE17": "Route 17",
    "MAP_ROUTE18": "Route 18",
    "MAP_ROUTE19": "Route 19",
    "MAP_ROUTE20": "Route 20",
    "MAP_ROUTE21_NORTH": "Route 21 North",
    "MAP_ROUTE21_SOUTH": "Route 21 South",
    "MAP_ROUTE22": "Route 22",
    "MAP_ROUTE23": "Route 23",
    "MAP_ROUTE24": "Route 24",
    "MAP_ROUTE25": "Route 25",
    "MAP_VIRIDIAN_FOREST": "Viridian Forest",
    "MAP_MT_MOON_1F": "Mt. Moon 1F",
    "MAP_MT_MOON_B1F": "Mt. Moon B1F",
    "MAP_MT_MOON_B2F": "Mt. Moon B2F",
    "MAP_DIGLETTS_CAVE_B1F": "Diglett's Cave",
    "MAP_ROCK_TUNNEL_1F": "Rock Tunnel 1F",
    "MAP_ROCK_TUNNEL_B1F": "Rock Tunnel B1F",
    "MAP_POKEMON_TOWER_3F": "Pokemon Tower 3F",
    "MAP_POKEMON_TOWER_4F": "Pokemon Tower 4F",
    "MAP_POKEMON_TOWER_5F": "Pokemon Tower 5F",
    "MAP_POKEMON_TOWER_6F": "Pokemon Tower 6F",
    "MAP_POKEMON_TOWER_7F": "Pokemon Tower 7F",
    "MAP_POWER_PLANT": "Power Plant",
    "MAP_POKEMON_MANSION_1F": "Pokemon Mansion 1F",
    "MAP_POKEMON_MANSION_2F": "Pokemon Mansion 2F",
    "MAP_POKEMON_MANSION_3F": "Pokemon Mansion 3F",
    "MAP_POKEMON_MANSION_B1F": "Pokemon Mansion B1F",
    "MAP_SAFARI_ZONE_CENTER": "Safari Zone Center",
    "MAP_SAFARI_ZONE_EAST": "Safari Zone East",
    "MAP_SAFARI_ZONE_NORTH": "Safari Zone North",
    "MAP_SAFARI_ZONE_WEST": "Safari Zone West",
    "MAP_SEAFOAM_ISLANDS_1F": "Seafoam Islands 1F",
    "MAP_SEAFOAM_ISLANDS_B1F": "Seafoam Islands B1F",
    "MAP_SEAFOAM_ISLANDS_B2F": "Seafoam Islands B2F",
    "MAP_SEAFOAM_ISLANDS_B3F": "Seafoam Islands B3F",
    "MAP_SEAFOAM_ISLANDS_B4F": "Seafoam Islands B4F",
    "MAP_VICTORY_ROAD_1F": "Victory Road 1F",
    "MAP_VICTORY_ROAD_2F": "Victory Road 2F",
    "MAP_VICTORY_ROAD_3F": "Victory Road 3F",
    "MAP_CERULEAN_CAVE_1F": "Cerulean Cave 1F",
    "MAP_CERULEAN_CAVE_2F": "Cerulean Cave 2F",
    "MAP_CERULEAN_CAVE_B1F": "Cerulean Cave B1F",
    "MAP_PALLET_TOWN": "Pallet Town",
    "MAP_VIRIDIAN_CITY": "Viridian City",
    "MAP_CERULEAN_CITY": "Cerulean City",
    "MAP_VERMILION_CITY": "Vermilion City",
    "MAP_CELADON_CITY": "Celadon City",
    "MAP_FUCHSIA_CITY": "Fuchsia City",
    "MAP_CINNABAR_ISLAND": "Cinnabar Island",
    "MAP_SSANNE_EXTERIOR": "S.S. Anne",
    # --- Sevii Islands (post-game) ---
    "MAP_ONE_ISLAND": "One Island",
    "MAP_ONE_ISLAND_KINDLE_ROAD": "Kindle Road",
    "MAP_ONE_ISLAND_TREASURE_BEACH": "Treasure Beach",
    "MAP_TWO_ISLAND_CAPE_BRINK": "Cape Brink",
    "MAP_THREE_ISLAND_BERRY_FOREST": "Berry Forest",
    "MAP_THREE_ISLAND_BOND_BRIDGE": "Bond Bridge",
    "MAP_THREE_ISLAND_PORT": "Three Isle Port",
    "MAP_FOUR_ISLAND": "Four Island",
    "MAP_FOUR_ISLAND_ICEFALL_CAVE_ENTRANCE": "Icefall Cave Entrance",
    "MAP_FOUR_ISLAND_ICEFALL_CAVE_1F": "Icefall Cave 1F",
    "MAP_FOUR_ISLAND_ICEFALL_CAVE_B1F": "Icefall Cave B1F",
    "MAP_FOUR_ISLAND_ICEFALL_CAVE_BACK": "Icefall Cave Back",
    "MAP_FIVE_ISLAND": "Five Island",
    "MAP_FIVE_ISLAND_LOST_CAVE_ROOM1": "Lost Cave",
    "MAP_FIVE_ISLAND_MEADOW": "Five Isle Meadow",
    "MAP_FIVE_ISLAND_MEMORIAL_PILLAR": "Memorial Pillar",
    "MAP_FIVE_ISLAND_RESORT_GORGEOUS": "Resort Gorgeous",
    "MAP_FIVE_ISLAND_WATER_LABYRINTH": "Water Labyrinth",
    "MAP_SIX_ISLAND_GREEN_PATH": "Green Path",
    "MAP_SIX_ISLAND_OUTCAST_ISLAND": "Outcast Island",
    "MAP_SIX_ISLAND_PATTERN_BUSH": "Pattern Bush",
    "MAP_SIX_ISLAND_RUIN_VALLEY": "Ruin Valley",
    "MAP_SIX_ISLAND_WATER_PATH": "Water Path",
    "MAP_SEVEN_ISLAND_SEVAULT_CANYON_ENTRANCE": "Sevault Canyon Entrance",
    "MAP_SEVEN_ISLAND_SEVAULT_CANYON": "Sevault Canyon",
    "MAP_SEVEN_ISLAND_TANOBY_RUINS": "Tanoby Ruins",
    "MAP_SEVEN_ISLAND_TANOBY_RUINS_MONEAN_CHAMBER": "Tanoby Ruins Monean Chamber",
    "MAP_SEVEN_ISLAND_TRAINER_TOWER": "Trainer Tower",
    "MAP_MT_EMBER_EXTERIOR": "Mt. Ember Exterior",
    "MAP_MT_EMBER_SUMMIT_PATH_1F": "Mt. Ember Summit 1F",
    "MAP_MT_EMBER_SUMMIT_PATH_2F": "Mt. Ember Summit 2F",
    "MAP_MT_EMBER_RUBY_PATH_1F": "Mt. Ember Ruby Path 1F",
    "MAP_MT_EMBER_RUBY_PATH_B1F": "Mt. Ember Ruby Path B1F",
    "MAP_MT_EMBER_RUBY_PATH_B2F": "Mt. Ember Ruby Path B2F",
    "MAP_MT_EMBER_RUBY_PATH_B3F": "Mt. Ember Ruby Path B3F",
}

CAVE_KEYWORDS = [
    "Cave", "Moon", "Tunnel", "Tower", "Plant", "Mansion",
    "Victory", "Seafoam", "Ember", "Tanoby", "Canyon",
]


def species_name(raw: str) -> str:
    """SPECIES_PIDGEY -> Pidgey"""
    name = raw.replace("SPECIES_", "").replace("_", " ").title()
    # Fix special names
    fixes = {
        "Nidoran F": "Nidoran F",
        "Nidoran M": "Nidoran M",
        "Mr Mime": "Mr. Mime",
        "Farfetchd": "Farfetch'd",
        "Ho Oh": "Ho-Oh",
    }
    for wrong, right in fixes.items():
        if name == wrong:
            name = right
    return name


def merge_slots(mons, rates):
    """Combine duplicate species in adjacent slots by summing rates."""
    merged = []
    seen = {}
    for mon, rate in zip(mons, rates):
        name = species_name(mon["species"])
        lmin = mon["min_level"]
        lmax = mon["max_level"]
        key = (name, lmin, lmax)
        if key in seen:
            idx = seen[key]
            old = merged[idx]
            merged[idx] = (old[0], round(old[1] + rate, 2), old[2], old[3])
        else:
            seen[key] = len(merged)
            merged.append((name, round(rate, 2), lmin, lmax))
    return merged


def slots_equal(a, b):
    """Check if two slot lists are identical."""
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x["species"] != y["species"]:
            return False
        if x["min_level"] != y["min_level"]:
            return False
        if x["max_level"] != y["max_level"]:
            return False
    return True


def etype_for_name(name: str, is_water: bool = False) -> str:
    """Determine encounter type string from location name."""
    if is_water:
        return "SURF"
    if any(kw in name for kw in CAVE_KEYWORDS):
        return "CAVE"
    return "GRASS"


def format_route(name: str, etype: str, slots: list) -> str:
    """Format one route entry as Python code."""
    lines = [f'    "{name}": _route("{name}", {etype},']
    for s in slots:
        lines.append(f'        E("{s[0]}", {s[1]}, {s[2]}, {s[3]}),')
    lines.append("    ),")
    return "\n".join(lines)


def main():
    with open(SOURCE) as f:
        data = json.load(f)

    all_encounters = data["wild_encounter_groups"][0]["encounters"]

    # Split into FR and LG, keyed by map name
    fr = {}
    lg = {}
    for e in all_encounters:
        m = e["map"]
        if m not in MAP_NAMES:
            continue
        label = e.get("base_label", "")
        if "FireRed" in label:
            fr[m] = e
        elif "LeafGreen" in label:
            lg[m] = e

    shared_routes = {}
    fr_only_routes = {}
    lg_only_routes = {}

    for m in sorted(MAP_NAMES.keys(), key=lambda x: MAP_NAMES[x]):
        name = MAP_NAMES[m]
        fr_e = fr.get(m)
        lg_e = lg.get(m)
        if not fr_e or not lg_e:
            continue

        # --- Land/Cave encounters ---
        if "land_mons" in fr_e:
            fr_mons = fr_e["land_mons"]["mons"]
            lg_mons = lg_e["land_mons"]["mons"]
            same = slots_equal(fr_mons, lg_mons)
            etype = etype_for_name(name)

            fr_slots = merge_slots(fr_mons, LAND_RATES)
            lg_slots = merge_slots(lg_mons, LAND_RATES)

            if same:
                shared_routes[name] = format_route(name, etype, fr_slots)
            else:
                fr_only_routes[name] = format_route(name, etype, fr_slots)
                lg_only_routes[name] = format_route(name, etype, lg_slots)

        # --- Surf encounters ---
        if "water_mons" in fr_e:
            fr_mons = fr_e["water_mons"]["mons"]
            lg_mons = lg_e["water_mons"]["mons"]
            same = slots_equal(fr_mons, lg_mons)

            surf_name = f"{name} (Surf)"
            fr_slots = merge_slots(fr_mons, SURF_RATES)
            lg_slots = merge_slots(lg_mons, SURF_RATES)

            if same:
                shared_routes[surf_name] = format_route(surf_name, "SURF", fr_slots)
            else:
                fr_only_routes[surf_name] = format_route(surf_name, "SURF", fr_slots)
                lg_only_routes[surf_name] = format_route(surf_name, "SURF", lg_slots)

        # --- Fishing encounters ---
        if "fishing_mons" in fr_e:
            fr_fish = fr_e["fishing_mons"]["mons"]
            lg_fish = lg_e["fishing_mons"]["mons"]

            for rod_name, start, end, rates, etype in [
                ("Old Rod", 0, 2, OLD_ROD_RATES, "OLD_ROD"),
                ("Good Rod", 2, 5, GOOD_ROD_RATES, "GOOD_ROD"),
                ("Super Rod", 5, 10, SUPER_ROD_RATES, "SUPER_ROD"),
            ]:
                full_name = f"{name} ({rod_name})"
                fr_rod = fr_fish[start:end]
                lg_rod = lg_fish[start:end]
                same = slots_equal(fr_rod, lg_rod)

                fr_slots = merge_slots(fr_rod, rates)
                lg_slots = merge_slots(lg_rod, rates)

                if same:
                    shared_routes[full_name] = format_route(full_name, etype, fr_slots)
                else:
                    fr_only_routes[full_name] = format_route(full_name, etype, fr_slots)
                    lg_only_routes[full_name] = format_route(full_name, etype, lg_slots)

    # --- Build output file ---
    lines = []
    lines.append('"""Complete FR/LG encounter tables.')
    lines.append("")
    lines.append("Auto-generated from the pokefirered decompilation")
    lines.append("(github.com/pret/pokefirered, src/data/wild_encounters.json).")
    lines.append("This is the actual game data, not from fan wikis.")
    lines.append("")
    lines.append("Gen 3 encounter slot rates (hardcoded in the GBA engine):")
    lines.append("  Grass/Cave: 20, 20, 10, 10, 10, 10, 5, 5, 4, 4, 1, 1%")
    lines.append("  Surf:       60, 30, 5, 4, 1%")
    lines.append("  Old Rod:    70, 30%")
    lines.append("  Good Rod:   60, 20, 20%")
    lines.append("  Super Rod:  40, 40, 15, 4, 1%")
    lines.append('"""')
    lines.append("")
    lines.append("from shiny_pokemon.data.routes import (")
    lines.append("    EncounterSlot as E,")
    lines.append("    EncounterType,")
    lines.append("    GameVersion,")
    lines.append("    RouteData,")
    lines.append(")")
    lines.append("")
    lines.append("# Shorthand")
    lines.append("GRASS = EncounterType.GRASS")
    lines.append("CAVE = EncounterType.CAVE")
    lines.append("SURF = EncounterType.SURF")
    lines.append("OLD_ROD = EncounterType.OLD_ROD")
    lines.append("GOOD_ROD = EncounterType.GOOD_ROD")
    lines.append("SUPER_ROD = EncounterType.SUPER_ROD")
    lines.append("FR = GameVersion.FIRE_RED")
    lines.append("LG = GameVersion.LEAF_GREEN")
    lines.append("")
    lines.append("")
    lines.append('def _route(name: str, etype: EncounterType, *slots: E) -> RouteData:')
    lines.append("    return RouteData(name=name, encounter_type=etype, encounter_slots=tuple(slots))")
    lines.append("")
    lines.append("")

    # Shared routes
    lines.append("# " + "=" * 66)
    lines.append("# Shared routes (identical in Fire Red and Leaf Green)")
    lines.append("# " + "=" * 66)
    lines.append("")
    lines.append("_SHARED_ROUTES: dict[str, RouteData] = {")
    for name in sorted(shared_routes.keys()):
        lines.append(shared_routes[name])
    lines.append("}")
    lines.append("")

    # FR-only routes
    lines.append("# " + "=" * 66)
    lines.append("# Fire Red only (version-exclusive Pokemon)")
    lines.append("# " + "=" * 66)
    lines.append("")
    lines.append("_FIRE_RED_ROUTES: dict[str, RouteData] = {")
    for name in sorted(fr_only_routes.keys()):
        lines.append(fr_only_routes[name])
    lines.append("}")
    lines.append("")

    # LG-only routes
    lines.append("# " + "=" * 66)
    lines.append("# Leaf Green only (version-exclusive Pokemon)")
    lines.append("# " + "=" * 66)
    lines.append("")
    lines.append("_LEAF_GREEN_ROUTES: dict[str, RouteData] = {")
    for name in sorted(lg_only_routes.keys()):
        lines.append(lg_only_routes[name])
    lines.append("}")
    lines.append("")

    # ENCOUNTER_TABLES
    lines.append("")
    lines.append("# " + "=" * 66)
    lines.append("# Combined lookup tables")
    lines.append("# " + "=" * 66)
    lines.append("")
    lines.append("ENCOUNTER_TABLES: dict[GameVersion, dict[str, RouteData]] = {")
    lines.append("    FR: {**_SHARED_ROUTES, **_FIRE_RED_ROUTES},")
    lines.append("    LG: {**_SHARED_ROUTES, **_LEAF_GREEN_ROUTES},")
    lines.append("}")
    lines.append("")

    # Soft reset Pokemon (unchanged)
    lines.append("")
    lines.append("# " + "=" * 66)
    lines.append("# Soft-resettable Pokemon (not in wild encounter tables)")
    lines.append("# " + "=" * 66)
    lines.append("")
    lines.append('SOFT_RESET_POKEMON: dict[str, dict] = {')
    lines.append('    "Bulbasaur": {')
    lines.append('        "location": "Pallet Town (Prof. Oak\'s Lab)",')
    lines.append('        "category": "Starter",')
    lines.append("    },")
    lines.append('    "Charmander": {')
    lines.append('        "location": "Pallet Town (Prof. Oak\'s Lab)",')
    lines.append('        "category": "Starter",')
    lines.append("    },")
    lines.append('    "Squirtle": {')
    lines.append('        "location": "Pallet Town (Prof. Oak\'s Lab)",')
    lines.append('        "category": "Starter",')
    lines.append("    },")
    lines.append('    "Articuno": {')
    lines.append('        "location": "Seafoam Islands B4F",')
    lines.append('        "category": "Legendary",')
    lines.append("    },")
    lines.append('    "Zapdos": {')
    lines.append('        "location": "Power Plant",')
    lines.append('        "category": "Legendary",')
    lines.append("    },")
    lines.append('    "Moltres": {')
    lines.append('        "location": "Mt. Ember Summit",')
    lines.append('        "category": "Legendary",')
    lines.append("    },")
    lines.append('    "Mewtwo": {')
    lines.append('        "location": "Cerulean Cave B1F",')
    lines.append('        "category": "Legendary",')
    lines.append("    },")
    lines.append('    "Raikou": {')
    lines.append('        "location": "Roaming (choose Squirtle)",')
    lines.append('        "category": "Roaming Legendary",')
    lines.append("    },")
    lines.append('    "Entei": {')
    lines.append('        "location": "Roaming (choose Bulbasaur)",')
    lines.append('        "category": "Roaming Legendary",')
    lines.append("    },")
    lines.append('    "Suicune": {')
    lines.append('        "location": "Roaming (choose Charmander)",')
    lines.append('        "category": "Roaming Legendary",')
    lines.append("    },")
    lines.append('    "Eevee": {')
    lines.append('        "location": "Celadon Condominiums",')
    lines.append('        "category": "Gift",')
    lines.append("    },")
    lines.append('    "Hitmonlee": {')
    lines.append('        "location": "Saffron City (Fighting Dojo)",')
    lines.append('        "category": "Gift",')
    lines.append("    },")
    lines.append('    "Hitmonchan": {')
    lines.append('        "location": "Saffron City (Fighting Dojo)",')
    lines.append('        "category": "Gift",')
    lines.append("    },")
    lines.append('    "Lapras": {')
    lines.append('        "location": "Silph Co. 7F",')
    lines.append('        "category": "Gift",')
    lines.append("    },")
    lines.append('    "Omanyte": {')
    lines.append('        "location": "Cinnabar Island Lab (Helix Fossil)",')
    lines.append('        "category": "Fossil",')
    lines.append("    },")
    lines.append('    "Kabuto": {')
    lines.append('        "location": "Cinnabar Island Lab (Dome Fossil)",')
    lines.append('        "category": "Fossil",')
    lines.append("    },")
    lines.append('    "Aerodactyl": {')
    lines.append('        "location": "Cinnabar Island Lab (Old Amber)",')
    lines.append('        "category": "Fossil",')
    lines.append("    },")
    lines.append('    "Snorlax": {')
    lines.append('        "location": "Route 12 / Route 16 (blocking the path)",')
    lines.append('        "category": "Static",')
    lines.append("    },")
    lines.append('    "Lugia": {')
    lines.append('        "location": "Navel Rock (MysticTicket event)",')
    lines.append('        "category": "Event Legendary",')
    lines.append("    },")
    lines.append('    "Ho-Oh": {')
    lines.append('        "location": "Navel Rock (MysticTicket event)",')
    lines.append('        "category": "Event Legendary",')
    lines.append("    },")
    lines.append('    "Deoxys": {')
    lines.append('        "location": "Birth Island (AuroraTicket event)",')
    lines.append('        "category": "Event Legendary",')
    lines.append("    },")
    lines.append("}")
    lines.append("")

    output = "\n".join(lines)
    OUTPUT.write_text(output, encoding="utf-8")

    # Stats
    total = len(shared_routes) + len(fr_only_routes) + len(lg_only_routes)
    print(f"Generated {OUTPUT}")
    print(f"  Shared locations:    {len(shared_routes)}")
    print(f"  Fire Red exclusive:  {len(fr_only_routes)}")
    print(f"  Leaf Green exclusive:{len(lg_only_routes)}")
    print(f"  Total entries:       {total}")


if __name__ == "__main__":
    main()
