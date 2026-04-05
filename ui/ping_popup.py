"""
ui/ping_popup.py — 15-minute ping popup.
Shows 'Good morning' variant when no task is active.
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from core import database, config
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


class PingPopup(QWidget):
    logged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.projects = load_projects()
        self._setup_window()
        self._setup_ui()
        self._auto_dismiss = QTimer()
        self._auto_dismiss.setSingleShot(True)
        self._auto_dismiss.timeout.connect(self._on_auto_dismiss)
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
        self.setFixedWidth(400)

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
            QFrame#activeChip {{
                background: {c['s1']};
                border: 1px solid {c['border']};
                border-radius: 9px;
            }}
            QPushButton#btnStillOn {{
                background: {c['green_bg']};
                border: 1px solid {c['green_border']};
                color: {c['green']};
                text-align: left;
                padding: 10px 13px;
            }}
            QPushButton#btnStillOn:hover {{ background: rgba(74,222,128,0.13); }}
            QPushButton#btnEndTask {{
                background: {c['red_bg']};
                border: 1px solid {c['red_border']};
                color: {c['red']};
                text-align: left;
                padding: 10px 13px;
            }}
            QPushButton#btnEndTask:hover {{ background: rgba(252,165,165,0.13); }}
        """)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QFrame()
        self.card.setObjectName("card")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("header")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(14, 10, 14, 10)
        self.lbl_dot = QLabel("●")
        self.lbl_dot.setFixedWidth(10)
        self.lbl_header = QLabel("WORKPULSE · PING")
        self.lbl_header.setStyleSheet("font-size: 10px; font-weight: 600; letter-spacing: 3px;")
        self.lbl_streak = QLabel("🔥 0 entries")
        self.lbl_streak.setStyleSheet("font-size: 10px; font-weight: 600;")
        hdr_layout.addWidget(self.lbl_dot)
        hdr_layout.addWidget(self.lbl_header)
        hdr_layout.addStretch()
        hdr_layout.addWidget(self.lbl_streak)
        card_layout.addWidget(header)

        # Body
        body = QWidget()
        self.body_layout = QVBoxLayout(body)
        self.body_layout.setContentsMargins(14, 14, 14, 16)
        self.body_layout.setSpacing(9)

        # ── Active-task section (hidden when no active task) ──────────────────
        self.active_section = QWidget()
        act_layout = QVBoxLayout(self.active_section)
        act_layout.setContentsMargins(0, 0, 0, 0)
        act_layout.setSpacing(7)

        self.active_chip = QFrame()
        self.active_chip.setObjectName("activeChip")
        chip_row = QHBoxLayout(self.active_chip)
        chip_row.setContentsMargins(12, 10, 12, 10)
        self.lbl_chip_dot = QLabel("●")
        self.lbl_chip_dot.setFixedWidth(10)
        self.lbl_chip_info = QWidget()
        chip_info_layout = QVBoxLayout(self.lbl_chip_info)
        chip_info_layout.setContentsMargins(0, 0, 0, 0)
        chip_info_layout.setSpacing(1)
        self.lbl_task_name = QLabel()
        self.lbl_task_name.setStyleSheet("font-size: 12px; font-weight: 500;")
        self.lbl_task_meta = QLabel()
        self.lbl_task_meta.setStyleSheet("font-size: 10px;")
        chip_info_layout.addWidget(self.lbl_task_name)
        chip_info_layout.addWidget(self.lbl_task_meta)
        self.lbl_elapsed = QLabel()
        self.lbl_elapsed.setStyleSheet("font-size: 10px; font-family: 'JetBrains Mono', monospace;")
        chip_row.addWidget(self.lbl_chip_dot)
        chip_row.addWidget(self.lbl_chip_info, 1)
        chip_row.addWidget(self.lbl_elapsed)
        act_layout.addWidget(self.active_chip)

        self.btn_still_on = QPushButton("✓  Still on it — keep going")
        self.btn_still_on.setObjectName("btnStillOn")
        self.btn_still_on.clicked.connect(self._on_still_on)
        act_layout.addWidget(self.btn_still_on)

        end_row_widget = QWidget()
        end_row = QHBoxLayout(end_row_widget)
        end_row.setContentsMargins(0, 0, 0, 0)
        end_row.setSpacing(8)
        self.btn_end_task = QPushButton("⏹  Done with this task")
        self.btn_end_task.setObjectName("btnEndTask")
        self.btn_end_task.clicked.connect(self._on_end_task)
        lbl_ended = QLabel("ended at")
        lbl_ended.setStyleSheet("font-size: 10px;")
        self.cmb_end_time = QComboBox()
        self.cmb_end_time.setFixedWidth(110)
        end_row.addWidget(self.btn_end_task, 1)
        end_row.addWidget(lbl_ended)
        end_row.addWidget(self.cmb_end_time)
        act_layout.addWidget(end_row_widget)
        self.body_layout.addWidget(self.active_section)

        # ── First-ping hero (shown when no active task) ───────────────────────
        self.first_ping_section = QWidget()
        fp_layout = QVBoxLayout(self.first_ping_section)
        fp_layout.setContentsMargins(0, 4, 0, 4)
        fp_layout.setSpacing(2)
        self.lbl_gm_eyebrow = QLabel()
        self.lbl_gm_eyebrow.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gm_title = QLabel("What are you starting with?")
        self.lbl_gm_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gm_title.setStyleSheet("font-size: 16px; font-weight: 600;")
        self.lbl_gm_sub = QLabel("Log your first task to kick off the day")
        self.lbl_gm_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_gm_sub.setStyleSheet("font-size: 11px;")
        fp_layout.addWidget(self.lbl_gm_eyebrow)
        fp_layout.addWidget(self.lbl_gm_title)
        fp_layout.addWidget(self.lbl_gm_sub)
        self.body_layout.addWidget(self.first_ping_section)

        # ── New-task form (always shown) ──────────────────────────────────────
        self.divider_lbl = QLabel("OR SWITCHED TO SOMETHING NEW")
        self.divider_lbl.setStyleSheet("font-size: 8.5px; font-weight: 600; letter-spacing: 2px;")
        self.body_layout.addWidget(self.divider_lbl)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("What are you working on...")
        self.body_layout.addWidget(self.txt_desc)

        self.cmb_project = QComboBox()
        self.cmb_task = QComboBox()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        self.body_layout.addWidget(self.cmb_project)
        self.body_layout.addWidget(self.cmb_task)

        switched_row = QHBoxLayout()
        self.lbl_switched = QLabel("switched at")
        self.lbl_switched.setStyleSheet("font-size: 10px;")
        self.cmb_started = QComboBox()
        self.cmb_started.setFixedWidth(110)
        switched_row.addWidget(self.lbl_switched)
        switched_row.addStretch()
        switched_row.addWidget(self.cmb_started)
        self.body_layout.addLayout(switched_row)

        btn_row = QHBoxLayout()
        self.btn_log = QPushButton("Log New Task")
        self.btn_log.setObjectName("btnPrimary")
        self.btn_log.clicked.connect(self._on_log)
        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setObjectName("btnGhost")
        self.btn_skip.setFixedWidth(70)
        self.btn_skip.clicked.connect(self.hide)
        btn_row.addWidget(self.btn_log)
        btn_row.addWidget(self.btn_skip)
        self.body_layout.addLayout(btn_row)

        footer_row = QHBoxLayout()
        hint = QLabel("Tab · Enter · Esc")
        hint.setStyleSheet("font-size: 9.5px;")
        self.lbl_countdown = QLabel("auto-closing in 60s")
        self.lbl_countdown.setStyleSheet("font-size: 9.5px;")
        self.lbl_countdown.setAlignment(Qt.AlignmentFlag.AlignRight)
        footer_row.addWidget(hint)
        footer_row.addStretch()
        footer_row.addWidget(self.lbl_countdown)
        self.body_layout.addLayout(footer_row)

        card_layout.addWidget(body)
        outer.addWidget(self.card)
        self._on_project_changed(0)

    def _populate_times(self):
        options = _time_options()
        self.cmb_end_time.clear()
        self.cmb_started.clear()
        for val, label in options:
            self.cmb_end_time.addItem(label, val)
            self.cmb_started.addItem(label, val)

    def _on_project_changed(self, index):
        if not hasattr(self, "cmb_task") or index < 0 or index >= len(self.projects):
            return
        self.cmb_task.clear()
        for task in self.projects[index].get("tasks", []):
            self.cmb_task.addItem(task)

    def _refresh_active(self):
        c = get_colors()
        active = database.get_active_entry()

        if active:
            self.active_section.setVisible(True)
            self.first_ping_section.setVisible(False)
            self.divider_lbl.setVisible(True)
            self.btn_log.setText("Log New Task")
            self.lbl_switched.setText("switched at")
            self.btn_skip.setVisible(True)

            task = active.get("task", "")
            task_display = task.split(" \u2014 ", 1)[-1] if " \u2014 " in task else task
            project_name = active.get("project_name", "")
            self.lbl_task_name.setText(task_display)
            self.lbl_task_meta.setText(project_name)

            try:
                now = datetime.now()
                start = datetime.strptime(active["start_time"], "%H:%M").replace(
                    year=now.year, month=now.month, day=now.day
                )
                mins = max(0, int((now - start).total_seconds() // 60))
                elapsed = f"{mins}m" if mins < 60 else f"{mins//60}h {mins%60}m"
            except Exception:
                elapsed = ""
            self.lbl_elapsed.setText(elapsed)
            self.lbl_elapsed.setStyleSheet(
                f"font-size: 10px; font-family: 'JetBrains Mono', monospace; color: {c['gold_dim']};"
            )
            self.lbl_chip_dot.setStyleSheet(f"color: {c['state_active']}; font-size: 8px;")
            self.lbl_task_meta.setStyleSheet(f"font-size: 10px; color: {c['t3']};")

        else:
            self.active_section.setVisible(False)
            self.first_ping_section.setVisible(True)
            self.divider_lbl.setVisible(False)
            self.btn_log.setText("Start Tracking")
            self.lbl_switched.setText("started at")
            self.btn_skip.setVisible(True)

            name = config.get("USER_NAME", "Farhan").split()[0]
            self.lbl_gm_eyebrow.setText(f"Good morning, {name}")
            self.lbl_gm_eyebrow.setStyleSheet(
                f"font-size: 10px; font-weight: 600; letter-spacing: 2px; color: {c['gold_dim']};"
            )
            self.lbl_streak.setText("✦ Day start")

        self.lbl_dot.setStyleSheet(f"color: {c['state_active']}; font-size: 8px; background: transparent;")

    def _refresh_streak(self):
        count = database.count_entries_today()
        self.lbl_streak.setText(f"🔥 {count} entries")

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
            stopped_at=self.cmb_started.currentData(),
        )
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def _on_auto_dismiss(self):
        self._countdown_timer.stop()
        self.hide()

    def _tick_countdown(self):
        self._countdown_val -= 1
        if self._countdown_val > 0:
            self.lbl_countdown.setText(f"auto-closing in {self._countdown_val}s")
        else:
            self.lbl_countdown.setText("closing...")

    def showEvent(self, event):
        self.projects = load_projects()
        self.cmb_project.clear()
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self._on_project_changed(0)
        self._populate_times()
        self._apply_theme()
        self._refresh_active()
        active = database.get_active_entry()
        if active:
            self._refresh_streak()
        self.txt_desc.clear()
        self._countdown_val = 60
        self.lbl_countdown.setText("auto-closing in 60s")
        self._auto_dismiss.stop()
        self._auto_dismiss.start(60_000)
        self._countdown_timer.stop()
        self._countdown_timer.start(1_000)
        super().showEvent(event)
        self._position_top_center()

    def hideEvent(self, event):
        self._auto_dismiss.stop()
        self._countdown_timer.stop()
        super().hideEvent(event)

    def _position_top_center(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move((screen.width() - self.width()) // 2, 40)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_log()
