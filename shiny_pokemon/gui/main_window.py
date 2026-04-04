"""Main application window.

This is the central hub that creates all widgets and connects them.
The layout uses a left panel for controls and a right panel for charts.
"""

import json
import os
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QLabel,
    QComboBox,
    QSpinBox,
    QDoubleSpinBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
    QStatusBar,
    QHeaderView,
    QScrollArea,
    QFileDialog,
    QMessageBox,
    QLineEdit,
    QCompleter,
    QDialog,
    QDialogButtonBox,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer, QEvent

from shiny_pokemon.data import (
    ENCOUNTER_TABLES,
    SOFT_RESET_POKEMON,
    POKEMON,
    GameVersion,
)
from shiny_pokemon.data.routes import HuntMethod
from shiny_pokemon.shiny import ShinyOdds
from shiny_pokemon.simulation.monte_carlo import ShinyHuntSimulator
from shiny_pokemon.gui.charts.plotly_charts import (
    analytical_chart_html,
    simulation_histogram_html,
    empty_chart_html,
)
from shiny_pokemon.gui.pokemon_search import PokemonSearchDialog


# Where we save the hunt progress file
SAVE_DIR = Path.home() / ".shiny_pokemon"
SAVE_FILE = SAVE_DIR / "hunt_progress.json"

# Time presets: label -> seconds per attempt
TIME_PRESETS = {
    "Random encounter (~18s)": 18,
    "Soft reset: Starter (~35s)": 35,
    "Soft reset: Legendary (~50s)": 50,
    "Custom": None,
}


class SimulationWorker(QThread):
    """Runs Monte Carlo simulations in a background thread.

    This keeps the GUI responsive while simulations run.
    It emits signals (messages) that the main window listens to
    for updating the progress bar and charts.
    """

    # Signals are how threads communicate in Qt.
    # progress emits (completed_count, total_count, attempts_list)
    progress = Signal(int, int, list)
    finished = Signal(list)

    def __init__(
        self, effective_probability: float, num_trials: int, batch_size: int
    ) -> None:
        super().__init__()
        self.effective_probability = effective_probability
        self.num_trials = num_trials
        self.batch_size = batch_size
        self._should_stop = False

    def run(self) -> None:
        """This method runs in the background thread."""
        sim = ShinyHuntSimulator(self.effective_probability)
        for result in sim.run_incremental(self.num_trials, self.batch_size):
            if self._should_stop:
                break
            self.progress.emit(
                result.num_completed, self.num_trials, result.attempts
            )
        if not self._should_stop:
            self.finished.emit(result.attempts)

    def stop(self) -> None:
        self._should_stop = True


