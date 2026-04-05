# WorkPulse Redesign — Design Spec
**Date:** 2026-04-05  
**Author:** Farhan (Dotdash Technologies Sdn Bhd)  
**Status:** Approved

---

## Overview

A comprehensive improvement to WorkPulse covering three functional gaps and a full visual redesign aligned to the Dotdash Technologies brand identity.

### Problems Being Solved
1. Ping popup fires even when no task has been tracked yet (start of day)
2. No sound plays when the popup appears — setting exists but is a stub
3. Projects and tasks are hardcoded in `projects.json` instead of fetched from the Clockify API
4. Visual design lacks brand identity and personality

---

## 1. Visual Design System

### Brand Palette
| Token | Night Mode | Light Mode | Usage |
|---|---|---|---|
| `--gold` | `#e9bb51` | `#e9bb51` | Buttons, sliders, focus rings, elapsed time |
| `--bg` | `#030404` | `#f5f0e8` | Page/window background |
| `--s0`–`--s3` | `#080909`–`#1a1b1b` | `#fffdf8`–`#e8e0d0` | Layered surfaces |
| `--state-active` | `#4ade80` | `#16a34a` | Running task dot |
| `--state-overdue` | `#ef4444` | `#dc2626` | Overdue / nothing logged dot |
| `--state-idle` | `#3d3b37` | `#b0a898` | AFK / idle dot |

### Typography
- **UI font:** `Sora` (Google Fonts) — geometric, clean, not monospace
- **Mono font:** `JetBrains Mono` — used only for time values and hotkey labels

### Status Dot System (used consistently across all UI)
- 🟢 **Green** — task is actively running
- 🔴 **Red** — overdue or nothing logged (45+ min)
- ⚫ **Gray** — idle / AFK

### Light / Night Mode
- Toggled via a setting (persisted in `config.env` as `DARK_MODE`)
- Light mode uses warm cream `#f5f0e8` base — not cold white
- All CSS variables swap via `body.light` class
- Both modes use the same `#e9bb51` gold accent

---

## 2. Ping Popup

### Normal Ping (active task exists)
- **Header:** `WORKPULSE · PING` wordmark + pulsing green dot + streak badge (`🔥 N entries today`)
- **Active task chip:** green dot + task name + project + elapsed time (e.g. `1h 23m`)
- **Three actions:**
  1. ✓ Still on it — keep going (green outline button)
  2. ⏹ Done with this task (red outline) + "ended at" time dropdown
  3. OR SWITCHED TO SOMETHING NEW — description input + project dropdown + task type dropdown + "switched at" time dropdown → **Log New Task** gold button
- **Footer:** keyboard hint (`Tab · Enter · Esc`) + auto-close countdown (`auto-closing in Xs`)
- **Auto-dismiss:** 60 seconds, silently continues current task

### First Ping of Day (no active task)
- Triggered when `database.get_active_entry()` returns `None`
- **No** "Still on it" or "Done with this task" options shown
- Header badge changes to `✦ Day start` (muted, non-streak)
- Hero text: `Good morning, [FirstName]` / `What are you starting with?`
- Single focused form: description + project + task type + "started at" time dropdown
- CTA: **Start Tracking** (full-width gold button)

---

## 3. Sound on Popup

### Implementation
- Use Python `winsound` (stdlib, no extra dependency) for `.wav` playback on Windows
- Sound files stored in `sounds/` directory, already present in repo
- Play sound in a daemon thread to avoid blocking the UI
- **Volume:** `winsound` does not support volume control — volume is respected at the Windows system level only. The `VOLUME` setting will be preserved in config for future use but will not affect playback in this version. The Settings slider remains visible but shows a `(system volume)` note.

### Trigger Points (configurable)
- Setting: `PLAY_ON` with values `all` / `ping_only` / `ping_overdue` / `none`
- **All events:** ping popup, overdue toast, idle-return toast, end-of-day toast

### Settings UI Addition
- Existing `SOUND_THEME` and `VOLUME` settings remain
- New **"Play on"** dropdown: `All events` / `Ping only` / `Ping + Overdue` / `None`

---

## 4. Clockify Projects & Tasks from API

### Problem
`projects.json` is manually maintained. When a new project is added in Clockify, the user must manually update the file.

### Solution
Fetch projects and their tasks from the Clockify REST API and cache locally.

### API Endpoints Used
- `GET /workspaces/{workspaceId}/projects` — fetch all projects
- `GET /workspaces/{workspaceId}/projects/{projectId}/tasks` — fetch tasks per project

### Sync Behaviour
- **On startup:** auto-sync in a background daemon thread if API key is configured; no blocking of app launch
- **Manual sync:** "↻ Sync" button in Settings → Clockify section
- **Cache:** result written back to `data/projects.json` (existing format preserved for compatibility)
- **Last synced timestamp** displayed in Settings below the Sync button (e.g. `Synced today 09:02 · 9 projects loaded`)
- **Failure handling:** if sync fails, silently fall back to cached `projects.json`; show error only on manual sync

