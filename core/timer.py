"""
core/timer.py — Ping timer + idle detection
Uses Windows API to detect mouse/keyboard idle time.
"""

import ctypes
import time
import threading
from core import config


class IdleDetector:
    def get_idle_seconds(self) -> int:
        try:
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
                return 0
            # GetTickCount returns DWORD — handle wraparound with unsigned subtraction
            tick_now = ctypes.windll.kernel32.GetTickCount() & 0xFFFFFFFF
            tick_last = lii.dwTime & 0xFFFFFFFF
            millis = (tick_now - tick_last) & 0xFFFFFFFF
            return millis // 1000
        except Exception:
            return 0

    def is_idle(self) -> bool:
        threshold_mins = config.get_int("IDLE_THRESHOLD")
        idle_secs = self.get_idle_seconds()
        return idle_secs > (threshold_mins * 60)


class PingTimer:
    def __init__(self, ping_callback, idle_callback, overdue_callback):
        self.ping_callback = ping_callback
        self.idle_callback = idle_callback
        self.overdue_callback = overdue_callback

        self.idle_detector = IdleDetector()
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

        self._last_log_time = time.monotonic()
        self._next_ping_time = time.monotonic() + (config.get_int("PING_INTERVAL") * 60)
        self._was_idle = False
        self._idle_start = None
        self._overdue_fired = False

    def _reset_ping_timer(self):
        with self._lock:
            interval_secs = config.get_int("PING_INTERVAL") * 60
            self._next_ping_time = time.monotonic() + interval_secs
            self._overdue_fired = False

    def on_user_logged(self):
        with self._lock:
            self._last_log_time = time.monotonic()
            interval_secs = config.get_int("PING_INTERVAL") * 60
            self._next_ping_time = time.monotonic() + interval_secs
            self._overdue_fired = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.name = "WorkPulse-PingTimer"
        self._thread.start()

    def stop(self):
        self._running = False

    def _loop(self):
        print("[Timer] Loop started")
        CHECK_INTERVAL = 5  # Check every 5 seconds for more responsiveness

        while self._running:
            time.sleep(CHECK_INTERVAL)

            now = time.monotonic()
            idle_secs = self.idle_detector.get_idle_seconds()
            threshold_secs = config.get_int("IDLE_THRESHOLD") * 60
            is_idle = idle_secs > threshold_secs

            if is_idle:
                if not self._was_idle:
                    print(f"[Timer] User went idle (idle={idle_secs}s)")
                    self._was_idle = True
                    self._idle_start = now
                    with self._lock:
                        # Pause ping while idle
                        interval_secs = config.get_int("PING_INTERVAL") * 60
                        self._next_ping_time = now + interval_secs
                continue

            if self._was_idle:
                print(f"[Timer] User returned from idle")
                self._was_idle = False
                if self._idle_start:
                    idle_mins = int((now - self._idle_start) // 60)
                    self._idle_start = None
                    with self._lock:
                        interval_secs = config.get_int("PING_INTERVAL") * 60
                        self._next_ping_time = now + interval_secs
                    try:
                        self.idle_callback(idle_mins)
                    except Exception as e:
                        print(f"[Timer] idle_callback error: {e}")
                continue

            # Check if ping is due
            with self._lock:
                next_ping = self._next_ping_time

            if now >= next_ping:
                print(f"[Timer] Ping firing!")
                self._reset_ping_timer()
                try:
                    self.ping_callback()
                except Exception as e:
                    print(f"[Timer] ping_callback error: {e}")

            # Check overdue
            with self._lock:
                last_log = self._last_log_time
                overdue_fired = self._overdue_fired

            overdue_secs = config.get_int("OVERDUE_WARNING") * 60
            since_log = now - last_log
            if since_log >= overdue_secs and not overdue_fired:
                with self._lock:
                    self._overdue_fired = True
                mins_since_log = int(since_log // 60)
                print(f"[Timer] Overdue firing! ({mins_since_log} mins)")
                try:
                    self.overdue_callback(mins_since_log)
                except Exception as e:
                    print(f"[Timer] overdue_callback error: {e}")
