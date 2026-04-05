"""Tests for database.log_interrupt."""
import pytest
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch


@pytest.fixture
def mem_db(tmp_path, monkeypatch):
    """Patch DB_FILE to a temp file and init schema."""
    db_path = tmp_path / "test.db"
    monkeypatch.setattr("core.database.DB_FILE", db_path)
    from core import database
    database.init_db()
    return database


def test_log_interrupt_creates_completed_entry(mem_db):
    with patch("core.database._push_to_clockify"):
        mem_db.log_interrupt(
            project_id="internal_office",
            project_name="Internal - Office",
            task="Special Task \u2014 Reply customer email",
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
            task="Meeting \u2014 kickoff",
        )
        mem_db.log_interrupt(
            project_id="internal_office",
            project_name="Internal - Office",
            task="Special Task \u2014 quick email",
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
            task="Special Task \u2014 email",
            duration_minutes=15,
        )
    entries = mem_db.get_entries_for_date()
    e = entries[0]
    start = datetime.strptime(e["start_time"], "%H:%M")
    end = datetime.strptime(e["end_time"], "%H:%M")
    diff = int((end - start).total_seconds() // 60)
    assert diff == 15
