"""Pokemon search dialog: type a name, see where to find it.

Also tells you if a Pokemon isn't available in Fire Red or Leaf Green.
"""

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCompleter,
    QPushButton,
)
from PySide6.QtCore import Qt

from shiny_pokemon.data import ENCOUNTER_TABLES, SOFT_RESET_POKEMON, POKEMON, GameVersion


# Pokemon that exist in Gen 1-3 but are NOT obtainable in FR/LG at all.
# Grouped by where you CAN get them.
NOT_IN_FRLG = {
    # Gen 2 starters
    "Chikorita": "Gold/Silver/Crystal or Emerald",
    "Bayleef": "Evolve Chikorita",
    "Meganium": "Evolve Bayleef",
    "Cyndaquil": "Gold/Silver/Crystal or Emerald",
    "Quilava": "Evolve Cyndaquil",
    "Typhlosion": "Evolve Quilava",
    "Totodile": "Gold/Silver/Crystal or Emerald",
    "Croconaw": "Evolve Totodile",
    "Feraligatr": "Evolve Croconaw",
    # Gen 2 Pokemon not in FR/LG
    "Hoothoot": "Gold/Silver/Crystal or Colosseum",
    "Noctowl": "Evolve Hoothoot",
    "Chinchou": "Ruby/Sapphire/Emerald",
    "Lanturn": "Evolve Chinchou",
    "Togepi": "Gold/Silver/Crystal or Colosseum",
    "Togetic": "Evolve Togepi",
    "Flaaffy": "Evolve Mareep",
    "Ampharos": "Evolve Flaaffy",
    "Sudowoodo": "Gold/Silver/Crystal or Emerald",
    "Politoed": "Trade Poliwhirl holding King's Rock",
    "Aipom": "Gold/Silver/Crystal",
    "Sunkern": "Gold/Silver/Crystal or Colosseum",
    "Sunflora": "Evolve Sunkern",
    "Espeon": "Evolve Eevee (friendship, daytime)",
    "Umbreon": "Evolve Eevee (friendship, nighttime)",
    "Slowking": "Trade Slowpoke holding King's Rock",
    "Mareep": "Gold/Silver/Crystal or Colosseum",
    "Girafarig": "Gold/Silver/Crystal or Emerald",
    "Pineco": "Gold/Silver/Crystal or Colosseum",
    "Forretress": "Evolve Pineco",
    "Gligar": "Gold/Silver/Crystal or Emerald",
    "Steelix": "Trade Onix holding Metal Coat",
    "Snubbull": "Gold/Silver/Crystal or Colosseum",
    "Granbull": "Evolve Snubbull",
    "Scizor": "Trade Scyther holding Metal Coat",
    "Shuckle": "Gold/Silver/Crystal or Colosseum",
    "Teddiursa": "Gold/Silver/Crystal or Colosseum",
    "Ursaring": "Evolve Teddiursa",
    "Corsola": "Ruby/Sapphire/Emerald",
    "Houndour": "Gold/Silver/Crystal or Colosseum",
    "Houndoom": "Evolve Houndour",
    "Kingdra": "Trade Seadra holding Dragon Scale",
    "Porygon2": "Trade Porygon holding Up-Grade",
    "Stantler": "Gold/Silver/Crystal",
    "Smeargle": "Gold/Silver/Crystal or Emerald",
    "Tyrogue": "Gold/Silver/Crystal",
    "Hitmontop": "Evolve Tyrogue (Atk = Def)",
    "Smoochum": "Breed Jynx",
    "Elekid": "Breed Electabuzz",
    "Magby": "Breed Magmar",
    "Miltank": "Gold/Silver/Crystal or Colosseum",
    "Blissey": "Evolve Chansey (friendship)",
    "Celebi": "Event only (Japan, Colosseum bonus disc)",
    # Gen 3 starters
    "Treecko": "Ruby/Sapphire/Emerald",
    "Grovyle": "Evolve Treecko",
    "Sceptile": "Evolve Grovyle",
    "Torchic": "Ruby/Sapphire/Emerald",
    "Combusken": "Evolve Torchic",
    "Blaziken": "Evolve Combusken",
    "Mudkip": "Ruby/Sapphire/Emerald",
    "Marshtomp": "Evolve Mudkip",
    "Swampert": "Evolve Marshtomp",
    # Gen 3 Pokemon not in FR/LG
    "Azurill": "Breed Marill (with Sea Incense)",
    "Skitty": "Ruby/Sapphire/Emerald",
    "Delcatty": "Evolve Skitty",
    "Poochyena": "Ruby/Sapphire/Emerald",
    "Mightyena": "Evolve Poochyena",
    "Zigzagoon": "Ruby/Sapphire/Emerald",
    "Linoone": "Evolve Zigzagoon",
    "Wurmple": "Ruby/Sapphire/Emerald",
    "Silcoon": "Evolve Wurmple",
    "Beautifly": "Evolve Silcoon",
    "Cascoon": "Evolve Wurmple",
    "Dustox": "Evolve Cascoon",
    "Lotad": "Ruby/Sapphire/Emerald",
    "Lombre": "Evolve Lotad",
    "Ludicolo": "Evolve Lombre",
    "Seedot": "Ruby/Sapphire/Emerald",
    "Nuzleaf": "Evolve Seedot",
    "Shiftry": "Evolve Nuzleaf",
    "Taillow": "Ruby/Sapphire/Emerald",
    "Swellow": "Evolve Taillow",
    "Wingull": "Ruby/Sapphire/Emerald",
    "Pelipper": "Evolve Wingull",
    "Ralts": "Ruby/Sapphire/Emerald",
    "Kirlia": "Evolve Ralts",
    "Gardevoir": "Evolve Kirlia",
    "Surskit": "Ruby/Sapphire/Emerald",
    "Masquerain": "Evolve Surskit",
    "Shroomish": "Ruby/Sapphire/Emerald",
    "Breloom": "Evolve Shroomish",
    "Slakoth": "Ruby/Sapphire/Emerald",
    "Vigoroth": "Evolve Slakoth",
    "Slaking": "Evolve Vigoroth",
    "Nincada": "Ruby/Sapphire/Emerald",
    "Ninjask": "Evolve Nincada",
    "Shedinja": "Evolve Nincada (empty party slot)",
    "Whismur": "Ruby/Sapphire/Emerald",
    "Loudred": "Evolve Whismur",
    "Exploud": "Evolve Loudred",
    "Makuhita": "Ruby/Sapphire/Emerald",
    "Hariyama": "Evolve Makuhita",
    "Nosepass": "Ruby/Sapphire/Emerald",
    "Sableye": "Ruby/Sapphire/Emerald",
    "Mawile": "Ruby/Sapphire/Emerald",
    "Aron": "Ruby/Sapphire/Emerald",
    "Lairon": "Evolve Aron",
    "Aggron": "Evolve Lairon",
    "Meditite": "Ruby/Sapphire/Emerald",
    "Medicham": "Evolve Meditite",
    "Electrike": "Ruby/Sapphire/Emerald",
    "Manectric": "Evolve Electrike",
    "Plusle": "Ruby/Sapphire/Emerald",
    "Minun": "Ruby/Sapphire/Emerald",
    "Volbeat": "Ruby/Sapphire/Emerald",
    "Illumise": "Ruby/Sapphire/Emerald",
    "Roselia": "Ruby/Sapphire/Emerald",
    "Gulpin": "Ruby/Sapphire/Emerald",
    "Swalot": "Evolve Gulpin",
    "Carvanha": "Ruby/Sapphire/Emerald",
    "Sharpedo": "Evolve Carvanha",
    "Wailmer": "Ruby/Sapphire/Emerald",
    "Wailord": "Evolve Wailmer",
    "Numel": "Ruby/Sapphire/Emerald",
    "Camerupt": "Evolve Numel",
    "Torkoal": "Ruby/Sapphire/Emerald",
    "Spoink": "Ruby/Sapphire/Emerald",
    "Grumpig": "Evolve Spoink",
    "Spinda": "Ruby/Sapphire/Emerald",
    "Trapinch": "Ruby/Sapphire/Emerald",
    "Vibrava": "Evolve Trapinch",
    "Flygon": "Evolve Vibrava",
    "Cacnea": "Ruby/Sapphire/Emerald",
    "Cacturne": "Evolve Cacnea",
    "Swablu": "Ruby/Sapphire/Emerald",
    "Altaria": "Evolve Swablu",
    "Zangoose": "Ruby/Sapphire/Emerald",
    "Seviper": "Ruby/Sapphire/Emerald",
    "Lunatone": "Ruby/Sapphire/Emerald",
    "Solrock": "Ruby/Sapphire/Emerald",
    "Barboach": "Ruby/Sapphire/Emerald",
    "Whiscash": "Evolve Barboach",
    "Corphish": "Ruby/Sapphire/Emerald",
    "Crawdaunt": "Evolve Corphish",
    "Baltoy": "Ruby/Sapphire/Emerald",
    "Claydol": "Evolve Baltoy",
    "Lileep": "Ruby/Sapphire/Emerald",
    "Cradily": "Evolve Lileep",
    "Anorith": "Ruby/Sapphire/Emerald",
    "Armaldo": "Evolve Anorith",
    "Feebas": "Ruby/Sapphire/Emerald",
    "Milotic": "Evolve Feebas",
    "Castform": "Ruby/Sapphire/Emerald",
    "Kecleon": "Ruby/Sapphire/Emerald",
    "Shuppet": "Ruby/Sapphire/Emerald",
    "Banette": "Evolve Shuppet",
    "Duskull": "Ruby/Sapphire/Emerald",
    "Dusclops": "Evolve Duskull",
    "Tropius": "Ruby/Sapphire/Emerald",
    "Chimecho": "Ruby/Sapphire/Emerald",
    "Absol": "Ruby/Sapphire/Emerald",
    "Wynaut": "Breed Wobbuffet",
    "Snorunt": "Ruby/Sapphire/Emerald",
    "Glalie": "Evolve Snorunt",
    "Spheal": "Ruby/Sapphire/Emerald",
    "Sealeo": "Evolve Spheal",
    "Walrein": "Evolve Sealeo",
    "Clamperl": "Ruby/Sapphire/Emerald",
    "Huntail": "Evolve Clamperl",
    "Gorebyss": "Evolve Clamperl",
    "Relicanth": "Ruby/Sapphire/Emerald",
    "Luvdisc": "Ruby/Sapphire/Emerald",
    "Bagon": "Ruby/Sapphire/Emerald",
    "Shelgon": "Evolve Bagon",
    "Salamence": "Evolve Shelgon",
    "Beldum": "Ruby/Sapphire/Emerald",
    "Metang": "Evolve Beldum",
    "Metagross": "Evolve Metang",
    "Regirock": "Ruby/Sapphire/Emerald",
    "Regice": "Ruby/Sapphire/Emerald",
    "Registeel": "Ruby/Sapphire/Emerald",
    "Latias": "Ruby/Sapphire/Emerald",
    "Latios": "Ruby/Sapphire/Emerald",
    "Kyogre": "Sapphire/Emerald",
    "Groudon": "Ruby/Emerald",
    "Rayquaza": "Ruby/Sapphire/Emerald",
    "Jirachi": "Colosseum bonus disc or event",
}


