# WorkPulse Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign WorkPulse with Dotdash brand identity, fix first-ping-of-day flow, implement sound, sync projects from Clockify API, and add an interrupt log.

**Architecture:** Introduce `ui/theme.py` for shared design tokens, `core/sound.py` for audio playback, extend `core/clockify.py` with project fetch/sync, add `log_interrupt` to `core/database.py`, and create a new `ui/interrupt_log.py` popup. All UI files adopt the new theme. `main.py` wires two new hotkeys and the startup sync.

**Tech Stack:** PyQt6, Python `winsound` (stdlib), `requests` (already in requirements), `wave`+`struct` (stdlib, for generating sound files)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `ui/theme.py` | **Create** | Design tokens, font loader, base stylesheet |
| `core/sound.py` | **Create** | Sound playback, event→file routing |
| `ui/interrupt_log.py` | **Create** | Interrupt log popup (new feature) |
| `assets/fonts/` | **Create** | Sora font TTF files |
| `sounds/` | **Populate** | WAV sound files |
| `core/config.py` | Modify | Add `PLAY_ON`, `LAST_CLOCKIFY_SYNC` defaults |
| `core/clockify.py` | Modify | Add `fetch_projects`, `fetch_tasks`, `sync_projects_to_cache` |
| `core/database.py` | Modify | Add `log_interrupt` |
| `main.py` | Modify | Add `Alt+Shift+L` hotkey, startup sync, wire interrupt popup |
| `ui/ping_popup.py` | Modify | First-ping-of-day detection + Dotdash redesign |
| `ui/quick_log.py` | Modify | Dotdash redesign |
| `ui/status_bar.py` | Modify | Green/red/gray state dots, ⚡ hover button |
| `ui/summary.py` | Modify | Dotdash redesign |
| `ui/settings.py` | Modify | Play On dropdown, Sync button, last-synced label |
| `ui/tray.py` | Modify | Wire interrupt popup signal |
| `tests/conftest.py` | **Create** | Pytest fixtures (temp DB, mocked config) |
| `tests/test_sound.py` | **Create** | Sound routing logic tests |
| `tests/test_clockify_sync.py` | **Create** | Project sync tests (mocked HTTP) |
| `tests/test_database.py` | **Create** | `log_interrupt` tests |

---

## Task 1: Design tokens and Sora font

**Files:**
- Create: `ui/theme.py`
- Create: `assets/fonts/` (download Sora TTF)

- [ ] **Step 1: Download Sora font files**

Run this once to fetch the font:

```bash
python -c "
import urllib.request, os
os.makedirs('assets/fonts', exist_ok=True)
base = 'https://github.com/google/fonts/raw/main/ofl/sora/static/'
for f in ['Sora-Regular.ttf', 'Sora-SemiBold.ttf', 'Sora-Bold.ttf']:
    url = base + f
    print(f'Downloading {f}...')
    urllib.request.urlretrieve(url, f'assets/fonts/{f}')
    print(f'  saved to assets/fonts/{f}')
print('Done')
"
```

Expected output: three lines saying `saved to assets/fonts/...`

- [ ] **Step 2: Create `ui/theme.py`**

```python
"""
ui/theme.py — Dotdash design tokens and font loader.
Import DARK, LIGHT, or call get_colors(mode) in each UI file.
"""

from PyQt6.QtGui import QFontDatabase, QFont
from core.config import get_bool
import os, sys


def _base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.join(os.path.dirname(__file__), "..")


def load_fonts():
    """Load Sora from assets/fonts/. Call once at app start."""
    fonts_dir = os.path.join(_base_dir(), "assets", "fonts")
    loaded = []
    for name in ["Sora-Regular.ttf", "Sora-SemiBold.ttf", "Sora-Bold.ttf"]:
        path = os.path.join(fonts_dir, name)
        if os.path.exists(path):
            fid = QFontDatabase.addApplicationFont(path)
            if fid >= 0:
                loaded.append(name)
    return loaded


def font_family() -> str:
    """Return 'Sora' if loaded, else fall back to Segoe UI."""
    families = QFontDatabase.families()
    return "Sora" if "Sora" in families else "Segoe UI"


# ── Color palettes ────────────────────────────────────────────────────────────

DARK = {
    "bg":           "#030404",
    "s0":           "#080909",
    "s1":           "#0e0f0f",
    "s2":           "#141515",
    "s3":           "#1a1b1b",
    "border":       "rgba(255,255,255,0.055)",
    "border_h":     "rgba(255,255,255,0.10)",
    "gold":         "#e9bb51",
    "gold_dim":     "rgba(233,187,81,0.6)",
    "gold_border":  "rgba(233,187,81,0.22)",
    "gold_bg":      "rgba(233,187,81,0.07)",
    "t1":           "#f2ede4",
    "t2":           "#8a8478",
    "t3":           "#3d3b37",
    "green":        "#4ade80",
    "green_bg":     "rgba(74,222,128,0.07)",
    "green_border": "rgba(74,222,128,0.22)",
    "red":          "#fca5a5",
    "red_bg":       "rgba(252,165,165,0.07)",
    "red_border":   "rgba(252,165,165,0.22)",
    "state_active":  "#4ade80",
    "state_overdue": "#ef4444",
    "state_idle":    "#3d3b37",
}

LIGHT = {
    "bg":           "#f5f0e8",
    "s0":           "#fffdf8",
    "s1":           "#f9f4ec",
    "s2":           "#f0eade",
    "s3":           "#e8e0d0",
    "border":       "rgba(0,0,0,0.08)",
    "border_h":     "rgba(0,0,0,0.14)",
    "gold":         "#e9bb51",
    "gold_dim":     "#c9962a",
    "gold_border":  "rgba(233,187,81,0.4)",
    "gold_bg":      "rgba(233,187,81,0.12)",
    "t1":           "#1a1710",
    "t2":           "#6b6355",
    "t3":           "#b0a898",
    "green":        "#16a34a",
    "green_bg":     "rgba(22,163,74,0.07)",
    "green_border": "rgba(22,163,74,0.25)",
    "red":          "#dc2626",
    "red_bg":       "rgba(220,38,38,0.06)",
    "red_border":   "rgba(220,38,38,0.25)",
    "state_active":  "#16a34a",
    "state_overdue": "#dc2626",
    "state_idle":    "#b0a898",
}


def get_colors() -> dict:
    """Return color dict for current mode (reads DARK_MODE from config)."""
    return LIGHT if not get_bool("DARK_MODE") else DARK


def base_stylesheet(c: dict) -> str:
    """Return the base QSS shared across all windows."""
    ff = font_family()
    return f"""
QWidget {{
    background: {c['bg']};
    color: {c['t1']};
    font-family: '{ff}', 'Segoe UI', sans-serif;
}}
QLineEdit, QComboBox, QTimeEdit {{
    background: {c['s2']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 7px 11px;
    color: {c['t1']};
    font-size: 12px;
}}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus {{
    border-color: {c['gold_border']};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {c['s2']};
    color: {c['t1']};
    selection-background-color: {c['gold_bg']};
}}
QPushButton {{
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    padding: 9px 14px;
    border: 1px solid {c['border']};
    background: {c['s2']};
    color: {c['t2']};
    font-family: '{ff}', 'Segoe UI', sans-serif;
}}
QPushButton:hover {{ color: {c['t1']}; border-color: {c['border_h']}; }}
QPushButton#btnPrimary {{
    background: {c['gold']};
    border-color: {c['gold']};
    color: #030404;
}}
QPushButton#btnPrimary:hover {{ background: #f0c66a; }}
QPushButton#btnGhost {{
    background: transparent;
    color: {c['t3']};
}}
QPushButton#btnGhost:hover {{ color: {c['t2']}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {c['s1']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {c['s3']};
    border-radius: 3px;
}}
"""
```

- [ ] **Step 3: Verify font loads**

```bash
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from ui.theme import load_fonts, font_family
loaded = load_fonts()
print('Loaded fonts:', loaded)
print('Active family:', font_family())
"
```

Expected: `Active family: Sora` (or `Segoe UI` if font download failed)

- [ ] **Step 4: Commit**

```bash
git add ui/theme.py assets/fonts/
git commit -m "feat: add Dotdash design tokens and Sora font (ui/theme.py)"
```

---

## Task 2: Config — add PLAY_ON and LAST_CLOCKIFY_SYNC

