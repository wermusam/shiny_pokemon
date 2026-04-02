"""Build a standalone .exe for the Shiny Pokemon Calculator.

Run with: uv run python build_exe.py

This creates a single .exe file in the dist/ folder that your
roommate can download and double-click. No Python needed.
"""

import PyInstaller.__main__
import os

# Get the path to this script's directory
here = os.path.dirname(os.path.abspath(__file__))

PyInstaller.__main__.run([
    os.path.join(here, "shiny_pokemon", "gui", "app.py"),
    "--name", "ShinyCalculator",
    "--onefile",
    "--windowed",
    "--noconfirm",
    # Hidden imports that PyInstaller might miss
    "--hidden-import", "PySide6.QtWebEngineWidgets",
    "--hidden-import", "plotly",
    "--hidden-import", "numpy",
])
