"""
core/config.py — Settings management
Reads/writes config from AppData\Local\WorkPulse\config.env
"""

import os
import sys
import json
from pathlib import Path
from dotenv import dotenv_values, set_key

APP_NAME = "WorkPulse"
APP_DATA_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME
CONFIG_FILE = APP_DATA_DIR / "config.env"
DB_FILE = APP_DATA_DIR / "workpulse.db"

DEFAULTS = {
    "USER_NAME": "Farhan Jamaludin",
    "PING_INTERVAL": "15",
    "IDLE_THRESHOLD": "10",
    "OVERDUE_WARNING": "45",
    "WORK_START": "09:00",
    "END_OF_DAY": "18:00",
    "HOTKEY": "alt+l",
    "SOUND_THEME": "soft_chime",
    "VOLUME": "60",
    "PLAY_ON": "all",
    "START_ON_BOOT": "true",
    "DARK_MODE": "true",
    "WINDOW_TRACKING": "false",
    "CLIPBOARD_HINTS": "true",
    "CLOCKIFY_API_KEY": "",
    "CLOCKIFY_WORKSPACE_ID": "682c279d9eb4d30a38976325",
    "LAST_CLOCKIFY_SYNC": "",
    "STATUS_BAR_DURATION": "10",
}


def get_base_dir() -> Path:
    """Get the base directory — works both for .py and .exe (PyInstaller)."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller .exe
        return Path(sys._MEIPASS)
    else:
        # Running as normal Python script
        return Path(__file__).parent.parent


def ensure_app_dir():
    APP_DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_app_dir()
    if not CONFIG_FILE.exists():
        save_config(DEFAULTS)
        return dict(DEFAULTS)
    values = dotenv_values(CONFIG_FILE)
    config = dict(DEFAULTS)
    config.update(values)
    return config


def save_config(config: dict):
    ensure_app_dir()
    for key, value in config.items():
        set_key(str(CONFIG_FILE), key, str(value))


def get(key: str, fallback=None):
    config = load_config()
    return config.get(key, fallback or DEFAULTS.get(key))


def set(key: str, value):
    ensure_app_dir()
    set_key(str(CONFIG_FILE), key, str(value))


def get_int(key: str) -> int:
    return int(get(key))


def get_bool(key: str) -> bool:
    return get(key, "false").lower() == "true"


def load_projects() -> list:
    projects_file = get_base_dir() / "data" / "projects.json"
    try:
        with open(projects_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Fallback — return empty list so app doesn't crash
        return []