**Files:**
- Modify: `core/config.py`

- [ ] **Step 1: Add new defaults to `DEFAULTS` dict**

In `core/config.py`, find the `DEFAULTS` dict and add two new keys after `"CLOCKIFY_WORKSPACE_ID"`:

```python
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
    "PLAY_ON": "all",                          # new
    "START_ON_BOOT": "true",
    "DARK_MODE": "true",
    "WINDOW_TRACKING": "false",
    "CLIPBOARD_HINTS": "true",
    "CLOCKIFY_API_KEY": "",
    "CLOCKIFY_WORKSPACE_ID": "682c279d9eb4d30a38976325",
    "LAST_CLOCKIFY_SYNC": "",                  # new — ISO timestamp or empty
    "STATUS_BAR_DURATION": "10",
}
```

- [ ] **Step 2: Verify config loads with new defaults**

```bash
python -c "
from core.config import get
print('PLAY_ON:', get('PLAY_ON'))
print('LAST_CLOCKIFY_SYNC:', repr(get('LAST_CLOCKIFY_SYNC')))
"
```

Expected:
```
PLAY_ON: all
LAST_CLOCKIFY_SYNC: ''
```

- [ ] **Step 3: Commit**

```bash
git add core/config.py
git commit -m "feat: add PLAY_ON and LAST_CLOCKIFY_SYNC config defaults"
```

---

## Task 3: Sound module

**Files:**
- Create: `core/sound.py`
- Populate: `sounds/` directory (generated WAV files)

- [ ] **Step 1: Generate WAV sound files**

Run once to create the three sound files:

```bash
python -c "
import wave, struct, math, os

def write_wav(path, notes, sr=44100):
    frames = []
    for freq, dur, vol in notes:
        n = int(sr * dur)
        for i in range(n):
            t = i / sr
            fade = min(1.0, min(t, dur - t) / 0.01)  # 10ms fade in/out
            v = int(32767 * vol * fade * math.sin(2 * math.pi * freq * t))
            frames.append(struct.pack('<h', max(-32767, min(32767, v))))
    with wave.open(path, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sr)
        f.writeframes(b''.join(frames))

os.makedirs('sounds', exist_ok=True)

# soft_chime: two gentle tones
write_wav('sounds/soft_chime.wav', [
    (880, 0.12, 0.35),
    (0,   0.04, 0),
    (1100, 0.18, 0.25),
])

# typewriter: short sharp click
write_wav('sounds/typewriter.wav', [
    (1200, 0.03, 0.6),
    (800,  0.05, 0.3),
])

# retro_beep: classic beep
write_wav('sounds/retro_beep.wav', [
    (440, 0.08, 0.5),
    (0,   0.03, 0),
    (440, 0.08, 0.5),
])

print('Created:', os.listdir('sounds'))
"
```

Expected: `Created: ['retro_beep.wav', 'soft_chime.wav', 'typewriter.wav']`

- [ ] **Step 2: Create `core/sound.py`**

```python
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
```

- [ ] **Step 3: Write tests**

Create `tests/test_sound.py`:

```python
"""Tests for core/sound.py — should_play logic."""
import pytest
from unittest.mock import patch


def test_should_play_all_allows_ping():
    with patch("core.sound.get", return_value="all"):
        from core.sound import should_play
        assert should_play("ping") is True


def test_should_play_all_allows_overdue():
    with patch("core.sound.get", return_value="all"):
        from core.sound import should_play
        assert should_play("overdue") is True


def test_should_play_ping_only_blocks_overdue():
    with patch("core.sound.get", return_value="ping_only"):
        from core.sound import should_play
        assert should_play("overdue") is False


def test_should_play_ping_only_allows_ping():
    with patch("core.sound.get", return_value="ping_only"):
        from core.sound import should_play
        assert should_play("ping") is True


def test_should_play_none_blocks_all():
    with patch("core.sound.get", return_value="none"):
        from core.sound import should_play
        for event in ["ping", "overdue", "idle", "eod"]:
            assert should_play(event) is False


def test_should_play_ping_overdue_blocks_idle():
    with patch("core.sound.get", return_value="ping_overdue"):
        from core.sound import should_play
        assert should_play("idle") is False
        assert should_play("ping") is True
        assert should_play("overdue") is True
```

- [ ] **Step 4: Create `tests/conftest.py`**

```python
"""Shared pytest fixtures."""
import pytest
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
```

- [ ] **Step 5: Run the tests**

```bash
pip install pytest -q
pytest tests/test_sound.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 6: Commit**

```bash
git add core/sound.py sounds/ tests/
git commit -m "feat: add sound module and WAV files (core/sound.py)"
```

---

## Task 4: Clockify project sync

**Files:**
- Modify: `core/clockify.py`
- Create: `tests/test_clockify_sync.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_clockify_sync.py`:

```python
"""Tests for Clockify project sync functions."""
import pytest
import json
import os
from unittest.mock import patch, MagicMock


MOCK_PROJECTS = [
    {"id": "proj_abc", "name": "Maybank MY - RDRS", "archived": False},
    {"id": "proj_xyz", "name": "Internal - Office", "archived": False},
    {"id": "proj_old", "name": "Old Project", "archived": True},
]

MOCK_TASKS_ABC = [
    {"id": "t1", "name": "Meeting", "status": "ACTIVE"},
    {"id": "t2", "name": "UAT Support", "status": "ACTIVE"},
]

MOCK_TASKS_XYZ = [
    {"id": "t3", "name": "Document", "status": "ACTIVE"},
]


def _mock_get(url, **kwargs):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    if "/projects" in url and "/tasks" not in url:
        resp.json.return_value = MOCK_PROJECTS
    elif "proj_abc/tasks" in url:
        resp.json.return_value = MOCK_TASKS_ABC
    elif "proj_xyz/tasks" in url:
        resp.json.return_value = MOCK_TASKS_XYZ
    else:
        resp.json.return_value = []
    return resp


def test_fetch_projects_returns_active_only():
    with patch("core.clockify.requests.get", side_effect=_mock_get), \
         patch("core.clockify._get_api_key", return_value="testkey"), \
         patch("core.clockify.config.get", return_value="ws_123"):
        from core.clockify import fetch_projects
        projects = fetch_projects("ws_123")
    assert len(projects) == 2
    assert all(not p["archived"] for p in projects)


def test_fetch_tasks_returns_names():
    with patch("core.clockify.requests.get", side_effect=_mock_get), \
         patch("core.clockify._get_api_key", return_value="testkey"):
        from core.clockify import fetch_tasks
        tasks = fetch_tasks("ws_123", "proj_abc")
    assert tasks == ["Meeting", "UAT Support"]


def test_sync_slugifies_new_project_name():
    with patch("core.clockify.requests.get", side_effect=_mock_get), \
         patch("core.clockify._get_api_key", return_value="testkey"), \
         patch("core.clockify.config.get", return_value="ws_123"), \
         patch("core.clockify._load_cached_projects", return_value=[]), \
         patch("core.clockify._save_projects_cache") as mock_save:
        from core.clockify import sync_projects_to_cache
        result = sync_projects_to_cache()
    assert result is True
    saved = mock_save.call_args[0][0]
    ids = [p["id"] for p in saved]
    assert "maybank_my_rdrs" in ids
    assert "internal_office" in ids


def test_sync_preserves_existing_id():
    existing = [{"id": "my_custom_id", "clockify_project_id": "proj_abc",
                 "name": "Old Name", "tasks": []}]
    with patch("core.clockify.requests.get", side_effect=_mock_get), \
         patch("core.clockify._get_api_key", return_value="testkey"), \
         patch("core.clockify.config.get", return_value="ws_123"), \
         patch("core.clockify._load_cached_projects", return_value=existing), \
         patch("core.clockify._save_projects_cache") as mock_save:
        from core.clockify import sync_projects_to_cache
        sync_projects_to_cache()
    saved = mock_save.call_args[0][0]
    abc_entry = next(p for p in saved if p["clockify_project_id"] == "proj_abc")
    assert abc_entry["id"] == "my_custom_id"
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_clockify_sync.py -v
```

Expected: ImportError or AttributeError — `fetch_projects` not defined yet.

- [ ] **Step 3: Add sync functions to `core/clockify.py`**

Add these imports at the top of `core/clockify.py`:

```python
import re
import json
from pathlib import Path
from core import config
```

Then add these functions at the bottom of `core/clockify.py`:

```python
def fetch_projects(workspace_id: str) -> list:
    """Fetch all active (non-archived) projects from Clockify."""
    try:
        resp = requests.get(
            f"{BASE_URL}/workspaces/{workspace_id}/projects",
            headers=_headers(),
            params={"archived": "false", "page-size": 500},
            timeout=10,
        )
        resp.raise_for_status()
        return [p for p in resp.json() if not p.get("archived", False)]
    except Exception as e:
        print(f"[Clockify] fetch_projects error: {e}")
        return []


