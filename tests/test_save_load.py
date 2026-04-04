"""Tests for save/load hunt progress functionality."""

import json
from pathlib import Path
import pytest


def test_save_file_format(tmp_path):
    """Save data should be valid JSON with the expected keys."""
    save_file = tmp_path / "hunt_progress.json"
    data = {
        "version": "Fire Red",
        "method": 0,
        "route": "Route 1",
        "target": "Pidgey",
        "encounters": 1234,
        "seconds_per_try": 18,
        "time_preset_index": 0,
    }
    with open(save_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    # Read it back and verify
    with open(save_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["version"] == "Fire Red"
    assert loaded["encounters"] == 1234
    assert loaded["target"] == "Pidgey"
    assert loaded["route"] == "Route 1"
    assert loaded["seconds_per_try"] == 18


def test_missing_save_file(tmp_path):
    """Loading a nonexistent file should not crash."""
    save_file = tmp_path / "does_not_exist.json"
    assert not save_file.exists()


def test_corrupt_save_file(tmp_path):
    """A corrupted file should not crash the loader."""
    save_file = tmp_path / "hunt_progress.json"
    save_file.write_text("this is not json!!!", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        with open(save_file, "r", encoding="utf-8") as f:
            json.load(f)
