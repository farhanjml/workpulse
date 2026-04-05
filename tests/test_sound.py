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
