from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QPushButton

from dothub_installer.ui.theme import MUTED, TEXT

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def svg_icon(name: str, color: str | QColor) -> QIcon:
    svg = (
        (ASSETS / f"{name}.svg")
        .read_text(encoding="utf-8")
        .replace("currentColor", QColor(color).name())
    )
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    if not renderer.isValid():
        raise ValueError(f"Invalid SVG: {name}.svg")

    icon = QIcon()
    for size in (16, 24, 32, 48):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


class LinkButton(QPushButton):
    def __init__(self, text: str, url: str, icon_name: str) -> None:
        super().__init__(
            text,
            objectName="link",
            cursor=Qt.CursorShape.PointingHandCursor,
            toolTip=url,
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._icon, self._hover_icon = (
            svg_icon(icon_name, MUTED),
            svg_icon(icon_name, TEXT),
        )
        self.setIcon(self._icon)
        self.setIconSize(QSize(16, 16))
        self.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))

    def enterEvent(self, event) -> None:
        self.setIcon(self._hover_icon)
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self.setIcon(self._icon)
        super().leaveEvent(event)