def build_pokemon_location_index():
    """Build a reverse lookup: Pokemon name -> list of locations.

    Returns a dict like:
        {"Pidgey": [
            {"location": "Route 1", "rate": 0.50, "levels": "2-5",
             "type": "Grass", "version": "Both"},
            ...
        ]}
    """
    index = {}

    for version in [GameVersion.FIRE_RED, GameVersion.LEAF_GREEN]:
        for route_name, route in ENCOUNTER_TABLES[version].items():
            for slot in route.encounter_slots:
                name = slot.pokemon_name
                if name not in index:
                    index[name] = []

                # Check if this exact location+rate+level already exists
                # from the other version
                existing = None
                for entry in index[name]:
                    if (entry["location"] == route_name
                            and entry["rate"] == slot.rate
                            and entry["levels"] == (str(slot.level_min) if slot.level_min == slot.level_max else f"{slot.level_min}-{slot.level_max}")):
                        existing = entry
                        break

                if existing:
                    if existing["version"] != "Both":
                        existing["version"] = "Both"
                else:
                    v = "Fire Red" if version == GameVersion.FIRE_RED else "Leaf Green"
                    index[name].append({
                        "location": route_name,
                        "rate": slot.rate,
                        "levels": str(slot.level_min) if slot.level_min == slot.level_max else f"{slot.level_min}-{slot.level_max}",
                        "type": route.encounter_type.value,
                        "version": v,
                    })

    # Add soft reset Pokemon (starters, legendaries, gifts, etc.)
    for name, info in SOFT_RESET_POKEMON.items():
        if name not in index:
            index[name] = []
        # Only add if not already listed at this location
        loc = info["location"]
        already = any(e["location"] == loc for e in index[name])
        if not already:
            index[name].append({
                "location": loc,
                "rate": 1.0,
                "levels": "-",
                "type": info["category"],
                "version": "Both",
            })

    return index


