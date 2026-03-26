"""
ui/summary.py — Today's Log summary window
"""

import csv
from datetime import datetime, date, timedelta
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QFrame, QApplication, QFileDialog
)
from PyQt6.QtCore import Qt
from core import database

STYLE = """
QWidget { background: #0d0d0f; color: #e8e8f0; font-family: 'JetBrains Mono', monospace; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #1c1c22; width: 6px; border-radius: 3px; }
QScrollBar::handle:vertical { background: #353545; border-radius: 3px; }
QPushButton { border-radius: 7px; font-size: 11px; font-family: 'JetBrains Mono', monospace; padding: 8px 14px; border: 1px solid #2a2a38; background: #1c1c22; color: #9090a8; }
QPushButton:hover { color: #e8e8f0; }
QPushButton#btnPrimary { background: #7c6af7; border-color: #7c6af7; color: white; }
QPushButton#btnPrimary:hover { background: #9d8fff; }
"""

PROJECT_COLORS = {
    "internal_rdrs":       ("#7c6af7", "#1a1630"),
    "maybank_impl":        ("#4ade80", "#0f2318"),
    "maybank_presales":    ("#4ade80", "#0f2318"),
    "maybank_sg_presales": ("#34d399", "#0a2018"),
    "rhb_presales":        ("#fbbf24", "#221a08"),
    "internal_ai":         ("#60a5fa", "#0f1a2e"),
    "internal_infra":      ("#f472b6", "#2a0f1e"),
    "internal_mobius":     ("#a78bfa", "#1a1030"),
    "internal_office":     ("#9090a8", "#1a1a22"),
}

SHORT_NAMES = {
    "Internal - RDRS": "Int·RDRS",
    "Malayan Banking Bhd - RDRS Implementation": "MBB·Impl",
    "Malayan Banking Bhd - RDRS Presales": "MBB·Pre",
    "Maybank Singapore Limited - RDRS Presales": "MBS·Pre",
    "RHB Bank Bhd - RDRS Presales": "RHB·Pre",
    "Internal - AI Exploration": "Int·AI",
    "Internal - Infra": "Int·Infra",
    "Internal - Mobius": "Int·Mobius",
    "Internal - Office": "Int·Office",
}