def fetch_tasks(workspace_id: str, project_id: str) -> list[str]:
    """Return task names for a project (active tasks only)."""
    try:
        resp = requests.get(
            f"{BASE_URL}/workspaces/{workspace_id}/projects/{project_id}/tasks",
            headers=_headers(),
            params={"status": "ACTIVE", "page-size": 200},
            timeout=10,
        )
        resp.raise_for_status()
        return [t["name"] for t in resp.json() if t.get("status") == "ACTIVE"]
    except Exception as e:
        print(f"[Clockify] fetch_tasks error: {e}")
        return []


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _load_cached_projects() -> list:
    from core.config import get_base_dir
    path = get_base_dir() / "data" / "projects.json"
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def _save_projects_cache(projects: list):
    from core.config import get_base_dir
    path = get_base_dir() / "data" / "projects.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(projects, f, indent=2)


def sync_projects_to_cache() -> bool:
    """
    Fetch projects+tasks from Clockify and write to data/projects.json.
    Preserves existing local 'id' slugs where clockify_project_id matches.
    Returns True on success, False on failure.
    """
    if not is_configured():
        return False

    workspace_id = config.get("CLOCKIFY_WORKSPACE_ID", WORKSPACE_ID)
    raw_projects = fetch_projects(workspace_id)
    if not raw_projects:
        return False

    existing = _load_cached_projects()
    id_by_clockify = {p["clockify_project_id"]: p["id"]
                      for p in existing if p.get("clockify_project_id")}

    result = []
    for rp in raw_projects:
        cid = rp["id"]
        local_id = id_by_clockify.get(cid) or _slugify(rp["name"])
        tasks = fetch_tasks(workspace_id, cid)
        result.append({
            "id": local_id,
            "name": rp["name"],
            "clockify_project_id": cid,
            "tasks": tasks,
        })

    _save_projects_cache(result)

    # Update last-sync timestamp
    from datetime import datetime
    config.set("LAST_CLOCKIFY_SYNC", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print(f"[Clockify] Synced {len(result)} projects")
    return True
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_clockify_sync.py -v
```

Expected: all 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/clockify.py tests/test_clockify_sync.py
git commit -m "feat: add Clockify project sync (fetch_projects, sync_projects_to_cache)"
```

---

## Task 5: Database — log_interrupt

**Files:**
- Modify: `core/database.py`
- Create: `tests/test_database.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_database.py`:

```python
"""Tests for database.log_interrupt."""
import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

# Use an in-memory DB path for tests
TEST_DB = ":memory:"


@pytest.fixture
def mem_db(tmp_path, monkeypatch):
    """Patch DB_FILE to a temp file and init schema."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("core.database.DB_FILE", db_path)
    monkeypatch.setattr("core.config.DB_FILE", db_path)
    from core import database
    database.init_db()
    return database


def test_log_interrupt_creates_completed_entry(mem_db):
    with patch("core.database._push_to_clockify"):
        mem_db.log_interrupt(
            project_id="internal_office",
            project_name="Internal - Office",
            task="Special Task — Reply customer email",
            duration_minutes=10,
        )
    entries = mem_db.get_entries_for_date()
    assert len(entries) == 1
    e = entries[0]
    assert e["project_id"] == "internal_office"
    assert e["end_time"] is not None


def test_log_interrupt_does_not_close_active_entry(mem_db):
    """Active task must keep running after an interrupt log."""
    with patch("core.database._push_to_clockify"):
        mem_db.log_entry(
            project_id="maybank_impl",
            project_name="Maybank MY",
            task="Meeting — kickoff",
        )
        mem_db.log_interrupt(
            project_id="internal_office",
            project_name="Internal - Office",
            task="Special Task — quick email",
            duration_minutes=5,
        )
    active = mem_db.get_active_entry()
    assert active is not None
    assert active["project_id"] == "maybank_impl"


def test_log_interrupt_duration_window(mem_db):
    """start_time should be approximately now - duration_minutes."""
    with patch("core.database._push_to_clockify"):
        mem_db.log_interrupt(
            project_id="internal_office",
            project_name="Internal - Office",
            task="Special Task — email",
            duration_minutes=15,
        )
    entries = mem_db.get_entries_for_date()
    e = entries[0]
    start = datetime.strptime(e["start_time"], "%H:%M")
    end = datetime.strptime(e["end_time"], "%H:%M")
    diff = int((end - start).total_seconds() // 60)
    assert diff == 15
```

- [ ] **Step 2: Run tests to confirm fail**

```bash
pytest tests/test_database.py -v
```

Expected: AttributeError — `log_interrupt` not defined.

- [ ] **Step 3: Add `log_interrupt` to `core/database.py`**

Add this function after `log_entry`:

```python
def log_interrupt(project_id: str, project_name: str, task: str, duration_minutes: int) -> int:
    """
    Log a quick side task without affecting the active entry.
    Creates a completed entry spanning (now - duration_minutes) → now.
    The active task timer continues unaffected.
    """
    now = datetime.now()
    end_time = now.strftime("%H:%M")
    start_time = (now - timedelta(minutes=duration_minutes)).strftime("%H:%M")
    today = date.today().isoformat()

    entry_id = add_entry(
        project_id=project_id,
        project_name=project_name,
        task=task,
        start_time=start_time,
        end_time=end_time,
        today=today,
    )

    # Sync to Clockify as a completed entry
    entry = {
        "project_id": project_id,
        "task": task,
        "start_time": start_time,
        "date": today,
        "is_break": False,
    }
    _push_to_clockify(entry, end_time)
    return entry_id
```

Also add `timedelta` to the existing datetime import at the top of `database.py`:

```python
from datetime import datetime, date, timedelta
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/test_database.py -v
```

Expected: all 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add core/database.py tests/test_database.py
git commit -m "feat: add log_interrupt to database (no active task disruption)"
```

---

## Task 6: Ping popup — first-ping-of-day + redesign

**Files:**
- Modify: `ui/ping_popup.py`

- [ ] **Step 1: Replace `ui/ping_popup.py` entirely**

```python
"""
ui/ping_popup.py — 15-minute ping popup.
Shows 'Good morning' variant when no task is active.
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core import database, config
from core.config import load_projects
from ui.theme import get_colors, base_stylesheet


def _time_options(minutes_back: int = 90) -> list:
    now = datetime.now()
    options = []
    for i in range(0, minutes_back + 1, 15):
        t = now - timedelta(minutes=i)
        label = t.strftime("%H:%M") + (" (now)" if i == 0 else "")
        options.append((t.strftime("%H:%M"), label))
    return options


class PingPopup(QWidget):
    logged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects = load_projects()
        self._setup_window()
        self._setup_ui()
        self._auto_dismiss = QTimer()
        self._auto_dismiss.setSingleShot(True)
        self._auto_dismiss.timeout.connect(self._on_auto_dismiss)
        self._countdown_val = 60
        self._countdown_timer = QTimer()
        self._countdown_timer.timeout.connect(self._tick_countdown)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(400)

    def _apply_theme(self):
        c = get_colors()
        self.setStyleSheet(base_stylesheet(c) + f"""
            QFrame#card {{
                background: {c['s0']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
            QWidget#header {{
                background: {c['s1']};
                border-radius: 14px 14px 0 0;
                border-bottom: 1px solid {c['border']};
            }}
            QFrame#activeChip {{
                background: {c['s1']};
                border: 1px solid {c['border']};
                border-radius: 9px;
            }}
            QPushButton#btnStillOn {{
                background: {c['green_bg']};
                border: 1px solid {c['green_border']};
                color: {c['green']};
                text-align: left;
                padding: 10px 13px;
            }}
            QPushButton#btnStillOn:hover {{ background: rgba(74,222,128,0.13); }}
            QPushButton#btnEndTask {{
                background: {c['red_bg']};
                border: 1px solid {c['red_border']};
                color: {c['red']};
                text-align: left;
                padding: 10px 13px;
            }}
            QPushButton#btnEndTask:hover {{ background: rgba(252,165,165,0.13); }}
        """)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("header")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(14, 10, 14, 10)
        self.lbl_dot = QLabel("●")
        self.lbl_dot.setFixedWidth(10)
        self.lbl_header = QLabel("WORKPULSE · PING")
        self.lbl_header.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 3px;")
        self.lbl_streak = QLabel("🔥 0 entries")
        self.lbl_streak.setStyleSheet("font-size: 10px; font-weight: 600;")
        hdr_layout.addWidget(self.lbl_dot)
        hdr_layout.addWidget(self.lbl_header)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self.lbl_streak)
        card_layout.addWidget(header)

        # Body
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(14, 14, 14, 16)
        self.body_layout.setSpacing(9)

        # ── Active-task section (hidden when no active task) ──────────────────
        self.active_section = QWidget()
        act_layout = QVBoxLayout(self.active_section)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.setSpacing(7)

        self.active_chip = QFrame()
        self.active_chip.setObjectName("activeChip")
        chip_row = QHBoxLayout(self.active_chip)
        chip_row.setContentsMargins(12, 10, 12, 10)
        self.lbl_chip_dot = QLabel("●")
        self.lbl_chip_dot.setFixedWidth(10)
        self.lbl_chip_info = QWidget()
        chip_info_layout = QVBoxLayout(self.lbl_chip_info)
        chip_info_layout.setContentsMargins(0, 0, 0, 0)
        chip_info_layout.setSpacing(1)
        self.lbl_task_name = QLabel()
        self.lbl_task_name.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.lbl_task_meta = QLabel()
        self.lbl_task_meta.setStyleSheet("font-size: 10px;")
        chip_info_layout.addWidget(self.lbl_task_name)
        chip_info_layout.addWidget(self.lbl_task_meta)
        self.lbl_elapsed = QLabel()
        self.lbl_elapsed.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        chip_row.addWidget(self.lbl_chip_dot)
        chip_row.addWidget(self.lbl_chip_info, 1)
        chip_row.addWidget(self.lbl_elapsed)
        act_layout.addWidget(self.active_chip)

        self.btn_still_on = QPushButton("✓  Still on it — keep going")
        self.btn_still_on.setObjectName("btnStillOn")
        self.btn_still_on.clicked.connect(self._on_still_on)
        act_layout.addWidget(self.btn_still_on)

        end_row_widget = QWidget()
        end_row = QHBoxLayout(end_row_widget)
        end_row.setContentsMargins(0, 0, 0, 0)
        end_row.setSpacing(8)
        self.btn_end_task = QPushButton("⏹  Done with this task")
        self.btn_end_task.setObjectName("btnEndTask")
        self.btn_end_task.clicked.connect(self._on_end_task)
        lbl_ended = QLabel("ended at")
        lbl_ended.setStyleSheet("font-size: 10px;")
        self.cmb_end_time = QComboBox()
        self.cmb_end_time.setFixedWidth(110)
        end_row.addWidget(self.btn_end_task, 1)
        end_row.addWidget(lbl_ended)
        end_row.addWidget(self.cmb_end_time)
        act_layout.addWidget(end_row_widget)
        self.body_layout.addWidget(self.active_section)

        # ── First-ping hero (shown when no active task) ───────────────────────
        self.first_ping_section = QWidget()
        fp_layout = QVBoxLayout(self.first_ping_section)
        fp_layout.setContentsMargins(0, 4, 0, 4)
        fp_layout.setSpacing(2)
        self.lbl_gm_eyebrow = QLabel()
        self.lbl_gm_eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gm_title = QLabel("What are you starting with?")
        self.lbl_gm_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gm_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.lbl_gm_sub = QLabel("Log your first task to kick off the day")
        self.lbl_gm_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gm_sub.setStyleSheet("font-size: 11px;")
        fp_layout.addWidget(self.lbl_gm_eyebrow)
        fp_layout.addWidget(self.lbl_gm_title)
        fp_layout.addWidget(self.lbl_gm_sub)
        self.body_layout.addWidget(self.first_ping_section)

        # ── New-task form (always shown) ──────────────────────────────────────
        self.divider_lbl = QLabel("OR SWITCHED TO SOMETHING NEW")
        self.divider_lbl.setStyleSheet("font-size: 8.5px; font-weight: 600; letter-spacing: 2px;")
        self.body_layout.addWidget(self.divider_lbl)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("What are you working on...")
        self.body_layout.addWidget(self.txt_desc)

        self.cmb_project = QComboBox()
        self.cmb_task = QComboBox()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        self.body_layout.addWidget(self.cmb_project)
        self.body_layout.addWidget(self.cmb_task)

        switched_row = QHBoxLayout()
        self.lbl_switched = QLabel("switched at")
        self.lbl_switched.setStyleSheet("font-size: 10px;")
        self.cmb_started = QComboBox()
        self.cmb_started.setFixedWidth(110)
        switched_row.addWidget(self.lbl_switched)
        switched_row.addStretch()
        switched_row.addWidget(self.cmb_started)
        self.body_layout.addLayout(switched_row)

        btn_row = QHBoxLayout()
        self.btn_log = QPushButton("Log New Task")
        self.btn_log.setObjectName("btnPrimary")
        self.btn_log.clicked.connect(self._on_log)
        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setObjectName("btnGhost")
        self.btn_skip.setFixedWidth(70)
        self.btn_skip.clicked.connect(self.hide)
        btn_row.addWidget(self.btn_log)
        btn_row.addWidget(self.btn_skip)
        self.body_layout.addLayout(btn_row)

        footer_row = QHBoxLayout()
        hint = QLabel("Tab · Enter · Esc")
        hint.setStyleSheet("font-size: 9.5px;")
        self.lbl_countdown = QLabel("auto-closing in 60s")
        self.lbl_countdown.setStyleSheet("font-size: 9.5px;")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer_row.addWidget(hint)
        footer_row.addStretch()
        footer_row.addWidget(self.lbl_countdown)
        self.body_layout.addLayout(footer_row)

        card_layout.addWidget(body)
        outer.addWidget(self.card)
        self._on_project_changed(0)

    def _populate_times(self):
        options = _time_options()
        self.cmb_end_time.clear()
        self.cmb_started.clear()
        for val, label in options:
            self.cmb_end_time.addItem(label, val)
            self.cmb_started.addItem(label, val)

    def _on_project_changed(self, index):
        if not hasattr(self, "cmb_task") or index < 0 or index >= len(self.projects):
            return
        self.cmb_task.clear()
        for task in self.projects[index].get("tasks", []):
            self.cmb_task.addItem(task)

    def _refresh_active(self):
        c = get_colors()
        active = database.get_active_entry()

        if active:
            # Normal mode — show active task section, hide first-ping hero
            self.active_section.setVisible(True)
            self.first_ping_section.setVisible(False)
            self.divider_lbl.setVisible(True)
            self.btn_log.setText("Log New Task")
            self.lbl_switched.setText("switched at")
            self.btn_skip.setVisible(True)

            task = active.get("task", "")
            task_display = task.split(" \u2014 ", 1)[-1] if " \u2014 " in task else task
            project_name = active.get("project_name", "")
            self.lbl_task_name.setText(task_display)
            self.lbl_task_meta.setText(project_name)

            # Elapsed
            try:
                now = datetime.now()
                start = datetime.strptime(active["start_time"], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                mins = max(0, int((now - start).total_seconds() // 60))
                elapsed = f"{mins}m" if mins < 60 else f"{mins//60}h {mins%60}m"
            except Exception:
                elapsed = ""
            self.lbl_elapsed.setText(elapsed)
            self.lbl_elapsed.setStyleSheet(f"font-size: 10px; font-family: 'JetBrains Mono', monospace; color: {c['gold_dim']};")
            self.lbl_chip_dot.setStyleSheet(f"color: {c['state_active']}; font-size: 8px;")
            self.lbl_task_meta.setStyleSheet(f"font-size: 10px; color: {c['t3']};")

        else:
            # First-ping mode — no active task
            self.active_section.setVisible(False)
            self.first_ping_section.setVisible(True)
            self.divider_lbl.setVisible(False)
            self.btn_log.setText("Start Tracking")
            self.lbl_switched.setText("started at")
            self.btn_skip.setVisible(True)

            name = config.get("USER_NAME", "Farhan").split()[0]
            self.lbl_gm_eyebrow.setText(f"Good morning, {name}")
            self.lbl_gm_eyebrow.setStyleSheet(f"font-size: 10px; font-weight: 600; letter-spacing: 2px; color: {c['gold_dim']};")
            self.lbl_streak.setText("✦ Day start")

        self.lbl_dot.setStyleSheet(f"color: {c['state_active']}; font-size: 8px; background: transparent;")

    def _refresh_streak(self):
        count = database.count_entries_today()
        self.lbl_streak.setText(f"🔥 {count} entries")

    def _on_still_on(self):
        database.extend_active_entry()
        self.logged.emit()
        self.hide()

    def _on_end_task(self):
        end_time = self.cmb_end_time.currentData()
        database.end_current_entry(end_time)
        self.logged.emit()
        self.hide()

    def _on_log(self):
        desc = self.txt_desc.text().strip()
        if not desc:
            self.txt_desc.setFocus()
            return
        idx = self.cmb_project.currentIndex()
        if idx < 0 or idx >= len(self.projects):
            return
        project = self.projects[idx]
        task_type = self.cmb_task.currentText()
        task = f"{task_type} \u2014 {desc}" if task_type else desc
        database.log_entry(
            project_id=project["id"],
            project_name=project["name"],
            task=task,
            stopped_at=self.cmb_started.currentData(),
        )
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def _on_auto_dismiss(self):
        self._countdown_timer.stop()
        self.hide()

    def _tick_countdown(self):
        self._countdown_val -= 1
        if self._countdown_val > 0:
            self.lbl_countdown.setText(f"auto-closing in {self._countdown_val}s")
        else:
            self.lbl_countdown.setText("closing...")

    def showEvent(self, event):
        self.projects = load_projects()
        # Rebuild project combo if list changed
        self.cmb_project.clear()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self._on_project_changed(0)
        self._populate_times()
        self._apply_theme()
        self._refresh_active()
        active = database.get_active_entry()
        if active:
            self._refresh_streak()
        self.txt_desc.clear()
        self._countdown_val = 60
        self.lbl_countdown.setText("auto-closing in 60s")
        self._auto_dismiss.stop()
        self._auto_dismiss.start(60_000)
        self._countdown_timer.stop()
        self._countdown_timer.start(1_000)
        super().showEvent(event)
        self._position_top_center()

    def hideEvent(self, event):
        self._auto_dismiss.stop()
        self._countdown_timer.stop()
        super().hideEvent(event)

    def _position_top_center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, 40)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_log()
```

- [ ] **Step 2: Run the app and verify visually**

```bash
python main.py
```

Verify:
- Popup appears with new Dotdash styling
- If no active task: shows "Good morning, [Name]" with "Start Tracking" button
- If active task: shows task chip, "Still on it", "Done with this task"
- Auto-dismiss countdown works

- [ ] **Step 3: Commit**

```bash
git add ui/ping_popup.py
git commit -m "feat: ping popup first-ping-of-day flow and Dotdash redesign"
```

---

## Task 7: Interrupt log popup

**Files:**
- Create: `ui/interrupt_log.py`

- [ ] **Step 1: Create `ui/interrupt_log.py`**

```python
"""
ui/interrupt_log.py — Quick interrupt log popup.
Logs a short side task without affecting the active task timer.
Triggered via Alt+Shift+L or the status bar ⚡ button.
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal

