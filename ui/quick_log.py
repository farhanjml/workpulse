"""
ui/quick_log.py — Hotkey-triggered quick log popup
Shows current running task with End Task option.
No favourites section.
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect

from core import database
from core.config import load_projects
from ui.theme import get_colors, base_stylesheet


def _time_options(minutes_back: int = 90) -> list:
    now = datetime.now()
    options = []
    for i in range(0, minutes_back + 1, 15):
        t = now - timedelta(minutes=i)
        label = t.strftime("%H:%M") + (" (now)" if i == 0 else "")
        options.append((t.strftime("%H:%M"), label))
    return options


class QuickLogPopup(QWidget):
    logged = pyqtSignal()
    task_ended = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects = load_projects()
        self._setup_window()
        self._setup_ui()

    def _apply_theme(self):
        c = get_colors()
        self.setStyleSheet(base_stylesheet(c) + f"""
            QFrame#card {{
                background: {c['s0']};
                border: 1px solid {c['border']};
                border-radius: 14px;
            }}
            QWidget#header {{
                background: {c['s1']};
                border-radius: 14px 14px 0 0;
                border-bottom: 1px solid {c['border']};
            }}
            QFrame#activeFrame {{
                background: {c['s1']};
                border: 1px solid {c['border']};
                border-radius: 8px;
            }}
            QPushButton#btnEndTask {{
                background: {c['red_bg']};
                border: 1px solid {c['red_border']};
                color: {c['red']};
                text-align: left;
            }}
            QPushButton#btnEndTask:hover {{ background: rgba(252,165,165,0.13); }}
        """)

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(420)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        # Header
        header_bar = QWidget()
        header_bar.setObjectName("header")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(14, 10, 14, 10)
        lbl_header = QLabel("WORKPULSE · QUICK LOG")
        lbl_header.setObjectName("header")
        lbl_hotkey = QLabel("Alt+L")
        lbl_hotkey.setStyleSheet("font-size: 10px; color: #3a3a52;")
        header_layout.addWidget(lbl_header)
        header_layout.addStretch()
        header_layout.addWidget(lbl_hotkey)
        card_layout.addWidget(header_bar)

        # Body
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(8)

        # Current running task section
        self.active_section = QWidget()
        active_layout = QVBoxLayout(self.active_section)
        active_layout.setContentsMargins(0, 0, 0, 0)
        active_layout.setSpacing(6)

        lbl_active = QLabel("NOW RUNNING")
        lbl_active.setObjectName("activeLabel")
        active_layout.addWidget(lbl_active)

        self.active_frame = QFrame()
        self.active_frame.setObjectName("activeFrame")
        active_frame_layout = QHBoxLayout(self.active_frame)
        active_frame_layout.setContentsMargins(12, 8, 12, 8)

        self.lbl_active_dot = QLabel("●")
        self.lbl_active_dot.setStyleSheet("color: #4ade80; font-size: 8px;")
        active_frame_layout.addWidget(self.lbl_active_dot)

        self.lbl_active_task = QLabel("")
        self.lbl_active_task.setStyleSheet("color: #e8e8f0; font-size: 11px;")
        self.lbl_active_task.setWordWrap(True)
        active_frame_layout.addWidget(self.lbl_active_task, 1)

        self.lbl_active_elapsed = QLabel("")
        self.lbl_active_elapsed.setStyleSheet("color: #5a5a72; font-size: 10px;")
        active_frame_layout.addWidget(self.lbl_active_elapsed)

        active_layout.addWidget(self.active_frame)

        self.btn_end_task = QPushButton("⏹  End Current Task")
        self.btn_end_task.setObjectName("btnEndTask")
        self.btn_end_task.clicked.connect(self._on_end_task)
        active_layout.addWidget(self.btn_end_task)

        body_layout.addWidget(self.active_section)

        # Divider
        self.div_lbl = QLabel("LOG NEW TASK")
        self.div_lbl.setObjectName("sectionLabel")
        body_layout.addWidget(self.div_lbl)

        # Description input
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("What are you working on...")
        body_layout.addWidget(self.txt_desc)

        # Project dropdown
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

        # Started at
        started_row = QHBoxLayout()
        lbl = QLabel("Started at:")
        lbl.setObjectName("sectionLabel")
        self.cmb_started = QComboBox()
        self.cmb_started.setFixedWidth(130)
        started_row.addWidget(lbl)
        started_row.addStretch()
        started_row.addWidget(self.cmb_started)
        body_layout.addLayout(started_row)

        # Buttons
        btn_row = QHBoxLayout()
        self.btn_log = QPushButton("Log It")
        self.btn_log.setObjectName("btnLog")
        self.btn_log.clicked.connect(self._on_log)
        self.btn_cancel = QPushButton("Esc")
        self.btn_cancel.setObjectName("btnCancel")
        self.btn_cancel.setFixedWidth(60)
        self.btn_cancel.clicked.connect(self.hide)
        btn_row.addWidget(self.btn_log)
        btn_row.addWidget(self.btn_cancel)
        body_layout.addLayout(btn_row)

        card_layout.addWidget(body)
        outer.addWidget(card)

        self._on_project_changed(0)
        self._populate_times()

    def _populate_times(self):
        options = _time_options()
        self.cmb_started.clear()
        for val, label in options:
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
        """Refresh the currently running task display."""
        active = database.get_active_entry()
        if active:
            task = active.get("task", "")
            if " \u2014 " in task:
                task = task.split(" \u2014 ", 1)[1]
            elif " - " in task:
                task = task.split(" - ", 1)[1]
            if len(task) > 45:
                task = task[:45] + "..."

            # Elapsed
            try:
                now = datetime.now()
                start = datetime.strptime(active["start_time"], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                mins = max(0, int((now - start).total_seconds() // 60))
                elapsed = f"{mins}m" if mins < 60 else f"{mins//60}h {mins%60}m"
            except Exception:
                elapsed = ""

            self.lbl_active_task.setText(task)
            self.lbl_active_elapsed.setText(elapsed)
            self.active_section.show()
        else:
            self.active_section.hide()

    def _on_end_task(self):
        now = datetime.now().strftime("%H:%M")
        database.end_current_entry(now)
        self.task_ended.emit()
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
        task_type = self.cmb_task.currentText()
        task = f"{task_type} \u2014 {desc}" if task_type else desc
        database.log_entry(
            project_id=project["id"],
            project_name=project["name"],
            task=task,
            stopped_at=self.cmb_started.currentData()
        )
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def showEvent(self, event):
        self._apply_theme()
        self._populate_times()
        self._refresh_active()
        self.txt_desc.clear()
        self.txt_desc.setStyleSheet("")
        self.txt_desc.setFocus()
        super().showEvent(event)
        self._position_top_center()

    def _position_top_center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = 50
        self.move(x, y)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_log()
