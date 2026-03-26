"""
main.py — WorkPulse entry point
"""

import sys
from datetime import datetime
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
import keyboard

from core import database, config
from core.timer import PingTimer
from ui.tray import TrayIcon
from ui.ping_popup import PingPopup
from ui.quick_log import QuickLogPopup
from ui.summary import SummaryWindow
from ui.settings import SettingsWindow


class WorkPulse:
    def __init__(self, app: QApplication):
        self.app = app
        database.init_db()
        self.cfg = config.load_config()

        self.tray = TrayIcon(app)
        self.ping_popup = PingPopup()
        self.quick_log_popup = QuickLogPopup()
        self.summary_window = SummaryWindow()
        self.settings_window = SettingsWindow()

        self.tray.signals.show_ping.connect(self._show_ping)
        self.tray.signals.show_quick.connect(self._show_quick_log)
        self.tray.signals.show_summary.connect(self._show_summary)
        self.tray.signals.show_settings.connect(self._show_settings)
        self.tray.signals.show_idle_return.connect(self._on_idle_return)
        self.tray.signals.show_overdue.connect(self._on_overdue)

        self.ping_popup.logged.connect(self._on_logged)
        self.quick_log_popup.logged.connect(self._on_logged)
        self.settings_window.settings_saved.connect(self._on_settings_saved)

        self.timer = PingTimer(
            ping_callback=self._fire_ping,
            idle_callback=self._fire_idle_return,
            overdue_callback=self._fire_overdue,
        )
        self.timer.start()

        self._register_hotkey()

        self._eod_timer = QTimer()
        self._eod_timer.timeout.connect(self._check_end_of_day)
        self._eod_timer.start(60_000)
        self._eod_fired_today = False

        QTimer.singleShot(1500, self._greet)

    def _greet(self):
        name = config.get("USER_NAME", "Farhan Jamaludin").split()[0]
        self.tray.show_toast(f"Good morning, {name}!", "WorkPulse is running. Press Alt+L to log your first task.")

    def _register_hotkey(self):
        hotkey = config.get("HOTKEY", "alt+l")
        try:
            keyboard.add_hotkey(hotkey, self._fire_quick_log)
        except Exception as e:
            print(f"[Hotkey error] {e}")

    def _fire_ping(self):
        QTimer.singleShot(0, self._show_ping)

    def _fire_quick_log(self):
        QTimer.singleShot(0, self._show_quick_log)

    def _show_ping(self):
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
        count = database.count_entries_today()
        self.tray.show_toast("Logged ✓", f"{count} entries today")

    def _fire_idle_return(self, idle_minutes: int):
        QTimer.singleShot(0, lambda: self._on_idle_return(idle_minutes))

    def _on_idle_return(self, idle_minutes: int):
        self.tray.show_toast("Welcome back!", f"You were away {idle_minutes} min. Open log to fill in the gap.")

    def _fire_overdue(self, minutes: int):
        QTimer.singleShot(0, lambda: self._on_overdue(minutes))

    def _on_overdue(self, minutes: int):
        self.tray.set_icon_overdue()
        self.tray.show_toast("⚠ Hey Farhan!", f"You've been active {minutes} min with nothing logged. Alt+L!")

    def _show_summary(self):
        self.summary_window.refresh()
        self.summary_window.show()
        self.summary_window.raise_()

    def _show_settings(self):
        self.settings_window.show()
        self.settings_window.raise_()

    def _on_settings_saved(self):
        keyboard.unhook_all()
        self._register_hotkey()
        self.tray.show_toast("Settings saved", "Changes applied.")

    def _check_end_of_day(self):
        now = datetime.now().strftime("%H:%M")
        eod = config.get("END_OF_DAY", "18:00")
        if now == eod and not self._eod_fired_today:
            self._eod_fired_today = True
            count = database.count_entries_today()
            total = database.get_total_logged_minutes()
            hrs, mins = total // 60, total % 60
            self.tray.show_toast("End of day — wrap up, Farhan!", f"{count} entries logged today · {hrs}hr {mins}min tracked")
            QTimer.singleShot(3000, self._show_summary)
        if now == "00:00":
            self._eod_fired_today = False


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    pulse = WorkPulse(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
