"""
ui/tray.py — System tray icon + right-click menu
"""

import sys
import threading
from datetime import datetime
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication
from PyQt6.QtGui import QIcon, QColor, QPixmap
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject

from core import database, config


def make_tray_icon(color: str) -> QIcon:
    """Generate a coloured 'W' icon programmatically."""
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    from PyQt6.QtGui import QPainter, QFont, QBrush
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QBrush(QColor(color)))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)
    font = QFont("Segoe UI", 28, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "W")
    painter.end()

    return QIcon(pixmap)


ICON_GREEN  = "#4ade80"
ICON_YELLOW = "#fbbf24"
ICON_RED    = "#f87171"


class TraySignals(QObject):
    show_ping        = pyqtSignal()
    show_quick       = pyqtSignal()
    show_summary     = pyqtSignal()
    show_settings    = pyqtSignal()
    show_idle_return = pyqtSignal(int)
    show_overdue     = pyqtSignal(int)
    task_ended       = pyqtSignal()


class TrayIcon:
    def __init__(self, app: QApplication):
        self.app = app
        self.signals = TraySignals()
        self.tray = QSystemTrayIcon()
        self.tray.setIcon(make_tray_icon(ICON_GREEN))
        self.tray.setToolTip("WorkPulse — All good")
        self.tray.activated.connect(self._on_activated)
        self._build_menu()
        self.tray.show()

        self._state_timer = QTimer()
        self._state_timer.timeout.connect(self._update_state)
        self._state_timer.start(30_000)

    def _build_menu(self):
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: #141418;
                border: 1px solid #2a2a38;
                border-radius: 8px;
                padding: 4px;
                color: #e8e8f0;
                font-family: 'JetBrains Mono', monospace;
                font-size: 12px;
            }
            QMenu::item { padding: 7px 16px; border-radius: 5px; }
            QMenu::item:selected { background: #242430; }
            QMenu::separator { height: 1px; background: #2a2a38; margin: 3px 8px; }
        """)
        menu.addAction("📋  View Today's Log", lambda: self.signals.show_summary.emit())
        menu.addAction("✏️  Quick Log", lambda: self.signals.show_quick.emit())
        menu.addAction("⏹  End Current Task", self._end_current_task)
        menu.addSeparator()
        menu.addAction("⚙️  Settings", lambda: self.signals.show_settings.emit())
        menu.addSeparator()
        menu.addAction("✕  Exit", self.app.quit)
        self.tray.setContextMenu(menu)

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.signals.show_summary.emit()

    def _end_current_task(self):
        now = datetime.now().strftime("%H:%M")
        database.end_current_entry(now)
        self.show_toast("Task ended ✓", "Entry pushed to Clockify.")
        self._update_state()
        self.signals.task_ended.emit()

    def _update_state(self):
        count = database.count_entries_today()
        total_mins = database.get_total_logged_minutes()
        hours = total_mins // 60
        mins = total_mins % 60
        active = database.get_active_entry()
        if active:
            task_preview = active["task"][:30] + "..." if len(active["task"]) > 30 else active["task"]
            tooltip = f"WorkPulse · {count} entries · {hours}h {mins}m\nNow: {task_preview}"
        else:
            tooltip = f"WorkPulse · {count} entries · {hours}h {mins}m\nNo active task"
        self.tray.setToolTip(tooltip)

        from core.timer import IdleDetector
        idle = IdleDetector()
        if idle.is_idle() or not active:
            self.tray.setIcon(make_tray_icon(ICON_YELLOW))
        else:
            self.tray.setIcon(make_tray_icon(ICON_GREEN))

    def set_icon_overdue(self):
        self.tray.setIcon(make_tray_icon(ICON_RED))

    def set_icon_ok(self):
        self.tray.setIcon(make_tray_icon(ICON_GREEN))

    def show_toast(self, title: str, message: str):
        self.tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 3000)
