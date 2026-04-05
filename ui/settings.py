"""
ui/settings.py — Settings window (Dotdash theme)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QComboBox, QLineEdit,
    QTimeEdit, QCheckBox, QScrollArea
)
from PyQt6.QtCore import Qt, QTime, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeySequence

from core import config
from ui.theme import get_colors, base_stylesheet, font_family


class Toggle(QCheckBox):
    def __init__(self, checked=False):
        super().__init__()
        self.setChecked(checked)
        # Styled via parent window QSS


class SettingRow(QWidget):
    def __init__(self, label: str, control: QWidget):
        super().__init__()
        self.setObjectName("settingRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(label)
        lbl.setObjectName("rowLabel")
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(control)


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
        self.lbl.setObjectName("sliderVal")
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
        self.setFixedWidth(180)
        self.clicked.connect(self._start_recording)

    def _start_recording(self):
        self._recording = True
        self.setText("Press keys...")

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
            self._recording = False
            self.hotkey_captured.emit(combo)

    def get_hotkey(self) -> str:
        return self._current


class SettingsWindow(QWidget):
    settings_saved = pyqtSignal()
    _sync_result = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cfg = config.load_config()
        self._setup_window()
        self._setup_ui()
        self._sync_result.connect(self._on_sync_done)
        self._apply_theme()

    def _setup_window(self):
        self.setWindowTitle("WorkPulse — Settings")
        self.setFixedWidth(460)
        self.setWindowFlags(Qt.WindowType.Window)

    def _apply_theme(self):
        c = get_colors()
        self.setStyleSheet(base_stylesheet(c) + f"""
            QWidget#settingsHeader {{
                background: {c['s1']};
                border-bottom: 1px solid {c['border']};
            }}
            QWidget#settingsFooter {{
                background: {c['s1']};
                border-top: 1px solid {c['border']};
            }}
            QWidget#settingRow {{
                background: {c['s2']};
                border-radius: 8px;
            }}
            QWidget#settingRow:hover {{
                background: {c['s3']};
            }}
            QWidget#settingRow QLabel {{
                color: {c['t2']};
                background: transparent;
            }}
            QLabel#sectionLabel {{
                color: {c['t3']};
                font-size: 10px;
                letter-spacing: 2px;
                padding: 0 4px;
                background: transparent;
            }}
            QLabel#sliderVal {{
                color: {c['gold']};
                background: transparent;
            }}
            QLabel#hint {{
                color: {c['t3']};
                font-size: 10px;
                padding: 0 12px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 36px;
                height: 20px;
                border-radius: 10px;
                background: {c['s3']};
                border: 1px solid {c['border']};
            }}
            QCheckBox::indicator:checked {{
                background: {c['gold']};
                border-color: {c['gold']};
            }}
            QSlider::groove:horizontal {{
                height: 4px;
                background: {c['s3']};
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                width: 14px;
                height: 14px;
                background: {c['gold']};
                border-radius: 7px;
                margin: -5px 0;
            }}
            QSlider::sub-page:horizontal {{
                background: {c['gold']};
                border-radius: 2px;
            }}
            QPushButton#btnSave {{
                background: {c['gold']};
                border-color: {c['gold']};
                color: #030404;
                font-weight: 700;
            }}
            QPushButton#btnSave:hover {{ background: #f0c66a; }}
            QPushButton#btnSync {{
                background: {c['gold_bg']};
                border: 1px solid {c['gold_border']};
                color: {c['gold']};
            }}
            QPushButton#btnSync:hover {{ background: rgba(233,187,81,0.12); }}
        """)

    def showEvent(self, event):
        self._apply_theme()
        super().showEvent(event)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("settingsHeader")
        header.setFixedHeight(52)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(16, 0, 16, 0)
        lbl = QLabel("Settings")
        lbl.setStyleSheet("font-size: 14px; font-weight: 600;")
        h_layout.addWidget(lbl)
        layout.addWidget(header)

        # Scrollable body
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(16, 16, 16, 16)
        body_layout.setSpacing(16)

        # ── TIMING ───────────────────────────────────────────────────────────────
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

        # ── HOTKEYS ──────────────────────────────────────────────────────────────
        body_layout.addWidget(self._section_label("HOTKEYS"))
        self.hotkey_btn = HotkeyCapture(self._cfg.get("HOTKEY", "alt+l"))
        body_layout.addWidget(SettingRow("Quick log", self.hotkey_btn))
        self.interrupt_hotkey_btn = HotkeyCapture(self._cfg.get("INTERRUPT_HOTKEY", "alt+shift+l"))
        body_layout.addWidget(SettingRow("Quick interrupt", self.interrupt_hotkey_btn))
        hint = QLabel("Click the button, then press your desired key combo")
        hint.setObjectName("hint")
        body_layout.addWidget(hint)

        # ── BEHAVIOUR ────────────────────────────────────────────────────────────
        body_layout.addWidget(self._section_label("BEHAVIOUR"))
        self.tog_boot = Toggle(self._cfg.get("START_ON_BOOT", "true") == "true")
        self.tog_dark = Toggle(self._cfg.get("DARK_MODE", "true") == "true")
        self.tog_window = Toggle(self._cfg.get("WINDOW_TRACKING", "false") == "true")
        self.tog_clipboard = Toggle(self._cfg.get("CLIPBOARD_HINTS", "true") == "true")
        body_layout.addWidget(SettingRow("Start on boot", self.tog_boot))
        body_layout.addWidget(SettingRow("Dark mode", self.tog_dark))
        body_layout.addWidget(SettingRow("Window tracking", self.tog_window))
        body_layout.addWidget(SettingRow("Clipboard hints", self.tog_clipboard))

        # ── SOUND ────────────────────────────────────────────────────────────────
        body_layout.addWidget(self._section_label("SOUND"))
        self.cmb_sound = QComboBox()
        self.cmb_sound.setFixedWidth(150)
        for theme in ["Soft chime", "Typewriter ding", "Retro beep", "None"]:
            self.cmb_sound.addItem(theme)
        theme_map = {"soft_chime": 0, "typewriter": 1, "retro": 2, "none": 3}
        self.cmb_sound.setCurrentIndex(theme_map.get(self._cfg.get("SOUND_THEME", "soft_chime"), 0))
        self.sld_volume = SliderWithValue(0, 100, int(self._cfg.get("VOLUME", 60)), "%")
        body_layout.addWidget(SettingRow("Sound theme", self.cmb_sound))
        body_layout.addWidget(SettingRow("Volume", self.sld_volume))

        self.cmb_play_on = QComboBox()
        self.cmb_play_on.setFixedWidth(160)
        play_on_options = [
            ("All events", "all"),
            ("Ping only", "ping_only"),
            ("Ping + Overdue", "ping_overdue"),
            ("None", "none"),
        ]
        play_on_val = self._cfg.get("PLAY_ON", "all")
        for label, value in play_on_options:
            self.cmb_play_on.addItem(label, value)
        play_on_index = next((i for i, (_, v) in enumerate(play_on_options) if v == play_on_val), 0)
        self.cmb_play_on.setCurrentIndex(play_on_index)
        body_layout.addWidget(SettingRow("Play on", self.cmb_play_on))

        # ── CLOCKIFY ─────────────────────────────────────────────────────────────
        body_layout.addWidget(self._section_label("CLOCKIFY"))
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_api_key.setPlaceholderText("Paste API key here...")
        self.txt_api_key.setFixedWidth(200)
        body_layout.addWidget(SettingRow("API Key", self.txt_api_key))

        self.txt_workspace = QLineEdit(self._cfg.get("CLOCKIFY_WORKSPACE_ID", ""))
        self.txt_workspace.setPlaceholderText("Workspace ID...")
        self.txt_workspace.setFixedWidth(200)
        body_layout.addWidget(SettingRow("Workspace ID", self.txt_workspace))

        # Sync row
        sync_row = QWidget()
        sync_row.setObjectName("settingRow")
        sync_layout = QHBoxLayout(sync_row)
        sync_layout.setContentsMargins(12, 8, 12, 8)
        sync_label = QLabel("Sync Projects")
        sync_label.setObjectName("rowLabel")
        self.btn_sync_projects = QPushButton("↻ Sync Projects")
        self.btn_sync_projects.setObjectName("btnSync")
        self.btn_sync_projects.clicked.connect(self._sync_projects)
        sync_layout.addWidget(sync_label)
        sync_layout.addStretch()
        sync_layout.addWidget(self.btn_sync_projects)
        body_layout.addWidget(sync_row)

        last_sync = self._cfg.get("LAST_CLOCKIFY_SYNC", "")
        self.lbl_sync_status = QLabel(f"Last synced: {last_sync}" if last_sync else "Not synced yet")
        self.lbl_sync_status.setObjectName("hint")
        body_layout.addWidget(self.lbl_sync_status)

        body_layout.addStretch()
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)

        # Footer
        footer = QWidget()
        footer.setObjectName("settingsFooter")
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
        lbl.setObjectName("sectionLabel")
        return lbl

    def _save(self):
        theme_map = {0: "soft_chime", 1: "typewriter", 2: "retro", 3: "none"}
        updates = {
            "PING_INTERVAL":       str(self.sld_ping.value()),
            "IDLE_THRESHOLD":      str(self.sld_idle.value()),
            "OVERDUE_WARNING":     str(self.sld_overdue.value()),
            "WORK_START":          self.time_start.time().toString("HH:mm"),
            "END_OF_DAY":          self.time_eod.time().toString("HH:mm"),
            "HOTKEY":              self.hotkey_btn.get_hotkey(),
            "INTERRUPT_HOTKEY":    self.interrupt_hotkey_btn.get_hotkey(),
            "START_ON_BOOT":       "true" if self.tog_boot.isChecked() else "false",
            "DARK_MODE":           "true" if self.tog_dark.isChecked() else "false",
            "WINDOW_TRACKING":     "true" if self.tog_window.isChecked() else "false",
            "CLIPBOARD_HINTS":     "true" if self.tog_clipboard.isChecked() else "false",
            "SOUND_THEME":         theme_map.get(self.cmb_sound.currentIndex(), "soft_chime"),
            "VOLUME":              str(self.sld_volume.value()),
            "PLAY_ON":             self.cmb_play_on.currentData(),
            "STATUS_BAR_DURATION": str(self.sld_status_dur.value()),
        }
        if self.txt_api_key.text().strip():
            updates["CLOCKIFY_API_KEY"] = self.txt_api_key.text().strip()
        if self.txt_workspace.text().strip():
            updates["CLOCKIFY_WORKSPACE_ID"] = self.txt_workspace.text().strip()
        config.save_config({**config.load_config(), **updates})
        self.settings_saved.emit()
        self.btn_save.setText("Saved ✓")
        self.btn_save.setStyleSheet(
            "background: #4ade80; color: #0a2010; border-radius: 8px; padding: 9px 14px; font-weight: 700;"
        )
        QTimer.singleShot(2000, self._reset_save_btn)

    def _sync_projects(self):
        self.btn_sync_projects.setText("Syncing...")
        self.btn_sync_projects.setEnabled(False)
        import threading
        def _run():
            from core.clockify import sync_projects_to_cache
            ok = sync_projects_to_cache()
            self._sync_result.emit(ok)
        threading.Thread(target=_run, daemon=True).start()

    @pyqtSlot(bool)
    def _on_sync_done(self, ok: bool):
        from core.config import get
        self.btn_sync_projects.setEnabled(True)
        self.btn_sync_projects.setText("↻ Sync Projects")
        if ok:
            last_sync = get("LAST_CLOCKIFY_SYNC", "")
            self.lbl_sync_status.setText(f"Last synced: {last_sync}")
            self.lbl_sync_status.setStyleSheet("")
        else:
            c = get_colors()
            self.lbl_sync_status.setText("Sync failed — check API key")
            self.lbl_sync_status.setStyleSheet(f"color: {c['red']}; font-size: 10px; padding: 0 12px;")

    def _reset_save_btn(self):
        self.btn_save.setText("Save")
        self.btn_save.setStyleSheet("")
