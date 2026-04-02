"""Main application window.

This is the central hub that creates all widgets and connects them.
The layout uses a left panel for controls and a right panel for charts.
"""

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
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QProgressBar,
    QStatusBar,
    QHeaderView,
    QScrollArea,
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Qt, QThread, Signal, QUrl

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

        # Temp directory for chart HTML files (QWebEngineView.setHtml
        # has a 2MB limit, so we write to files and load via URL)
        import tempfile
        self._chart_dir = tempfile.mkdtemp(prefix="shiny_charts_")

        # Build UI
        self._build_ui()
        self._connect_signals()

        # Initialize with first route
        self._on_version_changed(0)

        self.statusBar().showMessage("Pick a route and a Pokemon to get started!")

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
        self.encounter_button = QPushButton("+1 Encounter")
        self.encounter_button.setStyleSheet(
            "QPushButton { background-color: #2d5a27; font-weight: bold;"
            " font-size: 14px; min-height: 36px; }"
            "QPushButton:hover { background-color: #3a7a32; }"
            "QPushButton:pressed { background-color: #FFD700; color: #000; }"
        )
        self.encounter_button.clicked.connect(self._on_encounter_click)

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
        left_layout.addWidget(counter_group)

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
        self.target_combo.currentIndexChanged.connect(self._on_target_changed)
        self.encounters_spin.valueChanged.connect(self._update_percentile)
        self.run_button.clicked.connect(self._on_run_simulation)
        self.encounter_table.currentCellChanged.connect(
            self._on_table_row_changed
        )

    # ── Slot handlers ──────────────────────────────────────────

    def _on_version_changed(self, index: int) -> None:
        """Update routes when the game version changes.

        Preserves the current route, target, and encounter count
        if the same route exists in the new version.
        """
        self.current_version = (
            GameVersion.FIRE_RED if index == 0 else GameVersion.LEAF_GREEN
        )

        # Remember what was selected
        prev_route = self.route_combo.currentText()
        prev_target = self.target_combo.currentText()

        routes = ENCOUNTER_TABLES[self.current_version]
        self.route_combo.blockSignals(True)
        self.route_combo.clear()
        for name in sorted(routes.keys()):
            self.route_combo.addItem(name)

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
            self.target_combo.setCurrentIndex(target_idx)

    def _on_method_changed(self, index: int) -> None:
        """Toggle between random encounter and soft reset UI."""
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

    def _on_route_changed(self, index: int) -> None:
        """Update encounter table and target list for the selected route."""
        if index < 0:
            return

        route_name = self.route_combo.currentText()
        routes = ENCOUNTER_TABLES[self.current_version]
        if route_name not in routes:
            return

        route = routes[route_name]

        # Update encounter table
        slots = route.encounter_slots
        self.encounter_table.setRowCount(len(slots))
        for i, slot in enumerate(slots):
            self.encounter_table.setItem(i, 0, QTableWidgetItem(slot.pokemon_name))
            self.encounter_table.setItem(i, 1, QTableWidgetItem(f"{slot.rate * 100:.0f}%"))
            self.encounter_table.setItem(
                i, 2, QTableWidgetItem(f"{slot.level_min}-{slot.level_max}")
            )

        # Update target combo
        self.target_combo.blockSignals(True)
        self.target_combo.clear()
        self.target_combo.addItem("Any Shiny")
        for slot in slots:
            self.target_combo.addItem(slot.pokemon_name)
        self.target_combo.blockSignals(False)
        self.target_combo.setCurrentIndex(0)
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
        if index < 0:
            return

        if self.current_method == HuntMethod.SOFT_RESET:
            self.current_target = self.target_combo.currentText()
            self.current_encounter_rate = 1.0
        elif index == 0:  # "Any Shiny"
            self.current_target = "Any Pokemon"
            self.current_encounter_rate = 1.0
        else:
            self.current_target = self.target_combo.currentText()
            # Look up the encounter rate from the route data
            route_name = self.route_combo.currentText()
            routes = ENCOUNTER_TABLES[self.current_version]
            if route_name in routes:
                for slot in routes[route_name].encounter_slots:
                    if slot.pokemon_name == self.current_target:
                        self.current_encounter_rate = slot.rate
                        break

        self._update_analytical_chart()
        self._update_percentile(self.encounters_spin.value())
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

    def _on_encounter_click(self) -> None:
        """Increment the encounter counter by 1."""
        self.encounters_spin.setValue(self.encounters_spin.value() + 1)

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
