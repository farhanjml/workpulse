"""
ui/interrupt_log.py — Quick interrupt log popup.
Logs a short side task without affecting the active task timer.
Triggered via Alt+Shift+L or the status bar ⚡ button.
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication, QButtonGroup
)
from PyQt6.QtCore import Qt, pyqtSignal

from core import database
from core.config import load_projects
from ui.theme import get_colors, base_stylesheet

DURATIONS = [5, 10, 15, 30]  # minutes


class InterruptLogPopup(QWidget):
    logged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects = load_projects()
        self._selected_duration = 10
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(380)

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
            QFrame#runningChip {{
                background: {c['s1']};
                border: 1px solid {c['border']};
                border-radius: 9px;
            }}
            QPushButton#durActive {{
                background: {c['gold_bg']};
                border: 1px solid {c['gold_border']};
                color: {c['gold']};
                font-size: 11px;
                font-weight: 600;
                padding: 6px 0;
                border-radius: 7px;
                min-width: 46px;
            }}
        """)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("header")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(14, 10, 14, 10)
        lbl_dot = QLabel("●")
        lbl_dot.setFixedWidth(10)
        lbl_dot.setObjectName("headerDot")
        lbl_title = QLabel("QUICK INTERRUPT")
        lbl_title.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 3px;")
        lbl_hotkey = QLabel("Alt+Shift+L")
        lbl_hotkey.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        hdr_layout.addWidget(lbl_dot)
        hdr_layout.addWidget(lbl_title)
        hdr_layout.addStretch()
        hdr_layout.addWidget(lbl_hotkey)
        card_layout.addWidget(header)

        # Body
        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 13, 14, 14)
        body_layout.setSpacing(9)

        # Running task chip
        self.running_chip = QFrame()
        self.running_chip.setObjectName("runningChip")
        chip_layout = QHBoxLayout(self.running_chip)
        chip_layout.setContentsMargins(12, 9, 12, 9)
        chip_info = QWidget()
        chip_info_layout = QVBoxLayout(chip_info)
        chip_info_layout.setContentsMargins(0, 0, 0, 0)
        chip_info_layout.setSpacing(1)
        self.lbl_running_task = QLabel("No active task")
        self.lbl_running_task.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.lbl_running_meta = QLabel("")
        self.lbl_running_meta.setStyleSheet("font-size: 10px;")
        chip_info_layout.addWidget(self.lbl_running_task)
        chip_info_layout.addWidget(self.lbl_running_meta)
        self.lbl_still_running = QLabel("● still running")
        self.lbl_still_running.setStyleSheet("font-size: 9px; font-weight: 600; white-space: nowrap;")
        chip_layout.addWidget(chip_info, 1)
        chip_layout.addWidget(self.lbl_still_running)
        body_layout.addWidget(self.running_chip)

        # Description input
        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("Quick task description...")
        body_layout.addWidget(self.txt_desc)

        # Project + task dropdowns
        combo_row = QHBoxLayout()
        self.cmb_project = QComboBox()
        self.cmb_task = QComboBox()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        combo_row.addWidget(self.cmb_project, 3)
        combo_row.addWidget(self.cmb_task, 2)
        body_layout.addLayout(combo_row)

        # Duration quick-picks
        dur_label = QLabel("HOW LONG?")
        dur_label.setStyleSheet("font-size: 8.5px; font-weight: 700; letter-spacing: 2px;")
        body_layout.addWidget(dur_label)

        dur_row = QHBoxLayout()
        dur_row.setSpacing(6)
        self._dur_buttons = []
        for mins in DURATIONS:
            btn = QPushButton(f"{mins}m")
            btn.clicked.connect(lambda checked, m=mins: self._select_duration(m))
            dur_row.addWidget(btn)
            self._dur_buttons.append((mins, btn))
        body_layout.addLayout(dur_row)

        # CTA
        self.btn_log = QPushButton("⚡  Quick Log")
        self.btn_log.setObjectName("btnPrimary")
        self.btn_log.clicked.connect(self._on_log)
        body_layout.addWidget(self.btn_log)

        # Footer
        footer_row = QHBoxLayout()
        hint = QLabel("Enter to log · Esc to cancel")
        hint.setStyleSheet("font-size: 9.5px;")
        lbl_note = QLabel("main task keeps running")
        lbl_note.setStyleSheet("font-size: 9.5px;")
        lbl_note.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer_row.addWidget(hint)
        footer_row.addStretch()
        footer_row.addWidget(lbl_note)
        body_layout.addLayout(footer_row)

        card_layout.addWidget(body)
        outer.addWidget(card)
        self._on_project_changed(0)

    def _on_project_changed(self, index):
        if not hasattr(self, "cmb_task") or index < 0 or index >= len(self.projects):
            return
        self.cmb_task.clear()
        for task in self.projects[index].get("tasks", []):
            self.cmb_task.addItem(task)

    def _select_duration(self, minutes: int):
        self._selected_duration = minutes
        for m, btn in self._dur_buttons:
            if m == minutes:
                btn.setObjectName("durActive")
            else:
                btn.setObjectName("")
        self._apply_theme()

    def _refresh_running(self):
        c = get_colors()
        active = database.get_active_entry()
        if active:
            task = active.get("task", "")
            task_display = task.split(" \u2014 ", 1)[-1] if " \u2014 " in task else task
            self.lbl_running_task.setText(task_display)
            self.lbl_running_meta.setText(
                f"{active.get('project_name', '')}  ·  "
                + self._get_elapsed(active["start_time"])
            )
            self.lbl_still_running.setStyleSheet(
                f"font-size: 9px; font-weight: 600; color: {c['state_active']}; white-space: nowrap;"
            )
            self.lbl_running_meta.setStyleSheet(f"font-size: 10px; color: {c['t3']};")
        else:
            self.lbl_running_task.setText("No active task")
            self.lbl_running_meta.setText("")
            self.lbl_still_running.setStyleSheet(f"font-size: 9px; color: {c['t3']};")

    def _get_elapsed(self, start_time: str) -> str:
        try:
            now = datetime.now()
            start = datetime.strptime(start_time, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )
            mins = max(0, int((now - start).total_seconds() // 60))
            return f"{mins}m" if mins < 60 else f"{mins//60}h {mins%60}m"
        except Exception:
            return ""

    def _on_log(self):
        desc = self.txt_desc.text().strip()
        if not desc:
            self.txt_desc.setFocus()
            return
        idx = self.cmb_project.currentIndex()
        if idx < 0 or idx >= len(self.projects):
            return
        project = self.projects[idx]
        task_type = self.cmb_task.currentText()
        task = f"{task_type} \u2014 {desc}" if task_type else desc
        database.log_interrupt(
            project_id=project["id"],
            project_name=project["name"],
            task=task,
            duration_minutes=self._selected_duration,
        )
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def showEvent(self, event):
        self.projects = load_projects()
        self.cmb_project.clear()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self._on_project_changed(0)
        self._apply_theme()
        self._refresh_running()
        self._select_duration(10)
        self.txt_desc.clear()
        self.txt_desc.setFocus()
        super().showEvent(event)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, 40)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_log()
