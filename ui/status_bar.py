"""
ui/status_bar.py — Floating Dynamic Island style live task indicator
Uses a larger invisible hit zone so hover works reliably on Windows.
"""

from datetime import datetime
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QApplication
from PyQt6.QtCore import Qt, QTimer, QRect
from PyQt6.QtGui import QPainter, QColor, QPainterPath, QPen

from core import database, config

# Invisible padding around the dot to make hover reliable
HIT_PADDING = 20


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._active_task = None
        self._is_expanded = False
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
        # Inner widget that holds actual content, centered in the larger hit area
        self._inner = QWidget(self)
        inner_layout = QHBoxLayout(self._inner)
        inner_layout.setContentsMargins(10, 0, 10, 0)
        inner_layout.setSpacing(6)

        self.lbl_dot = QLabel("●")
        self.lbl_dot.setStyleSheet("color: #4ade80; font-size: 8px; background: transparent;")
        inner_layout.addWidget(self.lbl_dot)

        self.lbl_task = QLabel("")
        self.lbl_task.setStyleSheet(
            "color: #d0d0e0; font-family: 'JetBrains Mono', monospace; "
            "font-size: 11px; background: transparent;"
        )
        inner_layout.addWidget(self.lbl_task)

        self.lbl_elapsed = QLabel("")
        self.lbl_elapsed.setStyleSheet(
            "color: #5a5a72; font-family: 'JetBrains Mono', monospace; "
            "font-size: 10px; background: transparent;"
        )
        inner_layout.addWidget(self.lbl_elapsed)

    def _collapsed_inner_size(self):
        return 24, 24

    def _expanded_inner_size(self):
        self._inner.adjustSize()
        return max(self._inner.sizeHint().width() + 20, 120), 28

    def _do_collapse(self):
        self._is_expanded = False
        self.lbl_task.hide()
        self.lbl_elapsed.hide()
        w, h = self._collapsed_inner_size()
        # Outer widget includes hit padding
        self._inner.setGeometry(HIT_PADDING, HIT_PADDING, w, h)
        self.setFixedSize(w + HIT_PADDING * 2, h + HIT_PADDING * 2)
        self._reposition()
        self.update()

    def _do_expand(self):
        self._is_expanded = True
        self.lbl_task.show()
        self.lbl_elapsed.show()
        w, h = self._expanded_inner_size()
        self._inner.setGeometry(HIT_PADDING, HIT_PADDING, w, h)
        self.setFixedSize(w + HIT_PADDING * 2, h + HIT_PADDING * 2)
        self._reposition()
        self.update()

    def _reposition(self):
        screen = QApplication.primaryScreen().availableGeometry()
        # Center based on inner widget, offset by padding
        x = (screen.width() - self.width()) // 2
        y = 8 - HIT_PADDING  # Visual position stays at y=8
        self.move(x, y)

    def _pulse_dot(self):
        if self.isVisible():
            self._dot_state = not self._dot_state
            color = "#4ade80" if self._dot_state else "#1a4a2a"
            self.lbl_dot.setStyleSheet(
                f"color: {color}; font-size: 8px; background: transparent;"
            )

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
        # No truncation — show full task name
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
            duration_ms = 10000
        self.show()
        self._do_expand()
        self._collapse_timer.stop()
        self._collapse_timer.start(duration_ms)

    def enterEvent(self, event):
        """Expand on hover — check if cursor is over the inner pill area."""
        if self._active_task:
            self._collapse_timer.stop()
            self._load_task()
            self._do_expand()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Start collapse timer when mouse leaves."""
        self._collapse_timer.stop()
        self._collapse_timer.start(1500)
        super().leaveEvent(event)

    def paintEvent(self, event):
        """Only paint the inner pill area, not the invisible hit zone."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw pill only in the inner rect
        inner_rect = self._inner.geometry()
        path = QPainterPath()
        r = inner_rect.height() // 2
        path.addRoundedRect(
            inner_rect.x(), inner_rect.y(),
            inner_rect.width(), inner_rect.height(),
            r, r
        )
        painter.fillPath(path, QColor(14, 14, 18, 235))
        painter.setPen(QPen(QColor(50, 50, 68, 220), 1))
        painter.drawPath(path)
        painter.end()
