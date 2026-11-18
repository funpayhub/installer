from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QBrush, QColor, QPainter, QRadialGradient
from PySide6.QtWidgets import QWidget

from dothub_installer.ui.theme import ACCENTS, BG, mix


class Backdrop(QWidget):
    def __init__(self) -> None:
        super().__init__(objectName="content")
        self.position = 0.0

    def set_position(self, position: float) -> None:
        self.position = position
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(BG))
        accent = accent_at(self.position)
        w, h = self.width(), self.height()
        t = self.position / (len(ACCENTS) - 1)
        reach = max(w, h)
        for center, radius, alpha in (
            (QPointF(w * (1.0 - 0.45 * t), -h * 0.1), reach * 0.8, 0.26),
            (QPointF(w * (0.05 + 0.3 * t), h * 1.1), reach * 0.6, 0.12),
        ):
            gradient = QRadialGradient(center, radius)
            glow = QColor(accent)
            glow.setAlphaF(alpha)
            gradient.setColorAt(0, glow)
            glow.setAlpha(0)
            gradient.setColorAt(1, glow)
            painter.fillRect(self.rect(), QBrush(gradient))
        painter.end()


def accent_at(position: float) -> QColor:
    index = min(int(position), len(ACCENTS) - 1)
    return mix(
        ACCENTS[index], ACCENTS[min(index + 1, len(ACCENTS) - 1)], position - index
    )
