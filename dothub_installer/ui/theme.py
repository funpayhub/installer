from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# ---------- theme, taken from the .hub logo ----------

BG = "#1D2230"
SIDEBAR = "#161A25"
SURFACE = "#252B3A"
SURFACE_HOVER = "#2D3446"
BORDER = "#363E52"
TEXT = "#F2F4F8"
MUTED = "#8C95AB"
RED = "#F0272B"
YELLOW = "#FFC619"
GREEN = "#16C75C"
BLUE = "#16B8EA"
ACCENTS = [
    RED,
    YELLOW,
    GREEN,
    BLUE,
]  # the logo stripes, left to right: one accent per installer step
ERROR = "#FF5C60"


STYLESHEET = f"""
QWidget {{ color: {TEXT}; font-size: 10pt; }}
QDialog, QMessageBox {{ background: {BG}; }}
QFrame#sidebar {{ background: {SIDEBAR}; }}

QLabel#title {{ font-size: 20pt; font-weight: 700; }}
QLabel#subtitle, QLabel#hint, QLabel:disabled, QLabel#cardSubtitle {{ color: {MUTED}; }}

QLineEdit, QListWidget {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px;
    padding: 7px 10px; selection-background-color: {BLUE};
}}
QLineEdit:hover {{ border-color: #46506A; }}
QLineEdit:focus {{ border-color: {BLUE}; }}
QLineEdit:disabled {{ color: {MUTED}; }}
QLineEdit[error="true"], QLineEdit[error="true"]:hover, QLineEdit[error="true"]:focus {{ border-color: {ERROR}; }}

QPushButton {{
    background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 8px; padding: 8px 18px;
}}
QPushButton:hover {{ background: {SURFACE_HOVER}; }}
QPushButton:pressed {{ background: {BORDER}; }}
QPushButton:disabled {{ color: {MUTED}; }}
QPushButton#primary {{ background: {TEXT}; color: {BG}; border: none; font-weight: 700; padding: 9px 28px; }}
QPushButton#primary:hover {{ background: #D9DEE8; }}
QPushButton#primary:disabled {{ background: #454D61; color: {MUTED}; }}
QPushButton#star {{ background: {GREEN}; color: {BG}; border: none; font-weight: 700; padding: 9px 20px; }}
QPushButton#star:hover {{ background: #13B052; }}
QPushButton#star:pressed {{ background: #0F9746; }}
QPushButton#danger {{ background: {RED}; color: white; border: none; font-weight: 700; }}
QPushButton#link, QPushButton#link:hover, QPushButton#link:pressed {{
    background: transparent; border: none; padding: 2px 0; color: {MUTED};
}}
QPushButton#link:hover {{ color: {TEXT}; }}
QPushButton#danger:hover {{ background: #D61F23; }}

QFrame#card, QFrame#infoCard {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 12px; }}
QFrame#card:hover {{ border-color: #4A5470; }}
QFrame#card[checked="true"] {{ border-color: {BLUE}; background: #1F3346; }}
QFrame#card QLabel, QFrame#card QRadioButton, QFrame#infoCard QLabel {{ background: transparent; }}
QRadioButton#cardTitle {{ font-size: 11pt; font-weight: 700; spacing: 0; }}
QRadioButton#cardTitle::indicator {{ width: 0; height: 0; }}
QCheckBox, QRadioButton {{ spacing: 8px; }}

QAbstractScrollArea#terminal {{
    background: #12151E; border: 1px solid {BORDER}; border-radius: 10px; padding: 4px;
    font-family: "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace; font-size: 9pt;
}}
QListWidget::item {{ padding: 6px; border-radius: 6px; }}
QListWidget::item:hover {{ background: {SURFACE_HOVER}; }}
QListWidget::item:selected {{ background: #1F3346; color: {TEXT}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle {{ background: {BORDER}; border-radius: 3px; min-height: 24px; min-width: 24px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QToolTip {{ background: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER}; padding: 4px; }}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    for role, color in (
        (QPalette.ColorRole.Window, BG),
        (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.Base, SURFACE),
        (QPalette.ColorRole.AlternateBase, SURFACE_HOVER),
        (QPalette.ColorRole.Text, TEXT),
        (QPalette.ColorRole.Button, SURFACE),
        (QPalette.ColorRole.ButtonText, TEXT),
        (QPalette.ColorRole.Highlight, BLUE),
        (QPalette.ColorRole.HighlightedText, "#FFFFFF"),
        (QPalette.ColorRole.PlaceholderText, "#6B7489"),
        (QPalette.ColorRole.Link, BLUE),
        (QPalette.ColorRole.ToolTipBase, SURFACE),
        (QPalette.ColorRole.ToolTipText, TEXT),
    ):
        palette.setColor(role, QColor(color))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(MUTED))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def mix(a: str | QColor, b: str | QColor, t: float) -> QColor:
    ca, cb, t = QColor(a), QColor(b), clamp(t)
    return QColor(
        round(ca.red() + (cb.red() - ca.red()) * t),
        round(ca.green() + (cb.green() - ca.green()) * t),
        round(ca.blue() + (cb.blue() - ca.blue()) * t),
    )
