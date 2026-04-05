"""
core/database.py — SQLite operations
All log entries stored in AppData\Local\WorkPulse\workpulse.db
"""

import sqlite3
import threading
import requests
from datetime import datetime, date, timedelta
from contextlib import contextmanager
from core.config import DB_FILE, ensure_app_dir, load_projects, get


def get_connection():
    ensure_app_dir()
    conn = sqlite3.connect(str(DB_FILE))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def db():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS entries (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                date         TEXT NOT NULL,
                start_time   TEXT NOT NULL,
                end_time     TEXT,
                project_id   TEXT NOT NULL,
                project_name TEXT NOT NULL,
                task         TEXT NOT NULL,
                notes        TEXT DEFAULT '',
                is_break     INTEGER DEFAULT 0,
                created_at   TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS day_meta (
                date       TEXT PRIMARY KEY,
                work_start TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            );

            CREATE INDEX IF NOT EXISTS idx_entries_date ON entries(date);
        """)


def get_active_entry(today: str = None) -> dict | None:
    today = today or date.today().isoformat()
    with db() as conn:
        row = conn.execute(
            "SELECT * FROM entries WHERE date=? AND end_time IS NULL ORDER BY id DESC LIMIT 1",
            (today,)
        ).fetchone()
        return dict(row) if row else None


def close_active_entry(end_time: str, today: str = None):
    today = today or date.today().isoformat()
    with db() as conn:
        conn.execute(
            "UPDATE entries SET end_time=? WHERE date=? AND end_time IS NULL",
            (end_time, today)
        )


def add_entry(project_id, project_name, task, start_time, end_time=None, notes="", is_break=False, today=None) -> int:
    today = today or date.today().isoformat()
    with db() as conn:
        cursor = conn.execute(
            """INSERT INTO entries
               (date, start_time, end_time, project_id, project_name, task, notes, is_break)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (today, start_time, end_time, project_id, project_name, task, notes, int(is_break))
        )
        return cursor.lastrowid


def _get_clockify_project_id(project_id: str) -> str:
    projects = load_projects()
    for p in projects:
        if p["id"] == project_id:
            return p.get("clockify_project_id", "")
    return ""


def _clean_task(task: str) -> str:
    """Strip task type prefix for Clockify. 'Meeting — xyz' → 'xyz'"""
    if " \u2014 " in task:
        return task.split(" \u2014 ", 1)[1]
    if " - " in task:
        return task.split(" - ", 1)[1]
    return task


def _push_to_clockify(entry: dict, end_time: str):
    """Push a completed entry to Clockify in background thread."""
    def _run():
        try:
            from core.clockify import create_completed_entry, is_configured
            if not is_configured():
                return
            clockify_pid = _get_clockify_project_id(entry["project_id"])
            if not clockify_pid:
                print(f"[Clockify] No mapping for {entry['project_id']}")
                return
            create_completed_entry(
                project_id=clockify_pid,
                description=_clean_task(entry["task"]),
                start_time=entry["start_time"],
                end_time=end_time,
                entry_date=entry["date"],
            )
        except Exception as e:
            print(f"[Clockify] Push error: {e}")
    threading.Thread(target=_run, daemon=True).start()


def log_entry(project_id, project_name, task, stopped_at=None, notes="") -> int:
    now = datetime.now().strftime("%H:%M")
    start_time = stopped_at or now
    today = date.today().isoformat()

    # Get active entry before closing it
    active = get_active_entry()

    # Close active entry at start_time
    close_active_entry(start_time)

    # Push closed entry to Clockify as completed
    if active and not active.get("is_break"):
        _push_to_clockify(active, start_time)

    # Open new entry
    return add_entry(
        project_id=project_id,
        project_name=project_name,
        task=task,
        start_time=start_time,
        notes=notes,
        today=today
    )


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

    entry = {
        "project_id": project_id,
        "task": task,
        "start_time": start_time,
        "date": today,
        "is_break": False,
    }
    _push_to_clockify(entry, end_time)
    return entry_id


def extend_active_entry():
    pass


def end_current_entry(stopped_at=None):
    stopped_at = stopped_at or datetime.now().strftime("%H:%M")
    active = get_active_entry()
    close_active_entry(stopped_at)
    if active and not active.get("is_break"):
        _push_to_clockify(active, stopped_at)


def get_entries_for_date(target_date=None) -> list[dict]:
    target_date = target_date or date.today().isoformat()
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM entries WHERE date=? ORDER BY start_time ASC", (target_date,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_entries_for_week(week_start: str) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM entries WHERE date >= ? AND date <= date(?, '+6 days') ORDER BY date, start_time",
            (week_start, week_start)
        ).fetchall()
        return [dict(r) for r in rows]


def update_entry(entry_id: int, **kwargs):
    allowed = {"start_time", "end_time", "project_id", "project_name", "task", "notes"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k}=?" for k in fields)
    with db() as conn:
        conn.execute(f"UPDATE entries SET {set_clause} WHERE id=?", (*fields.values(), entry_id))


def delete_entry(entry_id: int):
    with db() as conn:
        conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))


def set_work_start(start_time: str, today=None):
    today = today or date.today().isoformat()
    with db() as conn:
        conn.execute("INSERT OR REPLACE INTO day_meta (date, work_start) VALUES (?, ?)", (today, start_time))


def get_work_start(today=None) -> str | None:
    today = today or date.today().isoformat()
    with db() as conn:
        row = conn.execute("SELECT work_start FROM day_meta WHERE date=?", (today,)).fetchone()
        return row["work_start"] if row else None


def get_merged_entries(target_date=None) -> list[dict]:
    entries = get_entries_for_date(target_date)
    if not entries:
        return []
    merged = []
    current = None
    for entry in entries:
        if (current and entry["project_id"] == current["project_id"]
                and entry["task"] == current["task"]
                and not entry["is_break"] and not current["is_break"]):
            current["end_time"] = entry["end_time"]
            current["_merged_ids"].append(entry["id"])
        else:
            if current:
                merged.append(current)
            current = dict(entry)
            current["_merged_ids"] = [entry["id"]]
    if current:
        merged.append(current)
    return merged


def count_entries_today() -> int:
    today = date.today().isoformat()
    with db() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM entries WHERE date=? AND is_break=0", (today,)
        ).fetchone()
        return row["cnt"] if row else 0


def get_top_tasks(limit: int = 3) -> list[dict]:
    with db() as conn:
        rows = conn.execute(
            """SELECT project_id, project_name, task, COUNT(*) as cnt
               FROM entries WHERE is_break=0
               GROUP BY project_id, task ORDER BY cnt DESC LIMIT ?""",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_total_logged_minutes(target_date=None) -> int:
    target_date = target_date or date.today().isoformat()
    entries = get_entries_for_date(target_date)
    total = 0
    for e in entries:
        if e["end_time"] and not e["is_break"]:
            start = datetime.strptime(e["start_time"], "%H:%M")
            end = datetime.strptime(e["end_time"], "%H:%M")
            total += (end - start).seconds // 60
    return total
