from __future__ import annotations

from PySide6.QtGui import QColor

from dothub_installer.ui.theme import BLUE, ERROR, GREEN, RED, YELLOW

FOREGROUND = QColor("#C9D1E3")
BACKGROUND = QColor("#12151E")

# pyte names the ANSI colors this way: "brown" is yellow, "bright*" are the aixterm 90-97 colors
ANSI = {
    "black": "#2A3044",
    "red": RED,
    "green": GREEN,
    "brown": YELLOW,
    "blue": "#5B8CFF",
    "magenta": "#C678DD",
    "cyan": BLUE,
    "white": "#C9D1E3",
    "brightblack": "#6B7489",
    "brightred": ERROR,
    "brightgreen": "#4BE08A",
    "brightbrown": "#FFD84D",
    "brightblue": "#8FB0FF",
    "brightmagenta": "#E0A3F0",
    "brightcyan": "#6BD9F5",
    "brightwhite": "#FFFFFF",
}
_cache: dict[str, QColor] = {}


def resolve(name: str, default: QColor) -> QColor:
    """Color of a pyte cell: 'default', an ANSI name or a 6-digit hex string (256 and true color)"""
    if name == "default":
        return default
    color = _cache.get(name)
    if color is None:
        color = _cache[name] = QColor(ANSI.get(name) or f"#{name}")
    return color
