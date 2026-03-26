"""
core/clockify.py — Clockify REST API integration
Only active if CLOCKIFY_API_KEY is set in config.
"""

import requests
from datetime import datetime, date, timezone, timedelta
from core import config

BASE_URL = "https://api.clockify.me/api/v1"


def _headers() -> dict:
    key = config.get("CLOCKIFY_API_KEY")
    if not key:
        raise ValueError("Clockify API key not configured.")
    return {"X-Api-Key": key, "Content-Type": "application/json"}


def is_configured() -> bool:
    return bool(config.get("CLOCKIFY_API_KEY"))


def fetch_workspaces() -> list[dict]:
    resp = requests.get(f"{BASE_URL}/workspaces", headers=_headers(), timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_projects(workspace_id: str) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/workspaces/{workspace_id}/projects",
        headers=_headers(), params={"page-size": 100}, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def fetch_tasks(workspace_id: str, project_id: str) -> list[dict]:
    resp = requests.get(
        f"{BASE_URL}/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=_headers(), params={"page-size": 100}, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def create_time_entry(workspace_id, project_id, task_id, description, start_time, end_time, entry_date=None) -> dict:
    entry_date = entry_date or date.today().isoformat()

    def to_iso(t: str) -> str:
        dt = datetime.strptime(f"{entry_date} {t}", "%Y-%m-%d %H:%M")
        myt = timezone(timedelta(hours=8))
        dt_myt = dt.replace(tzinfo=myt)
        dt_utc = dt_myt.astimezone(timezone.utc)
        return dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = {
        "start": to_iso(start_time),
        "end": to_iso(end_time),
        "description": description,
        "projectId": project_id,
        "taskId": task_id,
        "billable": False,
    }
    resp = requests.post(
        f"{BASE_URL}/workspaces/{workspace_id}/time-entries",
        headers=_headers(), json=payload, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def sync_entry(entry: dict, clockify_project_id: str, clockify_task_id: str) -> bool:
    workspace_id = config.get("CLOCKIFY_WORKSPACE_ID")
    if not workspace_id or not clockify_project_id:
        return False
    try:
        create_time_entry(
            workspace_id=workspace_id,
            project_id=clockify_project_id,
            task_id=clockify_task_id,
            description=entry["task"],
            start_time=entry["start_time"],
            end_time=entry["end_time"],
            entry_date=entry["date"],
        )
        return True
    except Exception as e:
        print(f"[Clockify sync error] {e}")
        return False
