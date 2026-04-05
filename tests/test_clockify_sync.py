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
         patch("core.clockify._save_projects_cache") as mock_save, \
         patch("core.clockify.is_configured", return_value=True):
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
         patch("core.clockify._save_projects_cache") as mock_save, \
         patch("core.clockify.is_configured", return_value=True):
        from core.clockify import sync_projects_to_cache
        sync_projects_to_cache()
    saved = mock_save.call_args[0][0]
    abc_entry = next(p for p in saved if p["clockify_project_id"] == "proj_abc")
    assert abc_entry["id"] == "my_custom_id"
