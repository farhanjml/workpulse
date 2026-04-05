"""
core/clockify.py — Clockify REST API integration
Creates completed time entries (with start + end time) — no running timers.
"""

import requests
from datetime import datetime, date, timezone, timedelta
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
