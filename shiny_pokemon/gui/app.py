"""Application entry point for the Shiny Pokemon GUI.

Run with: uv run python -m shiny_pokemon.gui.app
Or after install: shiny-gui
"""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor
from PySide6.QtCore import Qt
from shiny_pokemon.gui.main_window import MainWindow


def apply_dark_theme(app: QApplication) -> None:
    """Apply a dark color scheme with gold accents."""
    palette = QPalette()

    # Dark backgrounds
    palette.setColor(QPalette.ColorRole.Window, QColor("#2b2b2b"))
    palette.setColor(QPalette.ColorRole.WindowText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Base, QColor("#1e1e1e"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#3c3c3c"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#3c3c3c"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.Button, QColor("#3c3c3c"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor("#ffffff"))
    palette.setColor(QPalette.ColorRole.BrightText, QColor("#FFD700"))
    palette.setColor(QPalette.ColorRole.Link, QColor("#FFD700"))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#FFD700"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))

    app.setPalette(palette)

    # Stylesheet for finer control
    app.setStyleSheet("""
        QGroupBox {
            border: 1px solid #555;
            border-radius: 4px;
            margin-top: 8px;
            padding-top: 16px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
            color: #FFD700;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 6px 16px;
            min-height: 24px;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
            border-color: #FFD700;
        }
        QPushButton:pressed {
            background-color: #FFD700;
            color: #000;
        }
        QComboBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 8px;
            min-height: 24px;
        }
        QComboBox QAbstractItemView {
            background-color: #3c3c3c;
            color: #ffffff;
            selection-background-color: #FFD700;
            selection-color: #000000;
            border: 1px solid #555;
        }
        QSpinBox, QDoubleSpinBox {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 8px;
            color: #ffffff;
        }
        QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555;
            border-radius: 4px;
            padding: 4px 8px;
            color: #ffffff;
        }
        QTableWidget {
            gridline-color: #555;
            background-color: #1e1e1e;
        }
        QHeaderView::section {
            background-color: #3c3c3c;
            color: #FFD700;
            padding: 4px;
            border: 1px solid #555;
        }
        QProgressBar {
            border: 1px solid #555;
            border-radius: 4px;
            text-align: center;
            background-color: #1e1e1e;
        }
        QProgressBar::chunk {
            background-color: #FFD700;
            border-radius: 3px;
        }
        QStatusBar {
            color: #aaa;
        }
        QMessageBox {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QMessageBox QLabel {
            color: #ffffff;
        }
    """)


def main() -> None:
    """Launch the Shiny Pokemon probability tool."""
    app = QApplication(sys.argv)
    app.setApplicationName("Shiny Pokemon Calculator")

    apply_dark_theme(app)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
