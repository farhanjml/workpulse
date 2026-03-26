"""
ui/quick_log.py — Hotkey-triggered quick log popup
"""

from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect

from core import database
from core.config import load_projects

STYLE = """
QWidget { background: #141418; color: #e8e8f0; font-family: 'JetBrains Mono', monospace; }
QLineEdit { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; padding: 8px 12px; font-size: 12px; color: #e8e8f0; }
QLineEdit:focus { border-color: #7c6af7; }
QComboBox { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; padding: 7px 10px; font-size: 11px; color: #9090a8; }
QComboBox:focus { border-color: #7c6af7; }
QComboBox::drop-down { border: none; width: 20px; }
QPushButton { border-radius: 7px; font-size: 12px; font-weight: 600; padding: 9px; border: none; }
QPushButton#btnLog { background: #7c6af7; color: white; }
QPushButton#btnLog:hover { background: #9d8fff; }
QPushButton#btnCancel { background: #1c1c22; border: 1px solid #2a2a38; color: #5a5a72; }
QPushButton#btnCancel:hover { color: #9090a8; }
QLabel#header { font-size: 10px; color: #5a5a72; letter-spacing: 2px; }
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


class QuickLogPopup(QWidget):
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
        self.setFixedWidth(300)
        self.setStyleSheet(STYLE)

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setStyleSheet("QFrame { background: #141418; border: 1px solid #353545; border-radius: 14px; }")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)

        header_bar = QWidget()
        header_bar.setStyleSheet("background: #1c1c22; border-radius: 14px 14px 0 0; border-bottom: 1px solid #2a2a38;")
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

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(14, 14, 14, 14)
        body_layout.setSpacing(8)

        self._build_favourites(body_layout)

        div = QLabel("OR TYPE A NEW TASK")
        div.setObjectName("sectionLabel")
        body_layout.addWidget(div)

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
        lbl = QLabel("Started at:")
        lbl.setObjectName("sectionLabel")
        self.cmb_started = QComboBox()
        self.cmb_started.setFixedWidth(120)
        started_row.addWidget(lbl)
        started_row.addStretch()
        started_row.addWidget(self.cmb_started)
        body_layout.addLayout(started_row)

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

    def _build_favourites(self, layout):
        favs = database.get_top_tasks(limit=3)
        if not favs:
            return
        lbl = QLabel("⭐  FAVOURITES")
        lbl.setObjectName("sectionLabel")
        layout.addWidget(lbl)
        for fav in favs:
            btn = QPushButton(fav["task"])
            btn.setStyleSheet("""
                QPushButton { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; color: #9090a8; text-align: left; padding: 7px 10px; font-size: 11px; }
                QPushButton:hover { border-color: #7c6af7; color: #e8e8f0; background: rgba(124,106,247,0.08); }
            """)
            btn.clicked.connect(lambda _, f=fav: self._log_favourite(f))
            layout.addWidget(btn)
        layout.addSpacing(4)

    def _log_favourite(self, fav: dict):
        database.log_entry(project_id=fav["project_id"], project_name=fav["project_name"], task=fav["task"], stopped_at=datetime.now().strftime("%H:%M"))
        self.logged.emit()
        self.hide()

    def _populate_times(self):
        options = _time_options()
        self.cmb_started.clear()
        for val, label in options:
            self.cmb_started.addItem(label, val)

    def _on_project_changed(self, index):
        if index < 0 or index >= len(self.projects):
            return
        self.cmb_task.clear()
        for task in self.projects[index].get("tasks", []):
            self.cmb_task.addItem(task)

    def _on_log(self):
        desc = self.txt_desc.text().strip()
        if not desc:
            self.txt_desc.setFocus()
            self.txt_desc.setStyleSheet(self.txt_desc.styleSheet() + "border-color: #f87171;")
            return
        project = self.projects[self.cmb_project.currentIndex()]
        task = f"{self.cmb_task.currentText()} — {desc}"
        database.log_entry(project_id=project["id"], project_name=project["name"], task=task, stopped_at=self.cmb_started.currentData())
        self.logged.emit()
        self.txt_desc.clear()
        self.hide()

    def showEvent(self, event):
        self._populate_times()
        self.txt_desc.clear()
        self.txt_desc.setStyleSheet("")
        self.txt_desc.setFocus()
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
