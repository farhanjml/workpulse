"""
ui/ping_popup.py — 15-minute ping popup
Three clear options: Still on it / End this task / Switch to new task
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core import database
from core.config import load_projects

STYLE = """
QWidget { background: #141418; color: #e8e8f0; font-family: 'JetBrains Mono', monospace; }
QLineEdit { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; padding: 8px 12px; font-size: 12px; color: #e8e8f0; }
QLineEdit:focus { border-color: #7c6af7; }
QComboBox { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; padding: 7px 10px; font-size: 11px; color: #9090a8; }
QComboBox:focus { border-color: #7c6af7; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView { background: #1c1c22; color: #e8e8f0; selection-background-color: #7c6af7; min-width: 300px; }
QPushButton { border-radius: 7px; font-size: 12px; font-weight: 600; padding: 9px; border: none; }
QLabel#header { font-size: 10px; color: #5a5a72; letter-spacing: 2px; }
QLabel#streak { font-size: 11px; color: #fbbf24; }
QLabel#sectionLabel { font-size: 10px; color: #5a5a72; letter-spacing: 1px; }
"""


def _time_options(minutes_back: int = 90) -> list:
    now = datetime.now()
    options = []
    for i in range(0, minutes_back + 1, 15):
        t = now - timedelta(minutes=i)
        label = t.strftime("%H:%M") + (" (now)" if i == 0 else "")
        options.append((t.strftime("%H:%M"), label))
    return options


class PingPopup(QWidget):
    logged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects = load_projects()
        self._setup_window()
        self._setup_ui()

        # Auto-dismiss timer — closes after 60s if user ignores it
        self._auto_dismiss = QTimer()
        self._auto_dismiss.setSingleShot(True)
        self._auto_dismiss.timeout.connect(self._on_auto_dismiss)

        # Countdown label timer
        self._countdown_val = 60
        self._countdown_timer = QTimer()
        self._countdown_timer.timeout.connect(self._tick_countdown)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self.setStyleSheet(STYLE)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("QFrame { background: #141418; border: 1px solid #353545; border-radius: 14px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ── Header ────────────────────────────────────────────────────────────
        header_bar = QWidget()
        header_bar.setStyleSheet("background: #1c1c22; border-radius: 14px 14px 0 0; border-bottom: 1px solid #2a2a38;")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(14, 10, 14, 10)
        lbl_header = QLabel("WORKPULSE · PING")
        lbl_header.setObjectName("header")
        self.lbl_streak = QLabel("🔥 0 entries")
        self.lbl_streak.setObjectName("streak")
        header_layout.addWidget(lbl_header)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_streak)
        card_layout.addWidget(header_bar)

        # ── Body ──────────────────────────────────────────────────────────────
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(8)

        # Current task display
        self.active_frame = QFrame()
        self.active_frame.setStyleSheet("""
            QFrame {
                background: #1c1c22;
                border: 1px solid #2a2a38;
                border-radius: 8px;
                padding: 2px;
            }
        """)
        active_layout = QHBoxLayout(self.active_frame)
        active_layout.setContentsMargins(12, 10, 12, 10)
        self.lbl_dot = QLabel("●")
        self.lbl_dot.setStyleSheet("color: #4ade80; font-size: 8px;")
        self.lbl_active_task = QLabel("")
        self.lbl_active_task.setStyleSheet("color: #e8e8f0; font-size: 12px;")
        self.lbl_active_task.setWordWrap(True)
        active_layout.addWidget(self.lbl_dot)
        active_layout.addWidget(self.lbl_active_task, 1)
        body_layout.addWidget(self.active_frame)

        # ── Option 1: Still on it ─────────────────────────────────────────────
        self.btn_still_on = QPushButton("✓  Still on it — keep going")
        self.btn_still_on.setStyleSheet("""
            QPushButton {
                background: #1a2e1a;
                border: 1px solid #4ade80;
                color: #4ade80;
                border-radius: 8px;
                padding: 10px 14px;
                text-align: left;
                font-size: 12px;
            }
            QPushButton:hover { background: rgba(74,222,128,0.15); }
        """)
        self.btn_still_on.clicked.connect(self._on_still_on)
        body_layout.addWidget(self.btn_still_on)

        # ── Option 2: End this task ───────────────────────────────────────────
        end_row = QHBoxLayout()
        self.btn_end_task = QPushButton("⏹  Done with this task")
        self.btn_end_task.setStyleSheet("""
            QPushButton {
                background: #2a1a1a;
                border: 1px solid #f87171;
                color: #f87171;
                border-radius: 8px;
                padding: 10px 14px;
                text-align: left;
                font-size: 12px;
            }
            QPushButton:hover { background: rgba(248,113,113,0.15); }
        """)
        self.btn_end_task.clicked.connect(self._on_end_task)

        lbl_ended_at = QLabel("ended at:")
        lbl_ended_at.setStyleSheet("color: #5a5a72; font-size: 10px;")
        self.cmb_end_time = QComboBox()
        self.cmb_end_time.setFixedWidth(110)

        end_row.addWidget(self.btn_end_task, 1)
        end_row.addWidget(lbl_ended_at)
        end_row.addWidget(self.cmb_end_time)
        body_layout.addLayout(end_row)

        # ── Option 3: Switch to new task ──────────────────────────────────────
        div = QLabel("OR SWITCHED TO SOMETHING NEW")
        div.setObjectName("sectionLabel")
        body_layout.addWidget(div)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("What are you working on...")
        body_layout.addWidget(self.txt_desc)

        self.cmb_project = QComboBox()
        self.cmb_project.setMinimumWidth(390)
        self.cmb_project.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self.cmb_task = QComboBox()
        self.cmb_task.setMinimumWidth(390)
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        body_layout.addWidget(self.cmb_project)
        body_layout.addWidget(self.cmb_task)

        started_row = QHBoxLayout()
        lbl_started = QLabel("switched at:")
        lbl_started.setObjectName("sectionLabel")
        self.cmb_started = QComboBox()
        self.cmb_started.setFixedWidth(110)
        started_row.addWidget(lbl_started)
        started_row.addStretch()
        started_row.addWidget(self.cmb_started)
        body_layout.addLayout(started_row)

        btn_row = QHBoxLayout()
        self.btn_log = QPushButton("Log New Task")
        self.btn_log.setStyleSheet("""
            QPushButton {
                background: #7c6af7;
                color: white;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover { background: #9d8fff; }
        """)
        self.btn_log.clicked.connect(self._on_log)

        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setFixedWidth(70)
        self.btn_skip.setStyleSheet("""
            QPushButton {
                background: #1c1c22;
                border: 1px solid #2a2a38;
                color: #5a5a72;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton:hover { color: #9090a8; }
        """)
        self.btn_skip.clicked.connect(self.hide)

        btn_row.addWidget(self.btn_log)
        btn_row.addWidget(self.btn_skip)
        body_layout.addLayout(btn_row)

        bottom_row = QHBoxLayout()
        hint = QLabel("Tab · Enter · Esc — keyboard friendly")
        hint.setStyleSheet("font-size: 10px; color: #3a3a52;")
        self.lbl_countdown = QLabel("auto-closing in 60s")
        self.lbl_countdown.setStyleSheet("font-size: 10px; color: #3a3a52;")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignRight)
        bottom_row.addWidget(hint)
        bottom_row.addStretch()
        bottom_row.addWidget(self.lbl_countdown)
        body_layout.addLayout(bottom_row)

        card_layout.addWidget(body)
        outer.addWidget(card)

        self._on_project_changed(0)
        self._populate_times()

    def _populate_times(self):
        options = _time_options()
        self.cmb_end_time.clear()
        self.cmb_started.clear()
        for val, label in options:
            self.cmb_end_time.addItem(label, val)
            self.cmb_started.addItem(label, val)

    def _on_project_changed(self, index):
        if not hasattr(self, 'cmb_task'):
            return
        if index < 0 or index >= len(self.projects):
            return
        self.cmb_task.clear()
        for task in self.projects[index].get("tasks", []):
            self.cmb_task.addItem(task)

    def _refresh_active(self):
        active = database.get_active_entry()
        if active:
            task = active.get("task", "")
            if " \u2014 " in task:
                task = task.split(" \u2014 ", 1)[1]
            elif " - " in task:
                task = task.split(" - ", 1)[1]
            # No truncation — show full task
            self.lbl_active_task.setText(f"{task}  ·  {active['project_name']}")
            self.active_frame.setVisible(True)
            self.btn_still_on.setVisible(True)
            self.btn_end_task.setVisible(True)
            self.cmb_end_time.setVisible(True)
        else:
            self.active_frame.setVisible(False)
            self.btn_still_on.setVisible(False)
            self.btn_end_task.setVisible(False)
            self.cmb_end_time.setVisible(False)

    def _refresh_streak(self):
        self.lbl_streak.setText(f"🔥 {database.count_entries_today()} entries")

    def _on_still_on(self):
        database.extend_active_entry()
        self.logged.emit()
        self.hide()

    def _on_end_task(self):
        end_time = self.cmb_end_time.currentData()
        database.end_current_entry(end_time)
        self.logged.emit()
        self.hide()

    def _on_log(self):
        desc = self.txt_desc.text().strip()
        if not desc:
            self.txt_desc.setFocus()
            self.txt_desc.setStyleSheet(self.txt_desc.styleSheet() + "border-color: #f87171;")
            return
        idx = self.cmb_project.currentIndex()
        if idx < 0 or idx >= len(self.projects):
            return
        project = self.projects[idx]
        task = f"{self.cmb_task.currentText()} \u2014 {desc}"
        database.log_entry(
            project_id=project["id"],
            project_name=project["name"],
            task=task,
            stopped_at=self.cmb_started.currentData()
        )
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def _on_auto_dismiss(self):
        """User ignored the ping — silently continue current task."""
        self._countdown_timer.stop()
        self.hide()

    def _tick_countdown(self):
        self._countdown_val -= 1
        if self._countdown_val > 0:
            self.lbl_countdown.setText(f"auto-closing in {self._countdown_val}s")
        else:
            self.lbl_countdown.setText("closing...")

    def showEvent(self, event):
        self._populate_times()
        self._refresh_active()
        self._refresh_streak()
        self.txt_desc.clear()
        self.txt_desc.setStyleSheet("")
        # Start auto-dismiss countdown
        self._countdown_val = 60
        self.lbl_countdown.setText("auto-closing in 60s")
        self._auto_dismiss.stop()
        self._auto_dismiss.start(60_000)
        self._countdown_timer.stop()
        self._countdown_timer.start(1000)
        super().showEvent(event)
        self._position_top_center()

    def hideEvent(self, event):
        self._auto_dismiss.stop()
        self._countdown_timer.stop()
        super().hideEvent(event)

    def _position_top_center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        self.move(x, 40)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_log()
