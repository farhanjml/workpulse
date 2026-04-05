"""
ui/status_bar.py — Floating live task indicator.
States: active (green), overdue (red), idle (gray).
Emits interrupt_requested signal when ⚡ button clicked.
"""

from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication, QPushButton
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen

from core import database, config
from ui.theme import get_colors

HIT_PADDING = 20

STATE_COLORS = {
    "active":  ("#4ade80", "#1a4a2a"),   # on, off (pulse)
    "overdue": ("#ef4444", "#4a1a1a"),
    "idle":    ("#3d3b37", "#3d3b37"),   # no pulse
}


class StatusBar(QWidget):
    interrupt_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_task = None
        self._is_expanded = False
        self._state = "active"   # "active" | "overdue" | "idle"
        self._setup_window()
        self._setup_ui()

        self._collapse_timer = QTimer()
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.timeout.connect(self._do_collapse)

        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._silent_refresh)
        self._refresh_timer.start(30_000)

        self._elapsed_timer = QTimer()
        self._elapsed_timer.timeout.connect(self._update_elapsed)
        self._elapsed_timer.start(60_000)

        self._dot_state = True
        self._dot_timer = QTimer()
        self._dot_timer.timeout.connect(self._pulse_dot)
        self._dot_timer.start(1500)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

    def _setup_ui(self):
        self._inner = QWidget(self)
        inner_layout = QHBoxLayout(self._inner)
        inner_layout.setContentsMargins(10, 0, 10, 0)
        inner_layout.setSpacing(6)

        self.lbl_dot = QLabel("●")
        self.lbl_dot.setStyleSheet("color: #4ade80; font-size: 8px; background: transparent;")
        inner_layout.addWidget(self.lbl_dot)

        self.lbl_task = QLabel("")
        self.lbl_task.setStyleSheet(
            "color: #f2ede4; font-family: 'Sora', 'Segoe UI', sans-serif; "
            "font-size: 11px; background: transparent;"
        )
        inner_layout.addWidget(self.lbl_task)

        self.lbl_elapsed = QLabel("")
        self.lbl_elapsed.setStyleSheet(
            "color: rgba(233,187,81,0.6); font-family: 'JetBrains Mono', monospace; "
            "font-size: 10px; background: transparent;"
        )
        inner_layout.addWidget(self.lbl_elapsed)

        self.btn_interrupt = QPushButton("⚡")
        self.btn_interrupt.setFixedSize(20, 20)
        self.btn_interrupt.setStyleSheet(
            "QPushButton { background: transparent; border: none; font-size: 12px; color: #e9bb51; }"
            "QPushButton:hover { color: #f0c66a; }"
        )
        self.btn_interrupt.hide()
        self.btn_interrupt.clicked.connect(self.interrupt_requested.emit)
        inner_layout.addWidget(self.btn_interrupt)

    def set_state(self, state: str):
        """Set dot state: 'active', 'overdue', 'idle'."""
        self._state = state
        self._apply_dot_color()

    def _apply_dot_color(self):
        color_on, _ = STATE_COLORS.get(self._state, STATE_COLORS["active"])
        self.lbl_dot.setStyleSheet(f"color: {color_on}; font-size: 8px; background: transparent;")

    def _collapsed_inner_size(self):
        return 24, 24

    def _expanded_inner_size(self):
        self._inner.adjustSize()
        return max(self._inner.sizeHint().width() + 20, 120), 28

    def _do_collapse(self):
        self._is_expanded = False
        self.lbl_task.hide()
        self.lbl_elapsed.hide()
        self.btn_interrupt.hide()
        w, h = self._collapsed_inner_size()
        self._inner.setGeometry(HIT_PADDING, HIT_PADDING, w, h)
        self.setFixedSize(w + HIT_PADDING * 2, h + HIT_PADDING * 2)
        self._reposition()
        self.update()

    def _do_expand(self):
        self._is_expanded = True
        self.lbl_task.show()
        self.lbl_elapsed.show()
        if self._active_task and self._state == "active":
            self.btn_interrupt.show()
        w, h = self._expanded_inner_size()
        self._inner.setGeometry(HIT_PADDING, HIT_PADDING, w, h)
        self.setFixedSize(w + HIT_PADDING * 2, h + HIT_PADDING * 2)
        self._reposition()
        self.update()

    def _reposition(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = 8 - HIT_PADDING
        self.move(x, y)

    def _pulse_dot(self):
        if not self.isVisible():
            return
        if self._state == "idle":
            return  # no pulse for idle
        self._dot_state = not self._dot_state
        color_on, color_off = STATE_COLORS.get(self._state, STATE_COLORS["active"])
        color = color_on if self._dot_state else color_off
        self.lbl_dot.setStyleSheet(f"color: {color}; font-size: 8px; background: transparent;")

    def _get_elapsed(self, start_time: str) -> str:
        try:
            now = datetime.now()
            start = datetime.strptime(start_time, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            mins = max(0, int((now - start).total_seconds() // 60))
            return f"{mins}m" if mins < 60 else f"{mins // 60}h {mins % 60}m"
        except Exception:
            return ""

    def _update_elapsed(self):
        if self._active_task and self._is_expanded:
            self.lbl_elapsed.setText(self._get_elapsed(self._active_task["start_time"]))

    def _load_task(self) -> bool:
        self._active_task = database.get_active_entry()
        if not self._active_task:
            return False
        task = self._active_task.get("task", "")
        if " \u2014 " in task:
            task = task.split(" \u2014 ", 1)[1]
        elif " - " in task:
            task = task.split(" - ", 1)[1]
        self.lbl_task.setText(task)
        self.lbl_elapsed.setText(self._get_elapsed(self._active_task["start_time"]))
        return True

    def _silent_refresh(self):
        if not self._load_task():
            self.hide()

    def refresh(self):
        """Called after logging — show expanded for configured duration."""
        if not self._load_task():
            self.hide()
            return
        try:
            duration_ms = int(config.get("STATUS_BAR_DURATION", "10")) * 1000
        except Exception:
            duration_ms = 10_000
        self.set_state("active")
        self.show()
        self._do_expand()
        self._collapse_timer.stop()
        self._collapse_timer.start(duration_ms)

    def set_overdue(self):
        self.set_state("overdue")
        if self._active_task or self._load_task():
            self.show()
            self._do_expand()

    def set_idle(self):
        self.set_state("idle")

    def enterEvent(self, event):
        if self._active_task:
            self._collapse_timer.stop()
            self._load_task()
            self._do_expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._collapse_timer.stop()
        self._collapse_timer.start(1500)
        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        inner_rect = self._inner.geometry()
        path = QPainterPath()
        r = inner_rect.height() // 2
        path.addRoundedRect(inner_rect.x(), inner_rect.y(),
                            inner_rect.width(), inner_rect.height(), r, r)

        if self._state == "overdue":
            bg = QColor(20, 8, 8, 235)
        elif self._state == "idle":
            bg = QColor(14, 14, 14, 180)
        else:
            bg = QColor(8, 9, 9, 235)

        painter.fillPath(path, bg)

        border_color = {
            "active":  QColor(50, 60, 50, 180),
            "overdue": QColor(80, 30, 30, 220),
            "idle":    QColor(40, 40, 40, 150),
        }.get(self._state, QColor(50, 50, 68, 220))

        painter.setPen(QPen(border_color, 1))
        painter.drawPath(path)
        painter.end()
