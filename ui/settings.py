"""
ui/settings.py — Settings window
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QComboBox, QLineEdit,
    QFrame, QTimeEdit, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence

from core import config

STYLE = """
QWidget { background: #0d0d0f; color: #e8e8f0; font-family: 'JetBrains Mono', monospace; font-size: 12px; }
QLineEdit, QComboBox, QTimeEdit { background: #1c1c22; border: 1px solid #2a2a38; border-radius: 7px; padding: 6px 10px; color: #9d8fff; }
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus { border-color: #7c6af7; }
QComboBox::drop-down { border: none; width: 20px; }
QSlider::groove:horizontal { height: 4px; background: #2a2a38; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; height: 14px; background: #7c6af7; border-radius: 7px; margin: -5px 0; }
QSlider::sub-page:horizontal { background: #7c6af7; border-radius: 2px; }
QPushButton { border-radius: 7px; padding: 9px 18px; border: 1px solid #2a2a38; background: #1c1c22; color: #9090a8; }
QPushButton:hover { color: #e8e8f0; }
QPushButton#btnSave { background: #7c6af7; border-color: #7c6af7; color: white; }
QPushButton#btnSave:hover { background: #9d8fff; }
"""


class Toggle(QCheckBox):
    def __init__(self, checked=False):
        super().__init__()
        self.setChecked(checked)
        self.setStyleSheet("""
            QCheckBox::indicator { width: 36px; height: 20px; border-radius: 10px; background: #2a2a38; border: 1px solid #353545; }
            QCheckBox::indicator:checked { background: #7c6af7; border-color: #7c6af7; }
        """)


class SettingRow(QWidget):
    def __init__(self, label: str, control: QWidget):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #9090a8;")
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(control)
        self.setStyleSheet("QWidget { background: #1c1c22; border-radius: 8px; } QWidget:hover { background: #242430; }")


class SliderWithValue(QWidget):
    def __init__(self, min_val, max_val, value, suffix=""):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(min_val, max_val)
        self.slider.setValue(value)
        self.slider.setFixedWidth(100)
        self.lbl = QLabel(f"{value}{suffix}")
        self.lbl.setFixedWidth(36)
        self.lbl.setStyleSheet("color: #9d8fff;")
        self.slider.valueChanged.connect(lambda v: self.lbl.setText(f"{v}{suffix}"))
        layout.addWidget(self.slider)
        layout.addWidget(self.lbl)

    def value(self):
        return self.slider.value()


class HotkeyCapture(QPushButton):
    hotkey_captured = pyqtSignal(str)

    def __init__(self, current: str):
        super().__init__(current.upper().replace("+", " + "))
        self._current = current
        self._recording = False
        self.setFixedWidth(160)
        self.clicked.connect(self._start_recording)

    def _start_recording(self):
        self._recording = True
        self.setText("Press keys...")
        self.setStyleSheet("color: #9d8fff; border-color: #7c6af7;")

    def keyPressEvent(self, event):
        if not self._recording:
            return super().keyPressEvent(event)
        parts = []
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier: parts.append("ctrl")
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier: parts.append("shift")
        if event.modifiers() & Qt.KeyboardModifier.AltModifier: parts.append("alt")
        if event.modifiers() & Qt.KeyboardModifier.MetaModifier: parts.append("win")
        key = event.key()
        if key not in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            key_str = event.text().upper() or QKeySequence(key).toString()
            if key_str:
                parts.append(key_str.lower())
        if len(parts) >= 2:
            combo = "+".join(parts)
            self._current = combo
            self.setText(combo.upper().replace("+", " + "))
            self.setStyleSheet("")
            self._recording = False
            self.hotkey_captured.emit(combo)

    def get_hotkey(self) -> str:
        return self._current


class SettingsWindow(QWidget):
    settings_saved = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = config.load_config()
        self._setup_window()
        self._setup_ui()

    def _setup_window(self):
        self.setWindowTitle("WorkPulse — Settings")
        self.setFixedWidth(440)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(Qt.WindowType.Window)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setStyleSheet("background: #1c1c22; border-bottom: 1px solid #2a2a38;")
        header.setFixedHeight(52)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel("⚙  Settings")
        lbl.setStyleSheet("font-size: 14px; font-weight: 600; color: #e8e8f0;")
        h_layout.addWidget(lbl)
        layout.addWidget(header)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; } QScrollBar:vertical { background: #1c1c22; width: 6px; border-radius: 3px; } QScrollBar::handle:vertical { background: #353545; border-radius: 3px; }")

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setSpacing(16)

        body_layout.addWidget(self._section_label("TIMING"))
        ping_val = int(self._cfg.get("PING_INTERVAL", 15))
        self.sld_ping = SliderWithValue(1, 15, max(1, ping_val), "m")
        self.sld_idle = SliderWithValue(5, 30, int(self._cfg.get("IDLE_THRESHOLD", 10)), "m")
        self.sld_overdue = SliderWithValue(20, 90, int(self._cfg.get("OVERDUE_WARNING", 45)), "m")
        t_start = self._cfg.get("WORK_START", "09:00").split(":")
        self.time_start = QTimeEdit(QTime(int(t_start[0]), int(t_start[1])))
        self.time_start.setFixedWidth(80)
        t_end = self._cfg.get("END_OF_DAY", "18:00").split(":")
        self.time_eod = QTimeEdit(QTime(int(t_end[0]), int(t_end[1])))
        self.time_eod.setFixedWidth(80)
        dur_val = int(self._cfg.get("STATUS_BAR_DURATION", 10))
        self.sld_status_dur = SliderWithValue(3, 30, dur_val, "s")
        body_layout.addWidget(SettingRow("Ping interval", self.sld_ping))
        body_layout.addWidget(SettingRow("Idle threshold", self.sld_idle))
        body_layout.addWidget(SettingRow("Overdue warning", self.sld_overdue))
        body_layout.addWidget(SettingRow("Status bar duration", self.sld_status_dur))
        body_layout.addWidget(SettingRow("Work start time", self.time_start))
        body_layout.addWidget(SettingRow("End of day alert", self.time_eod))

        body_layout.addWidget(self._section_label("HOTKEY"))
        self.hotkey_btn = HotkeyCapture(self._cfg.get("HOTKEY", "alt+l"))
        body_layout.addWidget(SettingRow("Quick log", self.hotkey_btn))
        hint = QLabel("Click the button then press your desired combo")
        hint.setStyleSheet("color: #3a3a52; font-size: 10px; padding: 0 12px;")
        body_layout.addWidget(hint)

        body_layout.addWidget(self._section_label("BEHAVIOUR"))
        self.tog_boot = Toggle(self._cfg.get("START_ON_BOOT", "true") == "true")
        self.tog_dark = Toggle(self._cfg.get("DARK_MODE", "true") == "true")
        self.tog_window = Toggle(self._cfg.get("WINDOW_TRACKING", "false") == "true")
        self.tog_clipboard = Toggle(self._cfg.get("CLIPBOARD_HINTS", "true") == "true")
        body_layout.addWidget(SettingRow("Start on boot", self.tog_boot))
        body_layout.addWidget(SettingRow("Dark mode", self.tog_dark))
        body_layout.addWidget(SettingRow("Window tracking", self.tog_window))
        body_layout.addWidget(SettingRow("Clipboard hints", self.tog_clipboard))

        body_layout.addWidget(self._section_label("SOUND"))
        self.cmb_sound = QComboBox()
        self.cmb_sound.setFixedWidth(140)
        for theme in ["Soft chime", "Typewriter ding", "Retro beep", "None"]:
            self.cmb_sound.addItem(theme)
        theme_map = {"soft_chime": 0, "typewriter": 1, "retro": 2, "none": 3}
        self.cmb_sound.setCurrentIndex(theme_map.get(self._cfg.get("SOUND_THEME", "soft_chime"), 0))
        self.sld_volume = SliderWithValue(0, 100, int(self._cfg.get("VOLUME", 60)), "%")
        body_layout.addWidget(SettingRow("Sound theme", self.cmb_sound))
        body_layout.addWidget(SettingRow("Volume", self.sld_volume))

        body_layout.addWidget(self._section_label("CLOCKIFY"))
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("Paste API key here...")
        self.txt_api_key.setFixedWidth(200)
        body_layout.addWidget(SettingRow("API Key", self.txt_api_key))

        body_layout.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        footer = QWidget()
        footer.setStyleSheet("background: #1c1c22; border-top: 1px solid #2a2a38;")
        footer.setFixedHeight(52)
        ft_layout = QHBoxLayout(footer)
        ft_layout.setContentsMargins(16, 0, 16, 0)
        ft_layout.setSpacing(8)
        self.btn_save = QPushButton("Save")
        self.btn_save.setObjectName("btnSave")
        self.btn_save.clicked.connect(self._save)
        btn_cancel = QPushButton("Close")
        btn_cancel.clicked.connect(self.hide)
        ft_layout.addStretch()
        ft_layout.addWidget(btn_cancel)
        ft_layout.addWidget(self.btn_save)
        layout.addWidget(footer)

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #3a3a52; font-size: 10px; letter-spacing: 2px; padding: 0 4px;")
        return lbl

    def _save(self):
        theme_map = {0: "soft_chime", 1: "typewriter", 2: "retro", 3: "none"}
        updates = {
            "PING_INTERVAL": str(self.sld_ping.value()),
            "IDLE_THRESHOLD": str(self.sld_idle.value()),
            "OVERDUE_WARNING": str(self.sld_overdue.value()),
            "WORK_START": self.time_start.time().toString("HH:mm"),
            "END_OF_DAY": self.time_eod.time().toString("HH:mm"),
            "HOTKEY": self.hotkey_btn.get_hotkey(),
            "START_ON_BOOT": "true" if self.tog_boot.isChecked() else "false",
            "DARK_MODE": "true" if self.tog_dark.isChecked() else "false",
            "WINDOW_TRACKING": "true" if self.tog_window.isChecked() else "false",
            "CLIPBOARD_HINTS": "true" if self.tog_clipboard.isChecked() else "false",
            "SOUND_THEME": theme_map.get(self.cmb_sound.currentIndex(), "soft_chime"),
            "VOLUME": str(self.sld_volume.value()),
            "STATUS_BAR_DURATION": str(self.sld_status_dur.value()),
        }
        if self.txt_api_key.text().strip():
            updates["CLOCKIFY_API_KEY"] = self.txt_api_key.text().strip()
        config.save_config({**config.load_config(), **updates})
        self.settings_saved.emit()
        # Flash "Saved ✓" on button instead of closing
        self.btn_save.setText("Saved ✓")
        self.btn_save.setStyleSheet("background: #4ade80; color: #0a2010; border-radius: 7px; padding: 9px 18px;")
        QTimer.singleShot(2000, self._reset_save_btn)

    def _reset_save_btn(self):
        self.btn_save.setText("Save")
        self.btn_save.setStyleSheet("")