from core import database
from core.config import load_projects
from ui.theme import get_colors, base_stylesheet

DURATIONS = [5, 10, 15, 30]  # minutes


class InterruptLogPopup(QWidget):
    logged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects = load_projects()
        self._selected_duration = 10
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(380)

    def _apply_theme(self):
        c = get_colors()
        self.setStyleSheet(base_stylesheet(c) + f"""
            QFrame#card {{
                background: {c['s0']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
            QWidget#header {{
                background: {c['s1']};
                border-radius: 14px 14px 0 0;
                border-bottom: 1px solid {c['border']};
            }}
            QFrame#runningChip {{
                background: {c['s1']};
                border: 1px solid {c['border']};
                border-radius: 9px;
            }}
            QPushButton.durPill {{
                background: {c['s2']};
                border: 1px solid {c['border']};
                color: {c['t2']};
                font-size: 11px;
                padding: 6px 0;
                border-radius: 7px;
                min-width: 46px;
            }}
            QPushButton.durPill:hover {{
                border-color: {c['gold_border']};
                color: {c['gold_dim']};
            }}
            QPushButton#durActive {{
                background: {c['gold_bg']};
                border: 1px solid {c['gold_border']};
                color: {c['gold']};
                font-size: 11px;
                font-weight: 600;
                padding: 6px 0;
                border-radius: 7px;
                min-width: 46px;
            }}
        """)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("header")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(14, 10, 14, 10)
        lbl_dot = QLabel("●")
        lbl_dot.setFixedWidth(10)
        lbl_dot.setObjectName("headerDot")
        lbl_title = QLabel("QUICK INTERRUPT")
        lbl_title.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 3px;")
        lbl_hotkey = QLabel("Alt+Shift+L")
        lbl_hotkey.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        hdr_layout.addWidget(lbl_dot)
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()
        hdr_layout.addWidget(lbl_hotkey)
        card_layout.addWidget(header)

        # Body
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 13, 14, 14)
        body_layout.setSpacing(9)

        # Running task chip
        self.running_chip = QFrame()
        self.running_chip.setObjectName("runningChip")
        chip_layout = QHBoxLayout(self.running_chip)
        chip_layout.setContentsMargins(12, 9, 12, 9)
        chip_info = QWidget()
        chip_info_layout = QVBoxLayout(chip_info)
        chip_info_layout.setContentsMargins(0, 0, 0, 0)
        chip_info_layout.setSpacing(1)
        self.lbl_running_task = QLabel("No active task")
        self.lbl_running_task.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.lbl_running_meta = QLabel("")
        self.lbl_running_meta.setStyleSheet("font-size: 10px;")
        chip_info_layout.addWidget(self.lbl_running_task)
        chip_info_layout.addWidget(self.lbl_running_meta)
        self.lbl_still_running = QLabel("● still running")
        self.lbl_still_running.setStyleSheet("font-size: 9px; font-weight: 600; white-space: nowrap;")
        chip_layout.addWidget(chip_info, 1)
        chip_layout.addWidget(self.lbl_still_running)
        body_layout.addWidget(self.running_chip)

        # Description input
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Quick task description...")
        body_layout.addWidget(self.txt_desc)

        # Project + task dropdowns
        combo_row = QHBoxLayout()
        self.cmb_project = QComboBox()
        self.cmb_task = QComboBox()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        combo_row.addWidget(self.cmb_project, 3)
        combo_row.addWidget(self.cmb_task, 2)
        body_layout.addLayout(combo_row)

        # Duration quick-picks
        dur_label = QLabel("HOW LONG?")
        dur_label.setStyleSheet("font-size: 8.5px; font-weight: 700; letter-spacing: 2px;")
        body_layout.addWidget(dur_label)

        dur_row = QHBoxLayout()
        dur_row.setSpacing(6)
        self._dur_buttons = []
        for mins in DURATIONS:
            btn = QPushButton(f"{mins}m")
            btn.setProperty("class", "durPill")
            btn.clicked.connect(lambda checked, m=mins: self._select_duration(m))
            dur_row.addWidget(btn)
            self._dur_buttons.append((mins, btn))
        body_layout.addLayout(dur_row)

        # CTA
        self.btn_log = QPushButton("⚡  Quick Log")
        self.btn_log.setObjectName("btnPrimary")
        self.btn_log.clicked.connect(self._on_log)
        body_layout.addWidget(self.btn_log)

        # Footer
        footer_row = QHBoxLayout()
        hint = QLabel("Enter to log · Esc to cancel")
        hint.setStyleSheet("font-size: 9.5px;")
        lbl_note = QLabel("main task keeps running")
        lbl_note.setStyleSheet("font-size: 9.5px;")
        lbl_note.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer_row.addWidget(hint)
        footer_row.addStretch()
        footer_row.addWidget(lbl_note)
        body_layout.addLayout(footer_row)

        card_layout.addWidget(body)
        outer.addWidget(card)
        self._on_project_changed(0)

    def _on_project_changed(self, index):
        if not hasattr(self, "cmb_task") or index < 0 or index >= len(self.projects):
            return
        self.cmb_task.clear()
        for task in self.projects[index].get("tasks", []):
            self.cmb_task.addItem(task)

    def _select_duration(self, minutes: int):
        self._selected_duration = minutes
        c = get_colors()
        for m, btn in self._dur_buttons:
            if m == minutes:
                btn.setObjectName("durActive")
            else:
                btn.setProperty("class", "durPill")
                btn.setObjectName("")
        self._apply_theme()

    def _refresh_running(self):
        c = get_colors()
        active = database.get_active_entry()
        if active:
            task = active.get("task", "")
            task_display = task.split(" \u2014 ", 1)[-1] if " \u2014 " in task else task
            self.lbl_running_task.setText(task_display)
            self.lbl_running_meta.setText(
                f"{active.get('project_name', '')}  ·  "
                + self._get_elapsed(active["start_time"])
            )
            self.lbl_still_running.setStyleSheet(
                f"font-size: 9px; font-weight: 600; color: {c['state_active']}; white-space: nowrap;"
            )
            self.lbl_running_meta.setStyleSheet(f"font-size: 10px; color: {c['t3']};")
        else:
            self.lbl_running_task.setText("No active task")
            self.lbl_running_meta.setText("")
            self.lbl_still_running.setStyleSheet(f"font-size: 9px; color: {c['t3']};")

    def _get_elapsed(self, start_time: str) -> str:
        try:
            now = datetime.now()
            start = datetime.strptime(start_time, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            mins = max(0, int((now - start).total_seconds() // 60))
            return f"{mins}m" if mins < 60 else f"{mins//60}h {mins%60}m"
        except Exception:
            return ""

    def _on_log(self):
        desc = self.txt_desc.text().strip()
        if not desc:
            self.txt_desc.setFocus()
            return
        idx = self.cmb_project.currentIndex()
        if idx < 0 or idx >= len(self.projects):
            return
        project = self.projects[idx]
        task_type = self.cmb_task.currentText()
        task = f"{task_type} \u2014 {desc}" if task_type else desc
        database.log_interrupt(
            project_id=project["id"],
            project_name=project["name"],
            task=task,
            duration_minutes=self._selected_duration,
        )
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def showEvent(self, event):
        self.projects = load_projects()
        self.cmb_project.clear()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self._on_project_changed(0)
        self._apply_theme()
        self._refresh_running()
        self._select_duration(10)  # default 10m selected
        self.txt_desc.clear()
        self.txt_desc.setFocus()
        super().showEvent(event)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, 40)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_log()
```

- [ ] **Step 2: Smoke test — verify import**

```bash
python -c "from ui.interrupt_log import InterruptLogPopup; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/interrupt_log.py
git commit -m "feat: add interrupt log popup (ui/interrupt_log.py)"
```

---

## Task 8: Status bar — green/red/gray state dots

**Files:**
- Modify: `ui/status_bar.py`

- [ ] **Step 1: Add state management and update `ui/status_bar.py`**

Replace the contents of `ui/status_bar.py` with:

```python
"""
ui/status_bar.py — Floating live task indicator.
States: active (green), overdue (red), idle (gray).
Emits interrupt_requested signal when ⚡ button clicked.
"""

from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen

from core import database, config
from ui.theme import get_colors

HIT_PADDING = 20

STATE_COLORS = {
    "active":  ("#4ade80", "#1a4a2a"),   # on, off (pulse)
    "overdue": ("#ef4444", "#4a1a1a"),
    "idle":    ("#3d3b37", "#3d3b37"),   # no pulse
}


class StatusBar(QWidget):
    interrupt_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_task = None
        self._is_expanded = False
        self._state = "active"   # "active" | "overdue" | "idle"
        self._setup_window()
        self._setup_ui()

        self._collapse_timer = QTimer()
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._do_collapse)

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._silent_refresh)
        self._refresh_timer.start(30_000)

        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_timer.start(60_000)

        self._dot_state = True
        self._dot_timer = QTimer()
        self._dot_timer.timeout.connect(self._pulse_dot)
        self._dot_timer.start(1500)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def _setup_ui(self):
        self._inner = QWidget(self)
        inner_layout = QHBoxLayout(self._inner)
        inner_layout.setContentsMargins(10, 0, 10, 0)
        inner_layout.setSpacing(6)

        self.lbl_dot = QLabel("●")
        self.lbl_dot.setStyleSheet("color: #4ade80; font-size: 8px; background: transparent;")
        inner_layout.addWidget(self.lbl_dot)

        self.lbl_task = QLabel("")
        self.lbl_task.setStyleSheet(
            "color: #f2ede4; font-family: 'Sora', 'Segoe UI', sans-serif; "
            "font-size: 11px; background: transparent;"
        )
        inner_layout.addWidget(self.lbl_task)

        self.lbl_elapsed = QLabel("")
        self.lbl_elapsed.setStyleSheet(
            "color: rgba(233,187,81,0.6); font-family: 'JetBrains Mono', monospace; "
            "font-size: 10px; background: transparent;"
        )
        inner_layout.addWidget(self.lbl_elapsed)

        self.btn_interrupt = QPushButton("⚡")
        self.btn_interrupt.setFixedSize(20, 20)
        self.btn_interrupt.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 12px; color: #e9bb51; }"
            "QPushButton:hover { color: #f0c66a; }"
        )
        self.btn_interrupt.hide()
        self.btn_interrupt.clicked.connect(self.interrupt_requested.emit)
        inner_layout.addWidget(self.btn_interrupt)

    def set_state(self, state: str):
        """Set dot state: 'active', 'overdue', 'idle'."""
        self._state = state
        self._apply_dot_color()

    def _apply_dot_color(self):
        color_on, _ = STATE_COLORS.get(self._state, STATE_COLORS["active"])
        self.lbl_dot.setStyleSheet(f"color: {color_on}; font-size: 8px; background: transparent;")

    def _collapsed_inner_size(self):
        return 24, 24

    def _expanded_inner_size(self):
        self._inner.adjustSize()
        return max(self._inner.sizeHint().width() + 20, 120), 28

    def _do_collapse(self):
        self._is_expanded = False
        self.lbl_task.hide()
        self.lbl_elapsed.hide()
        self.btn_interrupt.hide()
        w, h = self._collapsed_inner_size()
        self._inner.setGeometry(HIT_PADDING, HIT_PADDING, w, h)
        self.setFixedSize(w + HIT_PADDING * 2, h + HIT_PADDING * 2)
        self._reposition()
        self.update()

    def _do_expand(self):
        self._is_expanded = True
        self.lbl_task.show()
        self.lbl_elapsed.show()
        if self._active_task and self._state == "active":
            self.btn_interrupt.show()
        w, h = self._expanded_inner_size()
        self._inner.setGeometry(HIT_PADDING, HIT_PADDING, w, h)
        self.setFixedSize(w + HIT_PADDING * 2, h + HIT_PADDING * 2)
        self._reposition()
        self.update()

    def _reposition(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = 8 - HIT_PADDING
        self.move(x, y)

    def _pulse_dot(self):
        if not self.isVisible():
            return
        if self._state == "idle":
            return  # no pulse for idle
        self._dot_state = not self._dot_state
        color_on, color_off = STATE_COLORS.get(self._state, STATE_COLORS["active"])
        color = color_on if self._dot_state else color_off
        self.lbl_dot.setStyleSheet(f"color: {color}; font-size: 8px; background: transparent;")

    def _get_elapsed(self, start_time: str) -> str:
        try:
            now = datetime.now()
            start = datetime.strptime(start_time, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            mins = max(0, int((now - start).total_seconds() // 60))
            return f"{mins}m" if mins < 60 else f"{mins // 60}h {mins % 60}m"
        except Exception:
            return ""

    def _update_elapsed(self):
        if self._active_task and self._is_expanded:
            self.lbl_elapsed.setText(self._get_elapsed(self._active_task["start_time"]))

    def _load_task(self) -> bool:
        self._active_task = database.get_active_entry()
        if not self._active_task:
            return False
        task = self._active_task.get("task", "")
        if " \u2014 " in task:
            task = task.split(" \u2014 ", 1)[1]
        elif " - " in task:
            task = task.split(" - ", 1)[1]
        self.lbl_task.setText(task)
        self.lbl_elapsed.setText(self._get_elapsed(self._active_task["start_time"]))
        return True

    def _silent_refresh(self):
        if not self._load_task():
            self.hide()

    def refresh(self):
        if not self._load_task():
            self.hide()
            return
        try:
            duration_ms = int(config.get("STATUS_BAR_DURATION", "10")) * 1000
        except Exception:
            duration_ms = 10_000
        self.set_state("active")
        self.show()
        self._do_expand()
        self._collapse_timer.stop()
        self._collapse_timer.start(duration_ms)

    def set_overdue(self):
        self.set_state("overdue")
        if self._active_task or self._load_task():
            self.show()
            self._do_expand()

    def set_idle(self):
        self.set_state("idle")

    def enterEvent(self, event):
        if self._active_task:
            self._collapse_timer.stop()
            self._load_task()
            self._do_expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._collapse_timer.stop()
        self._collapse_timer.start(1500)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inner_rect = self._inner.geometry()
        path = QPainterPath()
        r = inner_rect.height() // 2
        path.addRoundedRect(inner_rect.x(), inner_rect.y(),
                            inner_rect.width(), inner_rect.height(), r, r)

        # Background color varies by state
        if self._state == "overdue":
            bg = QColor(20, 8, 8, 235)
        elif self._state == "idle":
            bg = QColor(14, 14, 14, 180)
        else:
            bg = QColor(8, 9, 9, 235)

        painter.fillPath(path, bg)

        border_color = {
            "active":  QColor(50, 60, 50, 180),
            "overdue": QColor(80, 30, 30, 220),
            "idle":    QColor(40, 40, 40, 150),
        }.get(self._state, QColor(50, 50, 68, 220))

        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)
        painter.end()
```

- [ ] **Step 2: Verify import**

```bash
python -c "from ui.status_bar import StatusBar; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/status_bar.py
git commit -m "feat: status bar green/red/gray states and interrupt button"
```

---

## Task 9: Settings window — Play On, Sync, last-synced

**Files:**
- Modify: `ui/settings.py`

- [ ] **Step 1: Update the `SOUND` section in `_setup_ui` to add Play On dropdown**

Find the SOUND section block in `_setup_ui` (after `self.sld_volume`) and add:

```python
# After sld_volume:
self.cmb_play_on = QComboBox()
self.cmb_play_on.setFixedWidth(160)
for label, val in [("All events", "all"), ("Ping only", "ping_only"),
                   ("Ping + Overdue", "ping_overdue"), ("None", "none")]:
    self.cmb_play_on.addItem(label, val)
play_on_val = self._cfg.get("PLAY_ON", "all")
play_on_vals = ["all", "ping_only", "ping_overdue", "none"]
self.cmb_play_on.setCurrentIndex(play_on_vals.index(play_on_val) if play_on_val in play_on_vals else 0)
body_layout.addWidget(SettingRow("Play on", self.cmb_play_on))
```

- [ ] **Step 2: Update the `CLOCKIFY` section to add Sync button and status**

Replace the existing Clockify section (just the API key row) with:

```python
body_layout.addWidget(self._section_label("CLOCKIFY"))

# API key row
self.txt_api_key = QLineEdit()
self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
self.txt_api_key.setPlaceholderText("Paste API key here...")
self.txt_api_key.setFixedWidth(200)
body_layout.addWidget(SettingRow("API Key", self.txt_api_key))

# Sync row
self.btn_sync_projects = QPushButton("↻ Sync Projects")
self.btn_sync_projects.setObjectName("btnPrimary")
self.btn_sync_projects.setFixedWidth(140)
self.btn_sync_projects.clicked.connect(self._sync_projects)
body_layout.addWidget(SettingRow("Projects", self.btn_sync_projects))

# Last synced label
last_sync = self._cfg.get("LAST_CLOCKIFY_SYNC", "")
sync_text = f"Last synced: {last_sync}" if last_sync else "Not synced yet"
self.lbl_sync_status = QLabel(sync_text)
self.lbl_sync_status.setStyleSheet("color: #3d3b37; font-size: 10px; padding: 0 12px;")
body_layout.addWidget(self.lbl_sync_status)
```

- [ ] **Step 3: Add `_sync_projects` method to `SettingsWindow`**

```python
def _sync_projects(self):
    self.btn_sync_projects.setText("Syncing...")
    self.btn_sync_projects.setEnabled(False)
    import threading
    def _run():
        from core.clockify import sync_projects_to_cache
        ok = sync_projects_to_cache()
        from PyQt6.QtCore import QMetaObject, Qt
        QMetaObject.invokeMethod(self, "_on_sync_done",
                                 Qt.ConnectionType.QueuedConnection,
                                 ok)
    threading.Thread(target=_run, daemon=True).start()

def _on_sync_done(self, ok: bool):
    from core.config import get
    self.btn_sync_projects.setEnabled(True)
    self.btn_sync_projects.setText("↻ Sync Projects")
    if ok:
        last_sync = get("LAST_CLOCKIFY_SYNC", "")
        self.lbl_sync_status.setText(f"Last synced: {last_sync}")
    else:
        self.lbl_sync_status.setText("Sync failed — check API key")
        self.lbl_sync_status.setStyleSheet("color: #fca5a5; font-size: 10px; padding: 0 12px;")
```

> **Note:** `QMetaObject.invokeMethod` requires the method to be decorated with `@pyqtSlot(bool)`. Add `from PyQt6.QtCore import pyqtSlot` to the imports and decorate `_on_sync_done`:
> ```python
> @pyqtSlot(bool)
> def _on_sync_done(self, ok: bool):
>     ...
> ```

- [ ] **Step 4: Update `_save` method to include `PLAY_ON`**

In `_save`, add to the `updates` dict:

```python
"PLAY_ON": self.cmb_play_on.currentData(),
```

- [ ] **Step 5: Verify settings open without error**

```bash
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from ui.settings import SettingsWindow
w = SettingsWindow()
w.show()
print('Settings window OK')
"
```

Expected: `Settings window OK`

- [ ] **Step 6: Commit**

```bash
git add ui/settings.py
git commit -m "feat: settings — Play On dropdown, Clockify Sync button, last-synced label"
```

---

## Task 10: Wire everything in main.py

**Files:**
- Modify: `main.py`

- [ ] **Step 1: Update imports and add new signal + hotkey constant**

At the top of `main.py`, add:

```python
from ui.interrupt_log import InterruptLogPopup
from ui.theme import load_fonts
from core.sound import play as play_sound
import threading
```

Add new hotkey constant after existing ones:

```python
HOTKEY_ID_INTERRUPT = 2   # Alt+Shift+L
MOD_SHIFT = 0x0004
```

- [ ] **Step 2: Add `interrupt_fired` signal to `AppSignals`**

```python
class AppSignals(QObject):
    ping_fired       = pyqtSignal()
    idle_returned    = pyqtSignal(int)
    overdue_fired    = pyqtSignal(int)
    hotkey_fired     = pyqtSignal()
    interrupt_fired  = pyqtSignal()   # new
```

- [ ] **Step 3: Update `HotkeyListener.run` to register second hotkey**

```python
def run(self):
    result1 = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, MOD_ALT, 0x4C)
    result2 = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID_INTERRUPT, MOD_ALT | MOD_SHIFT, 0x4C)
    if not result1:
        print(f"[Hotkey] RegisterHotKey Alt+L failed: {ctypes.GetLastError()}")
    if not result2:
        print(f"[Hotkey] RegisterHotKey Alt+Shift+L failed: {ctypes.GetLastError()}")
    msg = ctypes.wintypes.MSG()
    while True:
        ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
        if ret == 0 or ret == -1:
            break
        if msg.message == WM_HOTKEY:
            if msg.wParam == HOTKEY_ID:
                self.signal.hotkey_fired.emit()
            elif msg.wParam == HOTKEY_ID_INTERRUPT:
                self.signal.interrupt_fired.emit()
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
    ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
    ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID_INTERRUPT)
