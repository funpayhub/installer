"""The .hub logo, drawn from assets/logo.svg.

The SVG is traced from the original logo and has a transparent background (the gaps where the stripes pass
behind the letters are cut out), so it fits any background: the app icon paints the theme background under it
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

from dothub_installer.ui.theme import BG

LOGO = Path(__file__).resolve().parent / "assets" / "logo.svg"

_renderer: QSvgRenderer | None = None
_canvas = (
    QRectF()
)  # the whole view box as loaded: paint_logo changes the renderer's view box to crop


def _logo() -> QSvgRenderer:
    global _renderer, _canvas
    if _renderer is None:
        _renderer = QSvgRenderer(str(LOGO))
        if not _renderer.isValid():
            raise ValueError(f"Invalid SVG: {LOGO}")
        _canvas = _renderer.viewBoxF()
    return _renderer


def paint_logo(painter: QPainter, rect: QRectF, crop: bool) -> None:
    """Draws the logo centered in rect, keeping its proportions: the whole square canvas, or (crop) only the artwork"""
    renderer = _logo()
    source = renderer.boundsOnElement("art") if crop else _canvas
    scale = min(rect.width() / source.width(), rect.height() / source.height())
    target = QRectF(0, 0, source.width() * scale, source.height() * scale)
    target.moveCenter(rect.center())
    renderer.setViewBox(source)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    renderer.render(painter, target)


def logo_pixmap(size: int) -> QPixmap:
    """The square logo on the theme background: window and executable icon"""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(BG))
    painter = QPainter(pixmap)
    paint_logo(painter, QRectF(0, 0, size, size), crop=False)
    painter.end()
    return pixmap


class LogoWidget(QWidget):
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        paint_logo(painter, QRectF(self.rect()), crop=True)
        painter.end()
