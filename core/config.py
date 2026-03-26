"""
core/config.py — Settings management
Reads/writes config from AppData\Local\WorkPulse\config.env
"""

import os
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
    "START_ON_BOOT": "true",
    "DARK_MODE": "true",
    "WINDOW_TRACKING": "false",
    "CLIPBOARD_HINTS": "true",
    "CLOCKIFY_API_KEY": "",
    "CLOCKIFY_WORKSPACE_ID": "",
}


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
    projects_file = Path(__file__).parent.parent / "data" / "projects.json"
    with open(projects_file, "r") as f:
        return json.load(f)
