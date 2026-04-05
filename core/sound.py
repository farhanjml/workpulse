"""
core/sound.py — Sound playback for WorkPulse events.
Uses winsound (stdlib). Volume is system-controlled; VOLUME setting is
stored but not applied (winsound limitation).
"""

import threading
import winsound
import os
import sys

from core.config import get, get_base_dir

# Map config SOUND_THEME values to filenames
THEME_FILES = {
    "soft_chime": "soft_chime.wav",
    "typewriter":  "typewriter.wav",
    "retro":       "retro_beep.wav",
}

# Events and which PLAY_ON setting values trigger them
EVENT_PLAY_ON = {
    "ping":     {"all", "ping_only", "ping_overdue"},
    "overdue":  {"all", "ping_overdue"},
    "idle":     {"all"},
    "eod":      {"all"},
}


def _sound_path(filename: str) -> str:
    return str(get_base_dir() / "sounds" / filename)


def should_play(event: str) -> bool:
    """Return True if the current PLAY_ON setting allows this event."""
    play_on = get("PLAY_ON", "all")
    if play_on == "none":
        return False
    allowed = EVENT_PLAY_ON.get(event, set())
    return play_on in allowed


def play(event: str):
    """Play the configured sound for an event in a background thread."""
    if not should_play(event):
        return
    theme = get("SOUND_THEME", "soft_chime")
    filename = THEME_FILES.get(theme)
    if not filename:
        return
    path = _sound_path(filename)
    if not os.path.exists(path):
        print(f"[Sound] File not found: {path}")
        return

    def _run():
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
        except Exception as e:
            print(f"[Sound] Playback error: {e}")

    threading.Thread(target=_run, daemon=True).start()
