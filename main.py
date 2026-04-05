"""
main.py — WorkPulse entry point
Uses proper Qt signals for all cross-thread communication.
"""

import sys
import ctypes
import ctypes.wintypes
import threading
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, pyqtSignal, QObject

from core import database, config
from core.timer import PingTimer
from core.sound import play as play_sound
from ui.tray import TrayIcon
from ui.ping_popup import PingPopup
from ui.quick_log import QuickLogPopup
from ui.summary import SummaryWindow
from ui.settings import SettingsWindow
from ui.status_bar import StatusBar
from ui.interrupt_log import InterruptLogPopup
from ui.theme import load_fonts

# Windows hotkey constants
MOD_ALT   = 0x0001
MOD_CTRL  = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN   = 0x0008
WM_HOTKEY = 0x0312
WM_QUIT   = 0x0012
HOTKEY_ID           = 1
HOTKEY_ID_INTERRUPT = 2


def parse_hotkey(combo: str) -> tuple:
    """Parse 'alt+shift+l' → (modifiers, vk_code). Returns (0, 0) on failure."""
    parts = combo.lower().split("+")
    mods, key = 0, None
    for p in parts:
        if p == "alt":                   mods |= MOD_ALT
        elif p in ("ctrl", "control"):   mods |= MOD_CTRL
        elif p == "shift":               mods |= MOD_SHIFT
        elif p in ("win", "meta"):       mods |= MOD_WIN
        else:                            key = p
    vk = ord(key.upper()) if key and len(key) == 1 else 0
    return mods, vk


class AppSignals(QObject):
    """All cross-thread signals live here."""
    ping_fired       = pyqtSignal()
    idle_returned    = pyqtSignal(int)
    overdue_fired    = pyqtSignal(int)
    hotkey_fired     = pyqtSignal()
    interrupt_fired  = pyqtSignal()   # new signal


class HotkeyListener(threading.Thread):
    def __init__(self, signal: AppSignals):
        super().__init__(daemon=True)
        self.signal = signal
        self._win32_tid = 0

    def stop(self):
        """Post WM_QUIT to this thread's message queue to exit the loop."""
        if self._win32_tid:
            ctypes.windll.user32.PostThreadMessageW(self._win32_tid, WM_QUIT, 0, 0)

    def run(self):
        self._win32_tid = ctypes.windll.kernel32.GetCurrentThreadId()

        hotkey_combo = config.get("HOTKEY", "alt+l")
        interrupt_combo = config.get("INTERRUPT_HOTKEY", "alt+shift+l")
        mods1, vk1 = parse_hotkey(hotkey_combo)
        mods2, vk2 = parse_hotkey(interrupt_combo)

        result = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID, mods1, vk1)
        if not result:
            print(f"[Hotkey] RegisterHotKey ({hotkey_combo}) failed: {ctypes.GetLastError()}")
            return
        print(f"[Hotkey] {hotkey_combo} registered")

        result2 = ctypes.windll.user32.RegisterHotKey(None, HOTKEY_ID_INTERRUPT, mods2, vk2)
        if not result2:
            print(f"[Hotkey] RegisterHotKey ({interrupt_combo}) failed: {ctypes.GetLastError()}")
        else:
            print(f"[Hotkey] {interrupt_combo} registered")

        msg = ctypes.wintypes.MSG()
        while True:
            ret = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret == 0 or ret == -1:
                break
            if msg.message == WM_HOTKEY:
                if msg.wParam == HOTKEY_ID:
                    self.signal.hotkey_fired.emit()
                elif msg.wParam == HOTKEY_ID_INTERRUPT:
                    self.signal.interrupt_fired.emit()
            ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
            ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID)
        ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_ID_INTERRUPT)