def _fmt_duration(start, end):
    if not end:
        return "active"
    try:
        s = datetime.strptime(start, "%H:%M")
        e = datetime.strptime(end, "%H:%M")
        mins = int((e - s).total_seconds() // 60)
        return f"{mins}m" if mins < 60 else f"{mins // 60}h {mins % 60}m"
    except Exception:
        return ""


def _fmt_total(minutes):
    return f"{minutes // 60}hr {minutes % 60}min"


class EntryRow(QFrame):
    def __init__(self, entry, on_edit, on_delete, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.setStyleSheet("QFrame { background: transparent; border-radius: 8px; } QFrame:hover { background: #1c1c22; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        lbl_time = QLabel(f"{entry['start_time']} – {entry['end_time'] or 'now'}")
        lbl_time.setFixedWidth(115)
        lbl_time.setStyleSheet("color: #5a5a72; font-size: 11px;")
        layout.addWidget(lbl_time)

        pid = entry.get("project_id", "")
        fg, bg = PROJECT_COLORS.get(pid, ("#9090a8", "#1a1a22"))
        lbl_badge = QLabel(SHORT_NAMES.get(entry.get("project_name", ""), entry.get("project_name", "")[:10]))
        lbl_badge.setStyleSheet(f"background: {bg}; color: {fg}; border-radius: 4px; padding: 2px 8px; font-size: 10px;")
        lbl_badge.setFixedWidth(90)
        layout.addWidget(lbl_badge)

        lbl_desc = QLabel(entry.get("task", ""))
        lbl_desc.setStyleSheet("color: #e8e8f0; font-size: 12px;")
        lbl_desc.setWordWrap(True)
        layout.addWidget(lbl_desc, 1)

        lbl_dur = QLabel(_fmt_duration(entry["start_time"], entry.get("end_time")))
        lbl_dur.setStyleSheet("color: #5a5a72; font-size: 10px;")
        layout.addWidget(lbl_dur)

        btn_copy = QPushButton("⎘")
        btn_copy.setFixedSize(24, 24)
        btn_copy.setStyleSheet("QPushButton { padding: 0; font-size: 13px; } QPushButton:hover { color: #7c6af7; }")
        btn_copy.clicked.connect(self._copy_entry)
        layout.addWidget(btn_copy)

        btn_del = QPushButton("✕")
        btn_del.setFixedSize(24, 24)
        btn_del.setStyleSheet("QPushButton { padding: 0; font-size: 11px; } QPushButton:hover { color: #f87171; }")
        btn_del.clicked.connect(lambda: on_delete(entry["id"]))
        layout.addWidget(btn_del)

    def _copy_entry(self):
        e = self.entry
        QApplication.clipboard().setText(f"{e['start_time']} - {e['end_time'] or 'now'}  [{e['project_name']}]  {e['task']}")


class GapRow(QFrame):
    def __init__(self, start, end, parent=None):
        super().__init__(parent)
        self.setStyleSheet("QFrame { background: rgba(248,113,113,0.06); border: 1px solid rgba(248,113,113,0.2); border-radius: 8px; }")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        lbl = QLabel(f"⚠  {start} – {end}  ·  Unaccounted gap")
        lbl.setStyleSheet("color: #f87171; font-size: 11px;")
        layout.addWidget(lbl)
        layout.addStretch()


class BreakRow(QFrame):
    def __init__(self, duration_mins, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        line1 = QFrame()
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("background: #2a2a38; max-height: 1px;")
        lbl = QLabel(f"☕  Break  ·  {duration_mins}min")
        lbl.setStyleSheet("color: #3a3a52; font-size: 10px;")
        line2 = QFrame()
        line2.setFrameShape(QFrame.Shape.HLine)
        line2.setStyleSheet("background: #2a2a38; max-height: 1px;")
        layout.addWidget(line1, 1)
        layout.addWidget(lbl)
        layout.addWidget(line2, 1)


class SummaryWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_date = date.today().isoformat()
        self._setup_window()
        self._setup_ui()
        self.refresh()

    def _setup_window(self):
        self.setWindowTitle("WorkPulse — Today's Log")
        self.setMinimumSize(620, 500)
        self.resize(680, 600)
        self.setStyleSheet(STYLE)
        self.setWindowFlags(Qt.WindowType.Window)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        toolbar = QWidget()
        toolbar.setStyleSheet("background: #1c1c22; border-bottom: 1px solid #2a2a38;")
        toolbar.setFixedHeight(52)
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(16, 0, 16, 0)

        btn_prev = QPushButton("←")
        btn_prev.setFixedSize(28, 28)
        btn_prev.clicked.connect(self._prev_day)
        self.lbl_date = QLabel()
        self.lbl_date.setStyleSheet("font-size: 13px; color: #e8e8f0; font-weight: 600;")
        btn_next = QPushButton("→")
        btn_next.setFixedSize(28, 28)
        btn_next.clicked.connect(self._next_day)
        self.btn_day = QPushButton("Day")
        self.btn_week = QPushButton("Week")
        self.btn_day.setCheckable(True)
        self.btn_week.setCheckable(True)
        self.btn_day.setChecked(True)
        self.lbl_total = QLabel()
        self.lbl_total.setStyleSheet("color: #9d8fff; font-size: 11px;")

        tb_layout.addWidget(btn_prev)
        tb_layout.addWidget(self.lbl_date)
        tb_layout.addWidget(btn_next)
        tb_layout.addSpacing(16)
        tb_layout.addWidget(self.btn_day)
        tb_layout.addWidget(self.btn_week)
        tb_layout.addStretch()
        tb_layout.addWidget(self.lbl_total)
        layout.addWidget(toolbar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.entries_widget = QWidget()
        self.entries_layout = QVBoxLayout(self.entries_widget)
        self.entries_layout.setContentsMargins(8, 8, 8, 8)
        self.entries_layout.setSpacing(2)
        self.entries_layout.addStretch()
        self.scroll.setWidget(self.entries_widget)
        layout.addWidget(self.scroll, 1)

        footer = QWidget()
        footer.setStyleSheet("background: #1c1c22; border-top: 1px solid #2a2a38;")
        footer.setFixedHeight(52)
        ft_layout = QHBoxLayout(footer)
        ft_layout.setContentsMargins(16, 0, 16, 0)
        ft_layout.setSpacing(8)
        btn_copy = QPushButton("Copy All")
        btn_copy.setObjectName("btnPrimary")
        btn_copy.clicked.connect(self._copy_all)
        btn_txt = QPushButton("Export .txt")
        btn_txt.clicked.connect(self._export_txt)
        btn_csv = QPushButton("Export CSV")
        btn_csv.clicked.connect(self._export_csv)
        ft_layout.addWidget(btn_copy)
        ft_layout.addWidget(btn_txt)
        ft_layout.addWidget(btn_csv)
        ft_layout.addStretch()
        layout.addWidget(footer)

    def refresh(self):
        entries = database.get_merged_entries(self.current_date)
        total_mins = database.get_total_logged_minutes(self.current_date)
        d = datetime.strptime(self.current_date, "%Y-%m-%d")
        self.lbl_date.setText(d.strftime("%A, %d %b %Y"))
        self.lbl_total.setText(f"{_fmt_total(total_mins)} logged")

        while self.entries_layout.count() > 1:
            item = self.entries_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not entries:
            lbl_empty = QLabel("No entries yet today.\nHit Alt+L to log your first task.")
            lbl_empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl_empty.setStyleSheet("color: #3a3a52; font-size: 12px; padding: 40px;")
            self.entries_layout.insertWidget(0, lbl_empty)
            return

        prev_end = None
        insert_pos = 0
        for entry in entries:
            if prev_end and not entry.get("is_break"):
                gap_mins = self._minutes_diff(prev_end, entry["start_time"])
                if gap_mins > 5:
                    self.entries_layout.insertWidget(insert_pos, GapRow(prev_end, entry["start_time"]))
                    insert_pos += 1

            if entry.get("is_break"):
                dur = self._minutes_diff(entry["start_time"], entry.get("end_time", entry["start_time"]))
                row = BreakRow(dur)
            else:
                row = EntryRow(entry, on_edit=lambda eid: None, on_delete=lambda eid: self._delete_entry(eid))

            self.entries_layout.insertWidget(insert_pos, row)
            insert_pos += 1
            prev_end = entry.get("end_time")

    def _minutes_diff(self, start, end):
        try:
            s = datetime.strptime(start, "%H:%M")
            e = datetime.strptime(end, "%H:%M")
            return max(0, int((e - s).total_seconds() // 60))
        except Exception:
            return 0

    def _prev_day(self):
        d = datetime.strptime(self.current_date, "%Y-%m-%d") - timedelta(days=1)
        self.current_date = d.strftime("%Y-%m-%d")
        self.refresh()

    def _next_day(self):
        d = datetime.strptime(self.current_date, "%Y-%m-%d") + timedelta(days=1)
        if d.date() <= date.today():
            self.current_date = d.strftime("%Y-%m-%d")
            self.refresh()

    def _delete_entry(self, entry_id):
        database.delete_entry(entry_id)
        self.refresh()

    def _build_text_log(self):
        entries = database.get_merged_entries(self.current_date)
        d = datetime.strptime(self.current_date, "%Y-%m-%d")
        lines = [f"{'━' * 52}", f"  WORK LOG — {d.strftime('%A, %d %b %Y').upper()}", f"{'━' * 52}"]
        for e in entries:
            if e.get("is_break"):
                continue
            lines.append(f"{e['start_time']} - {e.get('end_time') or 'now'}  [{e['project_name']}]  {e['task']}")
        total = database.get_total_logged_minutes(self.current_date)
        lines += [f"{'━' * 52}", f"Total logged: {_fmt_total(total)}"]
        return "\n".join(lines)

    def _copy_all(self):
        QApplication.clipboard().setText(self._build_text_log())

    def _export_txt(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Log", f"worklog_{self.current_date}.txt", "Text Files (*.txt)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._build_text_log())

    def _export_csv(self):
        entries = database.get_merged_entries(self.current_date)
        path, _ = QFileDialog.getSaveFileName(self, "Export CSV", f"worklog_{self.current_date}.csv", "CSV Files (*.csv)")
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Date", "Start", "End", "Project", "Task", "Duration"])
                for e in entries:
                    if e.get("is_break"):
                        continue
                    writer.writerow([e["date"], e["start_time"], e.get("end_time", ""), e["project_name"], e["task"], _fmt_duration(e["start_time"], e.get("end_time"))])
