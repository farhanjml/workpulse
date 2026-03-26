"""
core/timer.py — Ping timer + idle detection
Uses Windows API to detect mouse/keyboard idle time.
"""

import ctypes
import threading
from datetime import datetime
from core import config


class IdleDetector:
    def get_idle_seconds(self) -> int:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
        millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
        return millis // 1000

    def is_idle(self) -> bool:
        threshold_mins = config.get_int("IDLE_THRESHOLD")
        return self.get_idle_seconds() > (threshold_mins * 60)


class PingTimer:
    def __init__(self, ping_callback, idle_callback, overdue_callback):
        self.ping_callback = ping_callback
        self.idle_callback = idle_callback
        self.overdue_callback = overdue_callback
        self.idle_detector = IdleDetector()
        self._running = False
        self._thread = None
        self._lock = threading.Lock()
        self._last_log_time = datetime.now()
        self._was_idle = False
        self._idle_start = None
        self._ping_due_at = None
        self._overdue_fired = False
        self._reset_ping_timer()

    def _reset_ping_timer(self):
        interval = config.get_int("PING_INTERVAL")
        now = datetime.now()
        self._ping_due_at = now.timestamp() + (interval * 60)
        self._overdue_fired = False

    def on_user_logged(self):
        with self._lock:
            self._last_log_time = datetime.now()
            self._reset_ping_timer()

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        CHECK_INTERVAL = 10
        while self._running:
            threading.Event().wait(CHECK_INTERVAL)
            now = datetime.now()
            is_idle = self.idle_detector.is_idle()

            if is_idle:
                if not self._was_idle:
                    self._was_idle = True
                    self._idle_start = now
                    self._reset_ping_timer()
                continue

            if self._was_idle:
                self._was_idle = False
                idle_duration = (now - self._idle_start).seconds // 60
                self._idle_start = None
                self._reset_ping_timer()
                self.idle_callback(idle_duration)
                continue

            if now.timestamp() >= self._ping_due_at:
                self._reset_ping_timer()
                self.ping_callback()

            overdue_mins = config.get_int("OVERDUE_WARNING")
            minutes_since_log = (now - self._last_log_time).seconds // 60
            if minutes_since_log >= overdue_mins and not self._overdue_fired:
                self._overdue_fired = True
                self.overdue_callback(minutes_since_log)