```

- [ ] **Step 4: Update `WorkPulse.__init__` to load fonts, create interrupt popup, wire signals, and trigger startup sync**

In `WorkPulse.__init__`, at the very start (before anything else), add font loading:

```python
load_fonts()
```

Then add interrupt popup creation after `self.settings_window`:

```python
self.interrupt_popup = InterruptLogPopup()
self.interrupt_popup.logged.connect(self._on_interrupt_logged)
```

Wire the new signal in the signals section:

```python
self.signals.interrupt_fired.connect(self._show_interrupt_log)
```

Wire the status bar interrupt button:

```python
self.status_bar.interrupt_requested.connect(self._show_interrupt_log)
```

Wire overdue and idle signals to status bar state:

```python
self.signals.overdue_fired.connect(lambda mins: self.status_bar.set_overdue())
self.signals.idle_returned.connect(lambda mins: self.status_bar.set_idle())
```

Trigger startup Clockify sync (after all UI is built):

```python
threading.Thread(target=self._startup_clockify_sync, daemon=True).start()
```

- [ ] **Step 5: Add new handler methods to `WorkPulse`**

```python
def _show_interrupt_log(self):
    self.interrupt_popup.show()
    self.interrupt_popup.raise_()
    self.interrupt_popup.activateWindow()