### `projects.json` Format (unchanged)
```json
[
  {
    "id": "internal_rdrs",
    "name": "Internal - RDRS",
    "clockify_project_id": "abc123",
    "tasks": ["Discussion (External)", "Meeting", "Document"]
  }
]
```
The `id` field remains a stable local slug. `clockify_project_id` and `tasks` are overwritten on sync.

**Generating `id` for new API-fetched projects:** use `re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')` to slugify the project name (e.g. `"Maybank MY - RDRS"` → `"maybank_my_rdrs"`). Existing entries with a matching `clockify_project_id` keep their existing `id` to avoid breaking historical log data.

### New functions in `core/clockify.py`
- `fetch_projects(workspace_id) -> list` — GET projects
- `fetch_tasks(workspace_id, project_id) -> list[str]` — GET task names for a project
- `sync_projects_to_cache() -> bool` — orchestrates fetch + write to `projects.json`

---

## 5. Interrupt Log

### Purpose
While a main task is running, the user occasionally does a quick unrelated task (reply to email, quick research, brief meeting). They want to record this without disrupting the main task timer.

### Behaviour
- Main task timer continues running — **no** stopping, switching, or resuming
- Interrupt entry is written as a standalone log entry with the chosen duration
- Both entries (main task + interrupt) will overlap in time in Today's Log — this is intentional and acceptable

### UI
- **Trigger:** `Alt+Shift+L` hotkey OR `⚡` button visible on status bar pill hover
- **Header:** `QUICK INTERRUPT` wordmark + `Alt+Shift+L` hint
- **"Still running" chip:** shows current task name + project + elapsed, with a pulsing green dot and `still running` label
- **Input:** description text field
- **Project + task type dropdowns** (compact, same as other popups)
- **Duration quick-picks:** `5m` / `10m` / `15m` / `30m` / `Custom…` — pill buttons, one selected at a time
- **CTA:** `⚡ Quick Log` (gold button, full width)
- **Footer:** `Enter to log · Esc to cancel` / `main task keeps running`

### Data
- Calls `database.log_interrupt(project_id, project_name, task, duration_minutes)` 
- Writes a completed entry with `start_time = now - duration_minutes`, `end_time = now`
- Does **not** call `timer.on_user_logged()` — ping timer is unaffected

---

## 6. Today's Log (Redesign)

### Layout
- **Toolbar:** `←` date nav + date label + `→` + Day/Week toggle + total logged time (right)
- **Entry rows:** `HH:MM – HH:MM` (mono) · colored project badge · task description · duration · copy ⎘ · delete ✕
- **Active entry:** gold-tinted row background + `active` duration label in gold
- **Gap row:** red-tinted row with `⚠ HH:MM – HH:MM · Unaccounted gap`
- **Break row:** subtle horizontal divider with `☕ Break · Nm`
- **Footer:** Copy All · Export .txt · Export CSV + entry/gap/break count summary

### Project Badge Colors
Each project gets a consistent accent color (existing `PROJECT_COLORS` dict in `ui/summary.py`) — preserved from current implementation.

---

## 7. Status Bar Pill

### States
| State | Dot | Border | Time chip |
|---|---|---|---|
| Active | Green `#4ade80` pulsing | default | gold tint |
| Overdue | Red `#ef4444` fast pulse | red tint | red tint |
| Idle/AFK | Gray `#3d3b37` static | default, 45% opacity | gray |

### Hover
- Slight background lift + border brightens
- `⚡` quick interrupt button appears on right side of pill on hover (when active task exists)

---

## 8. Settings Window Additions

### New fields
- **Sound → Play on:** dropdown (`All events` / `Ping only` / `Ping + Overdue` / `None`)
- **Clockify → Sync button:** `↻ Sync` gold button, triggers `sync_projects_to_cache()`
- **Clockify → Last synced:** `Synced [date] [time] · N projects loaded` status line
- **Clockify → Project chips:** compact preview of loaded projects

### Existing fields unchanged
All existing settings (TIMING, HOTKEY, BEHAVIOUR, SOUND theme/volume) remain as-is.

---

## File Changes Summary

| File | Change |
|---|---|
| `core/clockify.py` | Add `fetch_projects`, `fetch_tasks`, `sync_projects_to_cache` |
| `core/config.py` | Add `PLAY_ON` default; update `load_projects` to accept synced data |
| `core/timer.py` | No changes |
| `core/database.py` | Add `log_interrupt(project_id, project_name, task, duration_minutes)` |
| `main.py` | Add `Alt+Shift+L` hotkey; trigger startup Clockify sync; wire interrupt popup |
| `ui/ping_popup.py` | First-ping-of-day detection + redesigned UI |
| `ui/quick_log.py` | Renamed/repurposed or kept as-is (Alt+L full switch) |
| `ui/interrupt_log.py` | **New file** — interrupt log popup |
| `ui/status_bar.py` | Green/red/gray dot states; ⚡ button on hover |
| `ui/summary.py` | Redesigned entry rows, gap/break rows, footer |
| `ui/settings.py` | Add Play On dropdown, Sync button, last-synced label, project chips |
| `ui/tray.py` | No structural changes |
| All UI files | Apply Dotdash design tokens (font, colors, radius, spacing) |
