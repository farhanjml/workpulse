"""
ui/ping_popup.py — 15-minute ping popup
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QFont, QColor

from core import database, config
from core.config import load_projects

STYLE = """
QWidget { background: #141418; color: #e8e8f0; font-family: 'JetBrains Mono', monospace; }
QLineEdit { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; padding: 8px 12px; font-size: 12px; color: #e8e8f0; }
QLineEdit:focus { border-color: #7c6af7; }
QComboBox { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; padding: 7px 10px; font-size: 11px; color: #9090a8; }
QComboBox:focus { border-color: #7c6af7; }
QComboBox::drop-down { border: none; width: 20px; }
QPushButton { border-radius: 7px; font-size: 12px; font-weight: 600; padding: 9px; border: none; }
QPushButton#btnStillOn { background: #1c1c22; border: 1px solid #353545; color: #e8e8f0; text-align: left; padding: 10px 14px; border-radius: 8px; }
QPushButton#btnStillOn:hover { border-color: #7c6af7; background: rgba(124,106,247,0.08); }
QPushButton#btnLog { background: #7c6af7; color: white; }
QPushButton#btnLog:hover { background: #9d8fff; }
QPushButton#btnSkip { background: #1c1c22; border: 1px solid #2a2a38; color: #5a5a72; }
QPushButton#btnSkip:hover { color: #9090a8; }
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
        self._position_bottom_right()

    def _setup_window(self):
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(310)
        self.setStyleSheet(STYLE)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("QFrame { background: #141418; border: 1px solid #353545; border-radius: 14px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

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

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(10)

        self.btn_still_on = QPushButton()
        self.btn_still_on.setObjectName("btnStillOn")
        self.btn_still_on.clicked.connect(self._on_still_on)
        body_layout.addWidget(self.btn_still_on)

        stopped_row = QHBoxLayout()
        lbl_stopped = QLabel("✗  Stopped at:")
        lbl_stopped.setObjectName("sectionLabel")
        self.cmb_stopped = QComboBox()
        self.cmb_stopped.setFixedWidth(120)
        stopped_row.addWidget(lbl_stopped)
        stopped_row.addStretch()
        stopped_row.addWidget(self.cmb_stopped)
        body_layout.addLayout(stopped_row)

        div_lbl = QLabel("OR SWITCHED TO SOMETHING NEW")
        div_lbl.setObjectName("sectionLabel")
        body_layout.addWidget(div_lbl)

        self.txt_desc = QLineEdit()
        self.txt_desc.setPlaceholderText("What are you working on...")
        body_layout.addWidget(self.txt_desc)

        proj_row = QHBoxLayout()
        self.cmb_project = QComboBox()
        self.cmb_project.currentIndexChanged.connect(self._on_project_changed)
        for p in self.projects:
            self.cmb_project.addItem(p["name"], p["id"])
        self.cmb_task = QComboBox()
        proj_row.addWidget(self.cmb_project, 2)
        proj_row.addWidget(self.cmb_task, 1)
        body_layout.addLayout(proj_row)

        started_row = QHBoxLayout()
        lbl_started = QLabel("Started at:")
        lbl_started.setObjectName("sectionLabel")
        self.cmb_started = QComboBox()
        self.cmb_started.setFixedWidth(120)
        started_row.addWidget(lbl_started)
        started_row.addStretch()
        started_row.addWidget(self.cmb_started)
        body_layout.addLayout(started_row)

        btn_row = QHBoxLayout()
        self.btn_log = QPushButton("Log It")
        self.btn_log.setObjectName("btnLog")
        self.btn_log.clicked.connect(self._on_log)
        self.btn_skip = QPushButton("Skip")
        self.btn_skip.setObjectName("btnSkip")
        self.btn_skip.setFixedWidth(70)
        self.btn_skip.clicked.connect(self.hide)
        btn_row.addWidget(self.btn_log)
        btn_row.addWidget(self.btn_skip)
        body_layout.addLayout(btn_row)

        hint = QLabel("Tab · Enter · Esc — keyboard friendly")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setStyleSheet("font-size: 10px; color: #3a3a52;")
        body_layout.addWidget(hint)

        card_layout.addWidget(body)
        outer.addWidget(card)

        self._populate_times()
        self._on_project_changed(0)
        self._refresh_still_on()
        self._refresh_streak()

    def _populate_times(self):
        options = _time_options()
        self.cmb_stopped.clear()
        self.cmb_started.clear()
        for val, label in options:
            self.cmb_stopped.addItem(label, val)
            self.cmb_started.addItem(label, val)

    def _on_project_changed(self, index):
        if index < 0 or index >= len(self.projects):
            return
        self.cmb_task.clear()
        for task in self.projects[index].get("tasks", []):
            self.cmb_task.addItem(task)

    def _refresh_still_on(self):
        active = database.get_active_entry()
        if active:
            self.btn_still_on.setText(f"✓  Still on this?\n   {active['task']}  ·  {active['project_name']}")
            self.btn_still_on.setVisible(True)
        else:
            self.btn_still_on.setVisible(False)

    def _refresh_streak(self):
        self.lbl_streak.setText(f"🔥 {database.count_entries_today()} entries")

    def _on_still_on(self):
        database.extend_active_entry()
        self.hide()
        self.logged.emit()

    def _on_log(self):
        desc = self.txt_desc.text().strip()
        if not desc:
            self.txt_desc.setFocus()
            self.txt_desc.setStyleSheet(self.txt_desc.styleSheet() + "border-color: #f87171;")
            return
        project = self.projects[self.cmb_project.currentIndex()]
        task = f"{self.cmb_task.currentText()} — {desc}"
        database.log_entry(project_id=project["id"], project_name=project["name"], task=task, stopped_at=self.cmb_stopped.currentData())
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def showEvent(self, event):
        self._populate_times()
        self._refresh_still_on()
        self._refresh_streak()
        self.txt_desc.clear()
        self.txt_desc.setStyleSheet("")
        super().showEvent(event)
        self._animate_in()

    def _animate_in(self):
        screen = QApplication.primaryScreen().availableGeometry()
        end_rect = QRect(screen.width() - self.width() - 16, screen.height() - self.height() - 16, self.width(), self.height())
        start_rect = QRect(end_rect.x(), end_rect.y() + 30, end_rect.width(), end_rect.height())
        self.setGeometry(start_rect)
        anim = QPropertyAnimation(self, b"geometry")
        anim.setDuration(200)
        anim.setStartValue(start_rect)
        anim.setEndValue(end_rect)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start()
        self._anim = anim

    def _position_bottom_right(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - self.width() - 16, screen.height() - self.height() - 16)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._on_log()
