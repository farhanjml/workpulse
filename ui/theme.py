"""
ui/theme.py — Dotdash design tokens and font loader.
Import DARK, LIGHT, or call get_colors(mode) in each UI file.
"""

from PyQt6.QtGui import QFontDatabase
from core.config import get_bool
import os, sys


def _base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.join(os.path.dirname(__file__), "..")


def load_fonts():
    """Load Sora from assets/fonts/. Call once at app start."""
    fonts_dir = os.path.join(_base_dir(), "assets", "fonts")
    loaded = []
    for name in ["Sora-Regular.ttf", "Sora-SemiBold.ttf", "Sora-Bold.ttf"]:
        path = os.path.join(fonts_dir, name)
        if os.path.exists(path):
            fid = QFontDatabase.addApplicationFont(path)
            if fid >= 0:
                loaded.append(name)
    return loaded


def font_family() -> str:
    """Return 'Sora' if loaded, else fall back to Segoe UI."""
    families = QFontDatabase.families()
    return "Sora" if "Sora" in families else "Segoe UI"


# ── Color palettes ────────────────────────────────────────────────────────────

DARK = {
    "bg":           "#030404",
    "s0":           "#080909",
    "s1":           "#0e0f0f",
    "s2":           "#141515",
    "s3":           "#1a1b1b",
    "border":       "rgba(255,255,255,0.055)",
    "border_h":     "rgba(255,255,255,0.10)",
    "gold":         "#e9bb51",
    "gold_dim":     "rgba(233,187,81,0.6)",
    "gold_border":  "rgba(233,187,81,0.22)",
    "gold_bg":      "rgba(233,187,81,0.07)",
    "t1":           "#f2ede4",
    "t2":           "#8a8478",
    "t3":           "#3d3b37",
    "green":        "#4ade80",
    "green_bg":     "rgba(74,222,128,0.07)",
    "green_border": "rgba(74,222,128,0.22)",
    "red":          "#fca5a5",
    "red_bg":       "rgba(252,165,165,0.07)",
    "red_border":   "rgba(252,165,165,0.22)",
    "state_active":  "#4ade80",
    "state_overdue": "#ef4444",
    "state_idle":    "#3d3b37",
}

LIGHT = {
    "bg":           "#f5f0e8",
    "s0":           "#fffdf8",
    "s1":           "#f9f4ec",
    "s2":           "#f0eade",
    "s3":           "#e8e0d0",
    "border":       "rgba(0,0,0,0.08)",
    "border_h":     "rgba(0,0,0,0.14)",
    "gold":         "#e9bb51",
    "gold_dim":     "#c9962a",
    "gold_border":  "rgba(233,187,81,0.4)",
    "gold_bg":      "rgba(233,187,81,0.12)",
    "t1":           "#1a1710",
    "t2":           "#6b6355",
    "t3":           "#b0a898",
    "green":        "#16a34a",
    "green_bg":     "rgba(22,163,74,0.07)",
    "green_border": "rgba(22,163,74,0.25)",
    "red":          "#dc2626",
    "red_bg":       "rgba(220,38,38,0.06)",
    "red_border":   "rgba(220,38,38,0.25)",
    "state_active":  "#16a34a",
    "state_overdue": "#dc2626",
    "state_idle":    "#b0a898",
}


def get_colors() -> dict:
    """Return color dict for current mode (reads DARK_MODE from config)."""
    return LIGHT if not get_bool("DARK_MODE") else DARK


def base_stylesheet(c: dict) -> str:
    """Return the base QSS shared across all windows."""
    ff = font_family()
    return f"""
QWidget {{
    background: {c['bg']};
    color: {c['t1']};
    font-family: '{ff}', 'Segoe UI', sans-serif;
}}
QLineEdit, QComboBox, QTimeEdit {{
    background: {c['s2']};
    border: 1px solid {c['border']};
    border-radius: 8px;
    padding: 7px 11px;
    color: {c['t1']};
    font-size: 12px;
}}
QLineEdit:focus, QComboBox:focus, QTimeEdit:focus {{
    border-color: {c['gold_border']};
}}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {c['s2']};
    color: {c['t1']};
    selection-background-color: {c['gold_bg']};
}}
QPushButton {{
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    padding: 9px 14px;
    border: 1px solid {c['border']};
    background: {c['s2']};
    color: {c['t2']};
    font-family: '{ff}', 'Segoe UI', sans-serif;
}}
QPushButton:hover {{ color: {c['t1']}; border-color: {c['border_h']}; }}
QPushButton#btnPrimary {{
    background: {c['gold']};
    border-color: {c['gold']};
    color: #030404;
}}
QPushButton#btnPrimary:hover {{ background: #f0c66a; }}
QPushButton#btnGhost {{
    background: transparent;
    color: {c['t3']};
}}
QPushButton#btnGhost:hover {{ color: {c['t2']}; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: {c['s1']};
    width: 6px;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {c['s3']};
    border-radius: 3px;
}}
"""