def _on_interrupt_logged(self):
    self.status_bar.refresh()
    self.tray.show_toast("Logged ⚡", "Quick task noted.")

def _startup_clockify_sync(self):
    from core.clockify import sync_projects_to_cache, is_configured
    if is_configured():
        print("[Startup] Syncing Clockify projects...")
        sync_projects_to_cache()
```

- [ ] **Step 6: Add sound calls to existing event handlers**

```python
def _show_ping(self):
    play_sound("ping")          # add this line
    self.ping_popup.show()
    self.ping_popup.raise_()
    self.ping_popup.activateWindow()

def _on_overdue(self, minutes: int):
    play_sound("overdue")       # add this line
    self.tray.set_icon_overdue()
    self.tray.show_toast(
        "⚠ Hey Farhan!",
        f"You've been active {minutes} min with nothing logged. Alt+L!"
    )

def _on_idle_return(self, idle_minutes: int):
    play_sound("idle")          # add this line
    self.tray.show_toast(
        "Welcome back!",
        f"You were away {idle_minutes} min. Open log to fill in the gap."
    )

def _check_end_of_day(self):
    # existing logic unchanged, add sound on EOD trigger:
    if now == eod and not self._eod_fired_today:
        play_sound("eod")       # add before existing toast code
        # ... rest unchanged
