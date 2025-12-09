"""
Tests for configuration management.
"""

import json
from pathlib import Path

import pytest

from thub.config import load_config, save_config


def test_load_config_creates_default_structure_when_missing(tmp_path):
    """
    Loading config from non-existent file returns default structure.
    """
    config_path = tmp_path / "config.json"
    config = load_config(config_path)

    assert config == {"users": {}, "proxies": {}}


def test_load_config_reads_existing_file(tmp_path):
    """
    Loading config from existing file returns its contents.
    """
    config_path = tmp_path / "config.json"
    expected = {
        "users": {"alice": ["hash", "salt"]},
        "proxies": {"api": {"base_url": "https://example.com"}},
    }

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(expected, f)

    config = load_config(config_path)
    assert config == expected


def test_load_config_adds_missing_keys(tmp_path):
    """
    Loading config adds missing users and proxies keys.
    """
    config_path = tmp_path / "config.json"

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump({"other": "data"}, f)

    config = load_config(config_path)

    assert "users" in config
    assert "proxies" in config
    assert config["users"] == {}
    assert config["proxies"] == {}
    assert config["other"] == "data"


def test_save_config_writes_json_file(tmp_path):
    """
    Saving config writes properly formatted JSON to file.
    """
    config_path = tmp_path / "config.json"
    config = {"users": {"bob": ["hash", "salt"]}, "proxies": {}}

    save_config(config, config_path)

    assert config_path.exists()

    with open(config_path, "r", encoding="utf-8") as f:
        saved = json.load(f)

    assert saved == config


def test_save_config_creates_pretty_formatted_json(tmp_path):
    """
    Saved config is indented for readability.
    """
    config_path = tmp_path / "config.json"
    config = {"users": {"alice": ["hash", "salt"]}}

    save_config(config, config_path)

    content = config_path.read_text(encoding="utf-8")

    # Check that it's indented (contains newlines and spaces).
    assert "\n" in content
    assert "  " in content
