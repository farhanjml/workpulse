"""
core/clockify.py — Clockify REST API integration
Creates completed time entries (with start + end time) — no running timers.
"""

import re
import json
import requests
from datetime import datetime, date, timezone, timedelta
from pathlib import Path
from core import config

BASE_URL = "https://api.clockify.me/api/v1"
WORKSPACE_ID = "682c279d9eb4d30a38976325"


def _get_api_key() -> str:
    key = config.get("CLOCKIFY_API_KEY", "")
    if not key:
        return ""
    return key.strip().strip("'\"").strip()


def _headers() -> dict:
    key = _get_api_key()
    if not key:
        raise ValueError("Clockify API key not configured.")
    return {"X-Api-Key": key, "Content-Type": "application/json"}


def is_configured() -> bool:
    return bool(_get_api_key())


def _to_iso(entry_date: str, t: str) -> str:
    """Convert YYYY-MM-DD + HH:MM (MYT) to UTC ISO string for Clockify."""
    dt = datetime.strptime(f"{entry_date} {t}", "%Y-%m-%d %H:%M")
    myt = timezone(timedelta(hours=8))
    dt_myt = dt.replace(tzinfo=myt)
    dt_utc = dt_myt.astimezone(timezone.utc)
    return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")


def create_completed_entry(
    project_id: str,
    description: str,
    start_time: str,
    end_time: str,
    entry_date: str = None
) -> bool:
    """
    Create a completed time entry in Clockify with both start and end time.
    No running timer — just a clean logged entry.
    """
    if not is_configured():
        return False

    entry_date = entry_date or date.today().isoformat()

    payload = {
        "start": _to_iso(entry_date, start_time),
        "end": _to_iso(entry_date, end_time),
        "description": description,
        "projectId": project_id,
        "billable": False,
    }

    try:
        resp = requests.post(
            f"{BASE_URL}/workspaces/{WORKSPACE_ID}/time-entries",
            headers=_headers(),
            json=payload,
            timeout=10
        )
        resp.raise_for_status()
        print(f"[Clockify] ✓ Logged: {description} | {start_time} - {end_time}")
        return True
    except Exception as e:
        print(f"[Clockify] ✗ Error: {e}")
        return False


def sync_entry(entry: dict, clockify_project_id: str) -> bool:
    """Sync a completed WorkPulse entry to Clockify."""
    if not is_configured() or not clockify_project_id:
        return False
    if not entry.get("end_time"):
        return False
    return create_completed_entry(
        project_id=clockify_project_id,
        description=entry["task"],
        start_time=entry["start_time"],
        end_time=entry["end_time"],
        entry_date=entry["date"],
    )


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


def fetch_tasks(workspace_id: str, project_id: str) -> list:
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

    config.set("LAST_CLOCKIFY_SYNC", datetime.now().strftime("%Y-%m-%d %H:%M"))
    print(f"[Clockify] Synced {len(result)} projects")
    return True