class MainWindow(QMainWindow):
    """The main application window with controls and charts."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Shiny Pokemon Calculator - Fire Red / Leaf Green")
        self.setMinimumSize(1200, 800)

        # State
        self.game = ShinyOdds(name="Fire Red", odds=8192)
        self.current_version = GameVersion.FIRE_RED
        self.current_method = HuntMethod.RANDOM_ENCOUNTER
        self.current_target = ""
        self.current_encounter_rate = 1.0
        self.worker = None
        self._encounter_type_keys = []
        self._active_route_key = ""
        self._updating = False  # Guard against signal cascades

        # Auto-save timer: saves 2 seconds after the last counter change
        # so we don't write to disk on every single click
        self._auto_save_timer = QTimer()
        self._auto_save_timer.setSingleShot(True)
        self._auto_save_timer.setInterval(2000)
        self._auto_save_timer.timeout.connect(self._auto_save)

        # Temp directory for chart HTML files (QWebEngineView.setHtml
        # has a 2MB limit, so we write to files and load via URL)
        import tempfile
        self._chart_dir = tempfile.mkdtemp(prefix="shiny_charts_")

        # Build UI
        self._build_ui()
        self._connect_signals()

        # Stop combo boxes from changing when you scroll past them.
        # Without this, scrolling the left panel accidentally changes
        # the route/version/target and reloads the chart.
        for combo in [
            self.version_combo, self.method_combo, self.route_combo,
            self.encounter_type_combo, self.target_combo,
            self.time_preset_combo,
        ]:
            combo.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            combo.installEventFilter(self)

        # Initialize with first route
        self._on_version_changed(0)

        # Try to restore a saved hunt from a previous session
        self._auto_load_progress()

        self.statusBar().showMessage("Pick a route and a Pokemon to get started!")

    def eventFilter(self, obj, event):
        """Block scroll wheel on combo boxes unless they have focus."""
        if isinstance(obj, QComboBox) and event.type() == QEvent.Type.Wheel:
            if not obj.hasFocus():
                return True  # Eat the event
        return super().eventFilter(obj, event)

    def _build_ui(self) -> None:
        """Create all widgets and arrange them in the layout."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # --- Left panel: controls ---
        left = QWidget()
        left.setMinimumWidth(350)
        left.setMaximumWidth(420)
        left_layout = QVBoxLayout(left)

        # Version selector
        version_group = QGroupBox("Game Version")
        version_layout = QVBoxLayout(version_group)
        self.version_combo = QComboBox()
        self.version_combo.addItems(["Fire Red", "Leaf Green"])
        version_layout.addWidget(self.version_combo)
        left_layout.addWidget(version_group)

        # Pokemon search button
        self.search_button = QPushButton("Where can I find a Pokemon?")
        self.search_button.setStyleSheet(
            "QPushButton { background-color: #4a3a6a; font-weight: bold;"
            " font-size: 13px; min-height: 34px; }"
            "QPushButton:hover { background-color: #5a4a7a; }"
        )
        self.search_button.clicked.connect(self._open_pokemon_search)
        left_layout.addWidget(self.search_button)

        # Method selector
        method_group = QGroupBox("How are you hunting?")
        method_layout = QVBoxLayout(method_group)
        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Walking in grass (Random Encounter)",
            "Save & reload (Soft Reset)",
        ])
        method_desc = QLabel(
            '<span style="color: #aaa; font-size: 11px;">'
            "Random = walking around hoping for a shiny.<br>"
            "Soft Reset = saving before picking a Pokemon,<br>"
            "then reloading if it's not shiny.</span>"
        )
        method_desc.setWordWrap(True)
        method_layout.addWidget(self.method_combo)
        method_layout.addWidget(method_desc)
        left_layout.addWidget(method_group)

        # Route selector (shown for random encounters)
        self.route_group = QGroupBox("Location")
        route_layout = QVBoxLayout(self.route_group)
        self.route_combo = QComboBox()
        route_layout.addWidget(self.route_combo)

        # Encounter type within this location (Grass, Surf, Old Rod, etc.)
        self.encounter_type_combo = QComboBox()
        self.encounter_type_combo.setVisible(False)
        route_layout.addWidget(self.encounter_type_combo)

        left_layout.addWidget(self.route_group)

        # Encounter table
        self.encounter_group = QGroupBox("What can you find here?")
        enc_layout = QVBoxLayout(self.encounter_group)
        self.encounter_table = QTableWidget()
        self.encounter_table.setColumnCount(3)
        self.encounter_table.setHorizontalHeaderLabels(["Pokemon", "Chance", "Levels"])
        header = self.encounter_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.encounter_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.encounter_table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )
        self.encounter_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        self.encounter_table.setMinimumHeight(150)
        enc_layout.addWidget(self.encounter_table)
        left_layout.addWidget(self.encounter_group)

        # Target selector
        target_group = QGroupBox("Which shiny do you want?")
        target_layout = QVBoxLayout(target_group)
        self.target_combo = QComboBox()
        target_layout.addWidget(self.target_combo)
        left_layout.addWidget(target_group)

        # Encounter counter / tracker
        counter_group = QGroupBox("Encounter Counter")
        counter_layout = QVBoxLayout(counter_group)
        counter_desc = QLabel(
            '<span style="color: #aaa; font-size: 11px;">'
            "Click the button each time you encounter a Pokemon,<br>"
            "or type in your count. We'll track your luck!</span>"
        )
        counter_desc.setWordWrap(True)
        counter_layout.addWidget(counter_desc)

        self.encounters_spin = QSpinBox()
        self.encounters_spin.setRange(0, 200_000)
        self.encounters_spin.setSingleStep(1)
        self.encounters_spin.setValue(0)
        self.encounters_spin.setStyleSheet("font-size: 18px; min-height: 32px;")
        counter_layout.addWidget(self.encounters_spin)

        # Big clickable button row
        button_row = QHBoxLayout()
        self.encounter_button = QPushButton("+1 Encounter (Space)")
        self.encounter_button.setStyleSheet(
            "QPushButton { background-color: #2d5a27; font-weight: bold;"
            " font-size: 14px; min-height: 36px; }"
            "QPushButton:hover { background-color: #3a7a32; }"
            "QPushButton:pressed { background-color: #FFD700; color: #000; }"
        )
        self.encounter_button.clicked.connect(self._on_encounter_click)
        self.encounter_button.setShortcut("Space")

        self.reset_counter_button = QPushButton("Reset")
        self.reset_counter_button.setStyleSheet(
            "QPushButton { background-color: #5a2727; font-size: 11px;"
            " min-height: 36px; max-width: 60px; }"
            "QPushButton:hover { background-color: #7a3232; }"
        )
        self.reset_counter_button.clicked.connect(
            lambda: self.encounters_spin.setValue(0)
        )

        button_row.addWidget(self.encounter_button)
        button_row.addWidget(self.reset_counter_button)
        counter_layout.addLayout(button_row)

        self.percentile_label = QLabel("")
        self.percentile_label.setWordWrap(True)
        self.percentile_label.setStyleSheet("font-size: 14px; padding: 8px;")
        counter_layout.addWidget(self.percentile_label)

        # Save / Load / Clear buttons
        save_row = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.setStyleSheet(
            "QPushButton { background-color: #2d4a7a; font-size: 12px;"
            " min-height: 30px; }"
            "QPushButton:hover { background-color: #3a5a8a; }"
        )
        self.save_button.setToolTip("Save your count so you can close the app and come back later")
        self.save_button.clicked.connect(self._save_progress)

        self.save_as_button = QPushButton("Save As...")
        self.save_as_button.setStyleSheet(
            "QPushButton { background-color: #2d4a7a; font-size: 12px;"
            " min-height: 30px; }"
            "QPushButton:hover { background-color: #3a5a8a; }"
        )
        self.save_as_button.setToolTip("Pick where to save your progress file")
        self.save_as_button.clicked.connect(self._save_progress_as)

        self.load_button = QPushButton("Load")
        self.load_button.setStyleSheet(
            "QPushButton { background-color: #4a4a2d; font-size: 12px;"
            " min-height: 30px; }"
            "QPushButton:hover { background-color: #5a5a3a; }"
        )
        self.load_button.setToolTip("Load your saved hunt from a previous session")
        self.load_button.clicked.connect(self._load_progress)

        self.clear_progress_button = QPushButton("Clear")
        self.clear_progress_button.setStyleSheet(
            "QPushButton { background-color: #5a2727; font-size: 12px;"
            " min-height: 30px; }"
            "QPushButton:hover { background-color: #7a3232; }"
        )
        self.clear_progress_button.setToolTip("Delete your saved progress and start fresh")
        self.clear_progress_button.clicked.connect(self._clear_progress)

        save_row.addWidget(self.save_button)
        save_row.addWidget(self.save_as_button)
        save_row.addWidget(self.load_button)
        save_row.addWidget(self.clear_progress_button)
        counter_layout.addLayout(save_row)

        self.save_status_label = QLabel("")
        self.save_status_label.setWordWrap(True)
        self.save_status_label.setStyleSheet("color: #aaa; font-size: 11px;")
        counter_layout.addWidget(self.save_status_label)

        left_layout.addWidget(counter_group)

        # Time estimator
        time_group = QGroupBox("How long will this take?")
        time_layout = QVBoxLayout(time_group)
        time_desc = QLabel(
            '<span style="color: #aaa; font-size: 11px;">'
            "Pick how fast each attempt takes, and we'll estimate<br>"
            "how many hours of hunting you're looking at.</span>"
        )
        time_desc.setWordWrap(True)
        time_layout.addWidget(time_desc)

        self.time_preset_combo = QComboBox()
        for label in TIME_PRESETS:
            self.time_preset_combo.addItem(label)
        time_layout.addWidget(self.time_preset_combo)

        seconds_row = QHBoxLayout()
        self.seconds_spin = QDoubleSpinBox()
        self.seconds_spin.setRange(1, 300)
        self.seconds_spin.setValue(18)
        self.seconds_spin.setDecimals(0)
        self.seconds_spin.setStyleSheet(
            "QDoubleSpinBox { font-size: 14px; min-height: 28px;"
            " min-width: 80px; padding: 2px 6px; }"
        )
        seconds_label = QLabel("seconds per try")
        seconds_label.setStyleSheet("color: #ccc; font-size: 12px;")
        seconds_row.addWidget(self.seconds_spin)
        seconds_row.addWidget(seconds_label)
        seconds_row.addStretch()
        time_layout.addLayout(seconds_row)

        self.time_estimate_label = QLabel("")
        self.time_estimate_label.setWordWrap(True)
        self.time_estimate_label.setStyleSheet("font-size: 13px; padding: 6px;")
        time_layout.addWidget(self.time_estimate_label)

        left_layout.addWidget(time_group)

        # Simulation controls
        sim_group = QGroupBox("Simulate the Hunt")
        sim_layout = QVBoxLayout(sim_group)
        sim_desc = QLabel(
            '<span style="color: #aaa; font-size: 11px;">'
            "This simulates thousands of people all hunting<br>"
            "the same shiny. You'll see how long it took each<br>"
            "of them. Some get lucky, some don't!</span>"
        )
        sim_desc.setWordWrap(True)
        sim_layout.addWidget(sim_desc)
        sim_layout.addWidget(QLabel("How many hunters to simulate:"))
        self.trials_spin = QSpinBox()
        self.trials_spin.setRange(100, 1_000_000)
        self.trials_spin.setSingleStep(1000)
        self.trials_spin.setValue(10_000)
        sim_layout.addWidget(self.trials_spin)

        self.run_button = QPushButton("Run Simulation")
        self.run_button.setStyleSheet(
            "QPushButton { background-color: #2d5a27; font-weight: bold; }"
            "QPushButton:hover { background-color: #3a7a32; }"
        )
        sim_layout.addWidget(self.run_button)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        sim_layout.addWidget(self.progress_bar)
        left_layout.addWidget(sim_group)

        left_layout.addStretch()

        # Wrap left panel in a scroll area so it works at any window size
        scroll = QScrollArea()
        scroll.setWidget(left)
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(380)
        scroll.setMaximumWidth(440)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # --- Right panel: charts ---
        right = QWidget()
        right_layout = QVBoxLayout(right)

        # Analytical chart (top)
        self.analytical_view = QWebEngineView()
        self._load_chart(self.analytical_view, "analytical", empty_chart_html("Pick a route and Pokemon above"))

        # Simulation chart (bottom)
        self.simulation_view = QWebEngineView()
        self._load_chart(self.simulation_view, "simulation", empty_chart_html("Hit 'Run Simulation' to see what happens!"))

        # Use a splitter so user can resize the two chart areas
        chart_splitter = QSplitter(Qt.Orientation.Vertical)
        chart_splitter.addWidget(self.analytical_view)
        chart_splitter.addWidget(self.simulation_view)
        chart_splitter.setSizes([400, 400])
        right_layout.addWidget(chart_splitter)

        # Add left and right to main
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.addWidget(scroll)
        main_splitter.addWidget(right)
        main_splitter.setSizes([400, 800])
        main_layout.addWidget(main_splitter)

    def _connect_signals(self) -> None:
        """Wire up all the signal/slot connections."""
        self.version_combo.currentIndexChanged.connect(self._on_version_changed)
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        self.route_combo.currentIndexChanged.connect(self._on_route_changed)
        self.encounter_type_combo.currentIndexChanged.connect(self._on_encounter_type_changed)
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        self.encounters_spin.valueChanged.connect(self._update_percentile)
        self.encounters_spin.valueChanged.connect(self._update_time_estimate)
        self.run_button.clicked.connect(self._on_run_simulation)
        self.encounter_table.currentCellChanged.connect(
            self._on_table_row_changed
        )
        self.time_preset_combo.currentIndexChanged.connect(self._on_time_preset_changed)
        self.seconds_spin.valueChanged.connect(self._update_time_estimate)

    # ── Slot handlers ──────────────────────────────────────────

    @staticmethod
    def _base_location_name(route_key: str) -> str:
        """Extract the base location from a route key.

        'Route 4 (Surf)' -> 'Route 4'
        'Route 1'        -> 'Route 1'
        """
        for suffix in (" (Surf)", " (Old Rod)", " (Good Rod)", " (Super Rod)"):
            if route_key.endswith(suffix):
                return route_key[: -len(suffix)]
        return route_key

    @staticmethod
    def _encounter_type_label(route_key: str) -> str:
        """Get the encounter type label from a route key.

        'Route 4 (Surf)' -> 'Surf'
        'Route 1'        -> 'Grass' (or 'Cave' depending on data)
        """
        for suffix, label in [
            (" (Surf)", "Surf"),
            (" (Old Rod)", "Old Rod"),
            (" (Good Rod)", "Good Rod"),
            (" (Super Rod)", "Super Rod"),
        ]:
            if route_key.endswith(suffix):
                return label
        return "Walking"

    @staticmethod
    def _route_sort_key(name: str):
        """Sort routes so numbered routes come first in game order,
        then other locations alphabetically after."""
        import re
        m = re.match(r"Route (\d+)", name)
        if m:
            return (0, int(m.group(1)), name)
        return (1, 0, name)

    def _repopulate_routes(self) -> None:
        """Refill the route dropdown for the current version."""
        routes = ENCOUNTER_TABLES[self.current_version]
        base_names = []
        seen = set()
        for key in sorted(routes.keys()):
            base = self._base_location_name(key)
            if base not in seen:
                seen.add(base)
                base_names.append(base)
        base_names.sort(key=self._route_sort_key)

        was_blocked = self.route_combo.signalsBlocked()
        self.route_combo.blockSignals(True)
        self.route_combo.clear()
        for name in base_names:
            self.route_combo.addItem(name)
        self.route_combo.blockSignals(was_blocked)

    def _on_version_changed(self, index: int) -> None:
        """Update routes when the game version changes.

        Preserves the current route, target, and encounter count
        if the same route exists in the new version.
        """
        self._updating = True
        self.current_version = (
            GameVersion.FIRE_RED if index == 0 else GameVersion.LEAF_GREEN
        )

        # Remember what was selected
        prev_route = self.route_combo.currentText()
        prev_target = self.target_combo.currentText()

        self._repopulate_routes()

        self.route_combo.blockSignals(True)
        # Restore previous route if it exists in the new version
        restored = self.route_combo.findText(prev_route)
        if restored >= 0:
            self.route_combo.setCurrentIndex(restored)
        else:
            self.route_combo.setCurrentIndex(0)
        self.route_combo.blockSignals(False)

        self._on_route_changed(self.route_combo.currentIndex())

        # Restore previous target if it exists on this route
        target_idx = self.target_combo.findText(prev_target)
        if target_idx >= 0:
            self.target_combo.blockSignals(True)
            self.target_combo.setCurrentIndex(target_idx)
            self.target_combo.blockSignals(False)

        self._updating = False
        # Now do one single chart update
        self._on_target_changed(self.target_combo.currentIndex())

    def _on_method_changed(self, index: int) -> None:
        """Toggle between random encounter and soft reset UI."""
        self._updating = True
        if index == 0:  # Random Encounter
            self.current_method = HuntMethod.RANDOM_ENCOUNTER
            self.route_group.setVisible(True)
            self.encounter_group.setVisible(True)
            self._on_route_changed(self.route_combo.currentIndex())
        else:  # Soft Reset
            self.current_method = HuntMethod.SOFT_RESET
            self.route_group.setVisible(False)
            self.encounter_group.setVisible(False)
            self._populate_soft_reset_targets()
        self._updating = False
        self._on_target_changed(self.target_combo.currentIndex())

    @staticmethod
    def _merge_display_slots(slots):
        """Merge encounter slots by species for cleaner display.

        The raw data has separate slots per level (e.g. Meowth Lv17,
        Meowth Lv18, Meowth Lv19). For the table, we combine them
        into one row with the total rate and full level range.
        """
        merged = {}
        order = []
        for slot in slots:
            name = slot.pokemon_name
            if name in merged:
                entry = merged[name]
                entry["rate"] += slot.rate
                entry["level_min"] = min(entry["level_min"], slot.level_min)
                entry["level_max"] = max(entry["level_max"], slot.level_max)
            else:
                merged[name] = {
                    "name": name,
                    "rate": slot.rate,
                    "level_min": slot.level_min,
                    "level_max": slot.level_max,
                }
                order.append(name)
        return [merged[n] for n in order]

    def _on_route_changed(self, index: int) -> None:
        """Update encounter type dropdown for the selected location."""
        if index < 0:
            return

        base_name = self.route_combo.currentText()
        routes = ENCOUNTER_TABLES[self.current_version]

        # Find all encounter types available at this location
        # e.g. "Route 4" might have Walking, Surf, Old Rod, Good Rod, Super Rod
        available = []
        if base_name in routes:
            available.append(("Walking", base_name))
        for suffix, label in [
            (" (Surf)", "Surf"),
            (" (Old Rod)", "Old Rod"),
            (" (Good Rod)", "Good Rod"),
            (" (Super Rod)", "Super Rod"),
        ]:
            key = base_name + suffix
            if key in routes:
                available.append((label, key))

        was_blocked = self.encounter_type_combo.signalsBlocked()
        self.encounter_type_combo.blockSignals(True)
        self.encounter_type_combo.clear()
        for label, _key in available:
            self.encounter_type_combo.addItem(label)
        self.encounter_type_combo.blockSignals(was_blocked)

        # Show the dropdown only if there's more than one option
        self.encounter_type_combo.setVisible(len(available) > 1)

        # Store the mapping so we can look up the route key later
        self._encounter_type_keys = [key for _, key in available]

        # Load the first type
        if available:
            self._load_encounter_table(self._encounter_type_keys[0])

    def _on_encounter_type_changed(self, index: int) -> None:
        """Update the encounter table when switching between Walking/Surf/Rod."""
        if index < 0 or index >= len(self._encounter_type_keys):
            return
        self._updating = True
        self._load_encounter_table(self._encounter_type_keys[index])
        self._updating = False
        self._on_target_changed(self.target_combo.currentIndex())

    def _load_encounter_table(self, route_key: str) -> None:
        """Load the encounter table and target list for a specific route key.

        Does NOT trigger chart updates — the caller is responsible for that.
        """
        routes = ENCOUNTER_TABLES[self.current_version]
        if route_key not in routes:
            return

        route = routes[route_key]

        # Store the active route key so target lookup works
        self._active_route_key = route_key

        # Merge slots by species for display (combine duplicate species)
        display = self._merge_display_slots(route.encounter_slots)

        # Update encounter table
        self.encounter_table.setRowCount(len(display))
        for i, entry in enumerate(display):
            self.encounter_table.setItem(i, 0, QTableWidgetItem(entry["name"]))
            self.encounter_table.setItem(i, 1, QTableWidgetItem(f"{entry['rate'] * 100:.0f}%"))
            lvl = (f"{entry['level_min']}" if entry["level_min"] == entry["level_max"]
                   else f"{entry['level_min']}-{entry['level_max']}")
            self.encounter_table.setItem(i, 2, QTableWidgetItem(lvl))

        # Update target combo (unique names only)
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("Any Shiny")
        for entry in display:
            self.target_combo.addItem(entry["name"])
        self.target_combo.blockSignals(False)
        self.target_combo.setCurrentIndex(0)

        # Only update charts if not in the middle of a batch update
        if not self._updating:
            self._on_target_changed(0)

    def _on_table_row_changed(self, row: int, col: int, prev_row: int, prev_col: int) -> None:
        """When user clicks a row in the encounter table, select that target."""
        if row >= 0 and row < self.encounter_table.rowCount():
            name_item = self.encounter_table.item(row, 0)
            if name_item:
                # Find in target combo and select it (+1 because of "Any Shiny")
                idx = self.target_combo.findText(name_item.text())
                if idx >= 0:
                    self.target_combo.setCurrentIndex(idx)

    def _on_target_changed(self, index: int) -> None:
        """Update charts when the target Pokemon changes."""
        if index < 0 or self._updating:
            return

        if self.current_method == HuntMethod.SOFT_RESET:
            # Combo text is "Bulbasaur (Pallet Town)" — extract just the name
            full_text = self.target_combo.currentText()
            paren = full_text.find(" (")
            self.current_target = full_text[:paren] if paren > 0 else full_text
            self.current_encounter_rate = 1.0
        elif index == 0:  # "Any Shiny"
            self.current_target = "Any Pokemon"
            self.current_encounter_rate = 1.0
        else:
            self.current_target = self.target_combo.currentText()
            # Sum encounter rate across all slots for this species
            # (a species can appear in multiple slots at different levels)
            route_key = getattr(self, "_active_route_key", self.route_combo.currentText())
            routes = ENCOUNTER_TABLES[self.current_version]
            if route_key in routes:
                total_rate = sum(
                    slot.rate for slot in routes[route_key].encounter_slots
                    if slot.pokemon_name == self.current_target
                )
                self.current_encounter_rate = total_rate

        self._update_analytical_chart()
        self._update_percentile(self.encounters_spin.value())
        self._update_time_estimate()
        self._update_status()

    def _populate_soft_reset_targets(self) -> None:
        """Fill target combo with soft-resettable Pokemon."""
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        for name, info in sorted(SOFT_RESET_POKEMON.items()):
            self.target_combo.addItem(f"{name} ({info['location']})")
        self.target_combo.blockSignals(False)

        if self.target_combo.count() > 0:
            self.current_target = list(SOFT_RESET_POKEMON.keys())[0]
            self.current_encounter_rate = 1.0
            self.target_combo.setCurrentIndex(0)
            self._on_target_changed(0)

    def _load_chart(self, view: QWebEngineView, name: str, html: str) -> None:
        """Write chart HTML to a temp file and load it in the view.

        QWebEngineView.setHtml() has a 2MB size limit. Plotly charts
        with embedded JS are ~5MB, so we write to a file instead.
        """
        import os
        file_path = os.path.join(self._chart_dir, f"{name}.html")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html)
        view.load(QUrl.fromLocalFile(os.path.abspath(file_path)))

    def _update_analytical_chart(self) -> None:
        """Redraw the analytical probability chart."""
        p = self.game.effective_probability(self.current_encounter_rate)
        if p <= 0:
            return

        effective_odds = round(1 / p)
        max_enc = min(effective_odds * 5, 200_000)

        html = analytical_chart_html(
            effective_probability=p,
            game_name=self.current_version.value,
            target_name=self.current_target,
            max_encounters=max_enc,
        )
        self._load_chart(self.analytical_view, "analytical", html)

    def _update_percentile(self, encounters: int) -> None:
        """Update the 'Am I Unlucky?' display."""
        p = self.game.percentile_rank(
            encounters,
            encounter_rate=self.current_encounter_rate,
        )

        # Color based on percentile
        if p < 50:
            color = "#4ECDC4"  # teal — lucky or normal
            mood = "Totally normal! Most people haven't found it yet either."
        elif p < 80:
            color = "#FFD700"  # gold — getting up there
            mood = "A bit above average, but nothing unusual. Hang in there!"
        elif p < 95:
            color = "#FF8C42"  # orange — unlucky
            mood = "OK yeah, you're getting unlucky. But it WILL happen!"
        else:
            color = "#FF6B6B"  # red — very unlucky
            mood = "Wow, you're in the top 5% unluckiest hunters. RNG owes you one!"

        self.percentile_label.setText(
            f'<span style="color: {color}; font-size: 16px;">'
            f'{p:.1f}th percentile</span>'
            f'<br><span style="color: #aaa;">{mood}</span>'
        )

    def _open_pokemon_search(self) -> None:
        """Open the Pokemon search dialog."""
        dialog = PokemonSearchDialog(self)
        dialog.exec()

    def _on_encounter_click(self) -> None:
        """Increment the encounter counter by 1."""
        self.encounters_spin.setValue(self.encounters_spin.value() + 1)
        # Schedule auto-save (resets timer if already ticking)
        self._auto_save_timer.start()

    def _auto_save(self) -> None:
        """Silently save progress in the background."""
        data = self._get_save_data()
        self._write_save_file(SAVE_FILE, data)

    # ── Time estimator ────────────────────────────────────────

    def _on_time_preset_changed(self, index: int) -> None:
        """Update seconds spinner when a preset is selected."""
        label = self.time_preset_combo.currentText()
        seconds = TIME_PRESETS.get(label)
        if seconds is not None:
            self.seconds_spin.setValue(seconds)
            self.seconds_spin.setEnabled(False)
        else:
            # Custom: let them type whatever they want
            self.seconds_spin.setEnabled(True)
        self._update_time_estimate()

    def _update_time_estimate(self, _value=None) -> None:
        """Show how long the hunt is expected to take.

        The geometric distribution is memoryless: no matter how many
        tries you've already done, the expected number of REMAINING
        tries is always 1/p. So we always show the full expected time
        from scratch, plus context about how far along you are.
        """
        p = self.game.effective_probability(self.current_encounter_rate)
        if p <= 0:
            self.time_estimate_label.setText("")
            return

        seconds_per_try = self.seconds_spin.value()
        encounters_so_far = self.encounters_spin.value()

        import math

        # Expected encounters = 1/p (mean of geometric distribution)
        expected_encounters = 1 / p
        # 50% chance = median of geometric distribution
        median_encounters = math.ceil(math.log(0.5) / math.log(1 - p))

        # Convert to hours (from zero — these don't change with progress)
        expected_hours = (expected_encounters * seconds_per_try) / 3600
        median_hours = (median_encounters * seconds_per_try) / 3600

        def _format_time(hours: float) -> str:
            if hours < 1:
                return f"{hours * 60:.0f} minutes"
            elif hours < 24:
                return f"{hours:.1f} hours"
            else:
                days = hours / 24
                return f"{days:.1f} days ({hours:.0f} hours)"

        if encounters_so_far == 0:
            text = (
                f'<span style="color: #FFD700;">On average: {_format_time(expected_hours)}</span>'
                f'<br><span style="color: #4ECDC4;">50% chance within: {_format_time(median_hours)}</span>'
                f'<br><span style="color: #aaa; font-size: 11px;">'
                f"That's about {expected_encounters:,.0f} tries at "
                f"{seconds_per_try:.0f}s each</span>"
            )
        else:
            time_spent_hours = (encounters_so_far * seconds_per_try) / 3600
            text = (
                f'<span style="color: #FFD700;">On average it takes: {_format_time(expected_hours)}</span>'
                f'<br><span style="color: #4ECDC4;">50% chance within: {_format_time(median_hours)}</span>'
                f'<br><span style="color: #aaa; font-size: 11px;">'
                f"You've spent ~{_format_time(time_spent_hours)} so far "
                f"({encounters_so_far:,} tries)</span>"
                f'<br><span style="color: #aaa; font-size: 10px;">'
                f"Each try is independent, so the odds don't change "
                f"based on past attempts</span>"
            )

        self.time_estimate_label.setText(text)

    # ── Save / Load ───────────────────────────────────────────

    def _get_save_data(self) -> dict:
        """Collect current hunt state into a dictionary."""
        return {
            "version": self.version_combo.currentText(),
            "method": self.method_combo.currentIndex(),
            "route": self.route_combo.currentText(),
            "encounter_type_index": self.encounter_type_combo.currentIndex(),
            "target": self.target_combo.currentText(),
            "encounters": self.encounters_spin.value(),
            "seconds_per_try": self.seconds_spin.value(),
            "time_preset_index": self.time_preset_combo.currentIndex(),
        }

    def _write_save_file(self, path: Path, data: dict) -> bool:
        """Write save data to a file. Returns True on success."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            return True
        except OSError as err:
            self.save_status_label.setText(
                f'<span style="color: #FF6B6B;">Could not save: {err}</span>'
            )
            return False

    def _save_progress(self) -> None:
        """Save the current hunt to the default location."""
        data = self._get_save_data()
        if self._write_save_file(SAVE_FILE, data):
            self.save_status_label.setText(
                f'<span style="color: #4ECDC4;">Saved! ({data["encounters"]:,} encounters)</span>'
                f'<br><span style="color: #888; font-size: 10px;">{SAVE_FILE}</span>'
            )
            self.statusBar().showMessage(f"Progress saved to {SAVE_FILE}")

    def _save_progress_as(self) -> None:
        """Let the user pick where to save the file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Hunt Progress",
            str(Path.home() / "shiny_hunt_progress.json"),
            "JSON Files (*.json);;All Files (*)",
        )
        if not file_path:
            return  # User cancelled

        data = self._get_save_data()
        path = Path(file_path)
        if self._write_save_file(path, data):
            self.save_status_label.setText(
                f'<span style="color: #4ECDC4;">Saved! ({data["encounters"]:,} encounters)</span>'
                f'<br><span style="color: #888; font-size: 10px;">{path}</span>'
            )
            self.statusBar().showMessage(f"Progress saved to {path}")

    def _load_progress(self) -> None:
        """Load a saved hunt. Try default location first, or let user pick."""
        if SAVE_FILE.exists():
            self._load_from_file(SAVE_FILE)
        else:
            # No default file, let user browse for one
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Load Hunt Progress",
                str(Path.home()),
                "JSON Files (*.json);;All Files (*)",
            )
            if file_path:
                self._load_from_file(Path(file_path))
            else:
                self.save_status_label.setText(
                    '<span style="color: #FF8C42;">No saved hunt found.</span>'
                )

    def _load_from_file(self, path: Path) -> None:
        """Load hunt data from a specific file."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._apply_saved_data(data)
            self.save_status_label.setText(
                f'<span style="color: #4ECDC4;">Loaded! ({data.get("encounters", 0):,} encounters)</span>'
                f'<br><span style="color: #888; font-size: 10px;">From: {path}</span>'
            )
            self.statusBar().showMessage("Loaded saved hunt progress!")
        except (OSError, json.JSONDecodeError, KeyError) as err:
            self.save_status_label.setText(
                f'<span style="color: #FF6B6B;">Could not load: {err}</span>'
            )

    def _clear_progress(self) -> None:
        """Delete saved progress and reset the counter."""
        reply = QMessageBox.question(
            self,
            "Clear Progress",
            "This will delete your saved hunt and reset the counter to 0.\n\n"
            "Are you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        # Delete the save file if it exists
        try:
            if SAVE_FILE.exists():
                SAVE_FILE.unlink()
        except OSError:
            pass

        # Reset the counter
        self.encounters_spin.setValue(0)
        self.save_status_label.setText(
            '<span style="color: #4ECDC4;">Progress cleared. Fresh start!</span>'
        )
        self.statusBar().showMessage("Progress cleared.")

    def _auto_load_progress(self) -> None:
        """Automatically load saved progress on startup if available."""
        if not SAVE_FILE.exists():
            return
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._apply_saved_data(data)
            self.save_status_label.setText(
                f'<span style="color: #4ECDC4;">Welcome back! Loaded {data.get("encounters", 0):,} encounters.</span>'
            )
        except (OSError, json.JSONDecodeError, KeyError):
            pass  # Silently ignore bad save files on startup

    def _apply_saved_data(self, data: dict) -> None:
        """Restore the UI state from saved data.

        Blocks all signals during restore so we don't trigger
        cascading chart reloads for every dropdown change.
        """
        self._updating = True

        # Block signals on all combos to prevent cascades
        combos = [
            self.version_combo, self.method_combo, self.route_combo,
            self.encounter_type_combo, self.target_combo,
        ]
        for combo in combos:
            combo.blockSignals(True)

        # Version
        version_text = data.get("version", "Fire Red")
        version_idx = self.version_combo.findText(version_text)
        if version_idx >= 0:
            self.version_combo.setCurrentIndex(version_idx)
            # Manually update version state and repopulate routes
            self.current_version = (
                GameVersion.FIRE_RED if version_idx == 0 else GameVersion.LEAF_GREEN
            )
            self._repopulate_routes()

        # Method
        method_idx = data.get("method", 0)
        if 0 <= method_idx < self.method_combo.count():
            self.method_combo.setCurrentIndex(method_idx)
            if method_idx == 0:
                self.current_method = HuntMethod.RANDOM_ENCOUNTER
            else:
                self.current_method = HuntMethod.SOFT_RESET

        # Route
        route_text = data.get("route", "")
        route_idx = self.route_combo.findText(route_text)
        if route_idx >= 0:
            self.route_combo.setCurrentIndex(route_idx)
            # Manually populate encounter types for this route
            self._on_route_changed(route_idx)

        # Encounter type (Walking, Surf, Old Rod, etc.)
        etype_idx = data.get("encounter_type_index", 0)
        if 0 <= etype_idx < self.encounter_type_combo.count():
            self.encounter_type_combo.setCurrentIndex(etype_idx)
            if etype_idx < len(self._encounter_type_keys):
                self._load_encounter_table(self._encounter_type_keys[etype_idx])

        # Target
        target_text = data.get("target", "")
        target_idx = self.target_combo.findText(target_text)
        if target_idx >= 0:
            self.target_combo.setCurrentIndex(target_idx)

        # Unblock all signals
        for combo in combos:
            combo.blockSignals(False)

        # Set encounter count BEFORE unblocking so the chart update
        # uses the correct value on the first draw
        self.encounters_spin.blockSignals(True)
        self.encounters_spin.setValue(data.get("encounters", 0))
        self.encounters_spin.blockSignals(False)

        self._updating = False

        # One single chart update at the end
        self._on_target_changed(self.target_combo.currentIndex())

        # Time preset and seconds
        preset_idx = data.get("time_preset_index", 0)
        if 0 <= preset_idx < self.time_preset_combo.count():
            self.time_preset_combo.setCurrentIndex(preset_idx)
        seconds = data.get("seconds_per_try", 18)
        self.seconds_spin.setValue(seconds)

    def _update_status(self) -> None:
        """Update the status bar with current hunt info."""
        p = self.game.effective_probability(self.current_encounter_rate)
        effective_odds = round(1 / p) if p > 0 else 0
        self.statusBar().showMessage(
            f"Hunting {self.current_target} on {self.current_version.value} | "
            f"Effective odds: 1/{effective_odds:,}"
        )

    # ── Simulation ─────────────────────────────────────────────

    def _on_run_simulation(self) -> None:
        """Start or stop a Monte Carlo simulation."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.run_button.setText("Run Simulation")
            self.progress_bar.setVisible(False)
            return

        p = self.game.effective_probability(self.current_encounter_rate)
        if p <= 0:
            return

        num_trials = self.trials_spin.value()

        # Compute batch size for ~100 updates
        if num_trials <= 10_000:
            batch_size = 100
        elif num_trials <= 100_000:
            batch_size = 1_000
        else:
            batch_size = 10_000

        self.run_button.setText("Stop")
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)

        self.worker = SimulationWorker(p, num_trials, batch_size)
        self.worker.progress.connect(self._on_sim_progress)
        self.worker.finished.connect(self._on_sim_finished)
        self.worker.start()

    def _on_sim_progress(
        self, completed: int, total: int, attempts: list[int]
    ) -> None:
        """Update progress bar and histogram during simulation."""
        self.progress_bar.setValue(int(completed / total * 100))

    def _on_sim_finished(self, attempts: list[int]) -> None:
        """Show final simulation results."""
        self.run_button.setText("Run Simulation")
        self.progress_bar.setVisible(False)

        p = self.game.effective_probability(self.current_encounter_rate)
        mean = ShinyHuntSimulator.theoretical_mean(p)
        median = ShinyHuntSimulator.theoretical_median(p)

        html = simulation_histogram_html(
            attempts=attempts,
            effective_probability=p,
            target_name=self.current_target,
            analytical_mean=mean,
            analytical_median=median,
        )
        self._load_chart(self.simulation_view, "simulation", html)
