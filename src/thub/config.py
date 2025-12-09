"""
Configuration management for Tufts Hub.
"""

import json
import os
from pathlib import Path
from typing import Any


def load_config(path: Path = Path("config.json")) -> dict[str, Any]:
    """
    Load configuration from JSON file.

    Returns an empty config structure if the file doesn't exist.
    """
    if not path.exists():
        return {
            "users": {},
            "proxies": {},
            "jwt": {
                "secret": None,
                "expiry_hours": 24,
            },
        }

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Ensure required keys exist.
    if "users" not in config:
        config["users"] = {}
    if "proxies" not in config:
        config["proxies"] = {}
    if "jwt" not in config:
        config["jwt"] = {"secret": None, "expiry_hours": 24}

    return config


def save_config(config: dict[str, Any], path: Path = Path("config.json")):
    """
    Save configuration to JSON file with pretty formatting.
    """
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