class PokemonSearchDialog(QDialog):
    """Dialog for searching where a Pokemon can be found."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Where can I find this Pokemon?")
        self.setMinimumSize(700, 500)

        # Build the location index once
        self._index = build_pokemon_location_index()
        self._all_names = sorted(
            set(list(self._index.keys()) + list(NOT_IN_FRLG.keys()) + list(POKEMON.keys()))
        )

        layout = QVBoxLayout(self)

        # Search input
        search_label = QLabel("Type a Pokemon name:")
        search_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(search_label)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("e.g. Pikachu, Dratini, Abra...")
        self.search_input.setStyleSheet("font-size: 16px; min-height: 32px; padding: 4px;")

        # Autocomplete
        completer = QCompleter(self._all_names)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.search_input.setCompleter(completer)
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)

        # Result label
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.result_label.setStyleSheet("font-size: 13px; padding: 8px;")
        layout.addWidget(self.result_label)

        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Location", "How", "Chance", "Levels", "Version"
        ])
        header = self.results_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.results_table)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

    def _on_search(self, text: str) -> None:
        """Search for a Pokemon and show results."""
        text = text.strip()
        if not text:
            self.result_label.setText("")
            self.results_table.setRowCount(0)
            return

        # Try exact match first, then case-insensitive
        name = None
        if text in self._index or text in NOT_IN_FRLG:
            name = text
        else:
            text_lower = text.lower()
            for n in self._all_names:
                if n.lower() == text_lower:
                    name = n
                    break

        if not name:
            # Partial match hint
            matches = [n for n in self._all_names if text.lower() in n.lower()]
            if matches:
                self.result_label.setText(
                    f'<span style="color: #aaa;">Did you mean: {", ".join(matches[:8])}?</span>'
                )
            else:
                self.result_label.setText(
                    f'<span style="color: #FF8C42;">No Pokemon named "{text}" found.</span>'
                )
            self.results_table.setRowCount(0)
            return

        # Check if it's not in FR/LG
        if name in NOT_IN_FRLG and name not in self._index:
            where = NOT_IN_FRLG[name]
            self.result_label.setText(
                f'<span style="color: #FF6B6B; font-size: 15px;">'
                f'{name} is not available in Fire Red or Leaf Green.</span>'
                f'<br><span style="color: #aaa;">Where to get it: {where}</span>'
            )
            self.results_table.setRowCount(0)
            return

        # Show locations
        if name in self._index:
            locations = sorted(self._index[name], key=lambda x: -x["rate"])

            count = len(locations)
            self.result_label.setText(
                f'<span style="color: #4ECDC4; font-size: 15px;">'
                f'{name} can be found in {count} location{"s" if count != 1 else ""}!</span>'
            )

            self.results_table.setRowCount(count)
            for i, loc in enumerate(locations):
                self.results_table.setItem(i, 0, QTableWidgetItem(loc["location"]))
                self.results_table.setItem(i, 1, QTableWidgetItem(loc["type"]))
                self.results_table.setItem(i, 2, QTableWidgetItem(f"{loc['rate'] * 100:.0f}%"))
                self.results_table.setItem(i, 3, QTableWidgetItem(loc["levels"]))
                self.results_table.setItem(i, 4, QTableWidgetItem(loc["version"]))
        else:
            self.result_label.setText(
                f'<span style="color: #FF8C42;">'
                f'{name} exists but has no wild encounters in FR/LG. '
                f'It might be available through evolution, gifts, or trades.</span>'
            )
            self.results_table.setRowCount(0)