```

- [ ] **Step 7: Full integration smoke test**

```bash
python main.py
```

Verify:
- App starts without errors
- Alt+L opens quick log
- Alt+Shift+L opens interrupt log
- Ping popup uses new Dotdash styling
- Console shows `[Startup] Syncing Clockify projects...` if API key configured

- [ ] **Step 8: Commit**

```bash
git add main.py
git commit -m "feat: wire interrupt log, sound events, startup Clockify sync, font loading"
```

---

## Task 11: Quick log, Today's Log, and tray icon redesign

**Files:**
- Modify: `ui/quick_log.py`
- Modify: `ui/summary.py`
- Modify: `ui/tray.py` (minor)

- [ ] **Step 1: Apply theme to `ui/quick_log.py`**

Replace the `STYLE` constant and `_setup_window` in `QuickLogPopup`:

```python
# Remove STYLE constant at top of file.
# Add import:
from ui.theme import get_colors, base_stylesheet

# In _setup_window:
def _setup_window(self):
    self.setWindowFlags(
        Qt.WindowType.FramelessWindowHint |
        Qt.WindowType.WindowStaysOnTopHint |
        Qt.WindowType.Tool
    )
    self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    self.setFixedWidth(420)

# Add new method:
def _apply_theme(self):
    c = get_colors()
    self.setStyleSheet(base_stylesheet(c) + f"""
        QFrame#card {{
            background: {c['s0']};
            border: 1px solid {c['border']};
            border-radius: 14px;
        }}
        QWidget#header {{
            background: {c['s1']};
            border-radius: 14px 14px 0 0;
            border-bottom: 1px solid {c['border']};
        }}
        QFrame#activeFrame {{
            background: {c['s1']};
            border: 1px solid {c['border']};
            border-radius: 8px;
        }}
        QPushButton#btnEndTask {{
            background: {c['red_bg']};
            border: 1px solid {c['red_border']};
            color: {c['red']};
            text-align: left;
        }}
        QPushButton#btnEndTask:hover {{ background: rgba(252,165,165,0.13); }}
    """)