class WorkPulse:
    def __init__(self, app: QApplication):
        load_fonts()
        self.app = app
        database.init_db()

        # All signals
        self.signals = AppSignals()
        self.signals.ping_fired.connect(self._show_ping)
        self.signals.idle_returned.connect(self._on_idle_return)
        self.signals.overdue_fired.connect(self._on_overdue)
        self.signals.hotkey_fired.connect(self._show_quick_log)
        self.signals.interrupt_fired.connect(self._show_interrupt_log)

        # UI
        self.tray = TrayIcon(app)
        self.ping_popup = PingPopup()
        self.quick_log_popup = QuickLogPopup()
        self.summary_window = SummaryWindow()
        self.settings_window = SettingsWindow()
        self.status_bar = StatusBar()
        self.interrupt_popup = InterruptLogPopup()
        self.interrupt_popup.logged.connect(self._on_interrupt_logged)

        # Status bar signals
        self.status_bar.interrupt_requested.connect(self._show_interrupt_log)
        self.signals.overdue_fired.connect(lambda mins: self.status_bar.set_overdue())
        self.signals.idle_returned.connect(lambda mins: self.status_bar.set_idle())

        # Tray signals
        self.tray.signals.show_ping.connect(self._show_ping)
        self.tray.signals.show_quick.connect(self._show_quick_log)
        self.tray.signals.show_summary.connect(self._show_summary)
        self.tray.signals.show_settings.connect(self._show_settings)
        self.tray.signals.show_idle_return.connect(self._on_idle_return)
        self.tray.signals.show_overdue.connect(self._on_overdue)
        self.tray.signals.task_ended.connect(self._on_task_ended)

        # Popup signals
        self.ping_popup.logged.connect(self._on_logged)
        self.quick_log_popup.logged.connect(self._on_logged)
        self.quick_log_popup.task_ended.connect(self._on_task_ended)
        self.settings_window.settings_saved.connect(self._on_settings_saved)

        # Ping timer — passes signals so background thread can emit safely
        self.timer = PingTimer(
            ping_callback=lambda: self.signals.ping_fired.emit(),
            idle_callback=lambda mins: self.signals.idle_returned.emit(mins),
            overdue_callback=lambda mins: self.signals.overdue_fired.emit(mins),
        )
        self.timer.start()

        # Hotkey listener
        self._hotkey_listener = HotkeyListener(self.signals)
        self._hotkey_listener.start()

        # Startup Clockify sync
        threading.Thread(target=self._startup_clockify_sync, daemon=True).start()

        # End of day checker
        self._eod_timer = QTimer()
        self._eod_timer.timeout.connect(self._check_end_of_day)
        self._eod_timer.start(60_000)
        self._eod_fired_today = False

        QTimer.singleShot(1500, self._greet)

    def _greet(self):
        name = config.get("USER_NAME", "Farhan Jamaludin").split()[0]
        self.tray.show_toast(
            f"Good morning, {name}!",
            "WorkPulse is running. Press Alt+L to log your first task."
        )

    def _show_ping(self):
        play_sound("ping")
        self.ping_popup.show()
        self.ping_popup.raise_()
        self.ping_popup.activateWindow()

    def _show_quick_log(self):
        self.quick_log_popup.show()
        self.quick_log_popup.raise_()
        self.quick_log_popup.activateWindow()

    def _on_logged(self):
        self.timer.on_user_logged()
        self.tray.set_icon_ok()
        self.status_bar.refresh()
        count = database.count_entries_today()
        self.tray.show_toast("Logged \u2713", f"{count} entries today")

    def _on_task_ended(self):
        self.timer.on_user_logged()
        self.tray.set_icon_ok()
        self.status_bar.refresh()
        self.tray.show_toast("Task ended \u2713", "Entry pushed to Clockify.")

    def _on_idle_return(self, idle_minutes: int):
        play_sound("idle")
        self.tray.show_toast(
            "Welcome back!",
            f"You were away {idle_minutes} min. Open log to fill in the gap."
        )

    def _on_overdue(self, minutes: int):
        play_sound("overdue")
        self.tray.set_icon_overdue()
        self.tray.show_toast(
            "\u26a0 Hey Farhan!",
            f"You've been active {minutes} min with nothing logged. Alt+L!"
        )

    def _show_summary(self):
        self.summary_window.refresh()
        self.summary_window.show()
        self.summary_window.raise_()

    def _show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()

    def _on_settings_saved(self):
        self.tray.show_toast("Settings saved", "Changes applied.")
        self._restart_hotkey_listener()

    def _restart_hotkey_listener(self):
        """Stop the current hotkey listener and start a new one with updated config."""
        old = self._hotkey_listener
        old.stop()
        def _start_new():
            import time
            time.sleep(0.15)   # let old thread exit and unregister
            self._hotkey_listener = HotkeyListener(self.signals)
            self._hotkey_listener.start()
        threading.Thread(target=_start_new, daemon=True).start()

    def _check_end_of_day(self):
        now = datetime.now().strftime("%H:%M")
        eod = config.get("END_OF_DAY", "18:00")
        if now == eod and not self._eod_fired_today:
            self._eod_fired_today = True
            play_sound("eod")
            database.end_current_entry(now)
            self.status_bar.refresh()
            count = database.count_entries_today()
            total = database.get_total_logged_minutes()
            hrs, mins = total // 60, total % 60
            self.tray.show_toast(
                "End of day \u2014 wrap up, Farhan!",
                f"{count} entries logged today \u00b7 {hrs}hr {mins}min tracked"
            )
            QTimer.singleShot(3000, self._show_summary)
        if now == "00:00":
            self._eod_fired_today = False

    def _show_interrupt_log(self):
        self.interrupt_popup.show()
        self.interrupt_popup.raise_()
        self.interrupt_popup.activateWindow()

    def _on_interrupt_logged(self):
        self.status_bar.refresh()
        self.tray.show_toast("Logged \u26a1", "Quick task noted.")

    def _startup_clockify_sync(self):
        from core.clockify import sync_projects_to_cache, is_configured
        if is_configured():
            print("[Startup] Syncing Clockify projects...")
            sync_projects_to_cache()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pulse = WorkPulse(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