# Call _apply_theme() in showEvent before super().showEvent(event)
```

Update card `QFrame` and `header_bar` `QWidget` `objectName` to `"card"` and `"header"` respectively, and `active_frame` to `"activeFrame"`.

- [ ] **Step 2: Apply theme to `ui/summary.py`**

Replace the `STYLE` constant with a theme-based approach:

```python
# Remove STYLE constant.
# Add import:
from ui.theme import get_colors, base_stylesheet

# In SummaryWindow._setup_window, replace setStyleSheet call:
def _apply_theme(self):
    c = get_colors()
    self.setStyleSheet(base_stylesheet(c) + f"""
        QWidget#toolbar {{
            background: {c['s1']};
            border-bottom: 1px solid {c['border']};
        }}
        QWidget#footer {{
            background: {c['s1']};
            border-top: 1px solid {c['border']};
        }}
    """)

# Call self._apply_theme() in __init__ after _setup_ui()
```

Update `EntryRow` hover style to use `c['s2']` instead of hardcoded `#1c1c22`:

```python
# In EntryRow.__init__, replace hardcoded style:
c = get_colors()
self.setStyleSheet(f"QFrame {{ background: transparent; border-radius: 8px; }} QFrame:hover {{ background: {c['s2']}; }}")
```

Update `GapRow` to use theme red:

```python
c = get_colors()
self.setStyleSheet(f"QFrame {{ background: {c['red_bg']}; border: 1px solid {c['red_border']}; border-radius: 8px; }}")
```

- [ ] **Step 3: Verify both windows open cleanly**

```bash
python -c "
from PyQt6.QtWidgets import QApplication
import sys
app = QApplication(sys.argv)
from ui.theme import load_fonts
load_fonts()
from ui.quick_log import QuickLogPopup
from ui.summary import SummaryWindow
q = QuickLogPopup(); q.show()
s = SummaryWindow(); s.show()
print('OK')
"
```

Expected: `OK` with no errors

- [ ] **Step 4: Commit**

```bash
git add ui/quick_log.py ui/summary.py
git commit -m "feat: apply Dotdash theme to quick log and summary windows"
```

---

## Task 12: Run all tests and final build verification

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: all tests PASS (12 tests total across 3 test files)

- [ ] **Step 2: Run the app end-to-end**

```bash
python main.py
```

Verify checklist:
- [ ] App starts, shows "Good morning" toast
- [ ] Alt+L opens quick log (Dotdash styled)
- [ ] Alt+Shift+L opens interrupt log
- [ ] Ping fires after interval — sound plays, Dotdash popup shown
- [ ] With no active task: ping shows "Good morning / What are you starting with?"
- [ ] With active task: ping shows "Still on it / Done / Switch" options
- [ ] Status bar: green dot when active, red when overdue
- [ ] Status bar ⚡ button visible on hover, opens interrupt log
- [ ] Settings → Clockify → Sync Projects fetches from API and updates last-synced label
- [ ] Settings → Sound → Play On saves correctly

- [ ] **Step 3: Build EXE**

```bash
build.bat
```

Expected: `dist/WorkPulse.exe` created without errors

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "feat: WorkPulse redesign complete — Dotdash brand, sound, Clockify sync, interrupt log"
```

---

## Spec Coverage Check

| Spec Section | Covered by |
|---|---|
| Visual design system (colors, font, dot states) | Tasks 1, 6, 7, 8, 9, 11 |
| Light / Night mode toggle | Task 1 (theme.py tokens); wired through `get_colors()` — toggling `DARK_MODE` in settings applies on next window open |
| Ping popup first-ping-of-day | Task 6 |
| Sound on popup | Tasks 3, 10 |
| Clockify project sync | Tasks 4, 9, 10 |
| Interrupt log (UI + data) | Tasks 5, 7, 10 |
| Status bar states | Task 8 |
| Settings additions (Play On, Sync, last-synced) | Task 9 |
| Today's Log redesign | Task 11 |
| Quick log redesign | Task 11 |
