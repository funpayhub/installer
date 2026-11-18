from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QWidget

from dothub_installer.ui.theme import ACCENTS, clamp


@dataclass
class Piece:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    angle: float
    spin: float
    phase: float
    color: str


class Confetti(QWidget):
    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.pieces: list[Piece] = []
        self._timer = QTimer(self, interval=16, timeout=self._step)
        self.hide()

    def burst(self) -> None:
        parent = self.parentWidget()
        assert parent is not None
        self.setGeometry(parent.rect())
        w = self.width()
        self.pieces = [
            Piece(
                x=random.uniform(0, w),
                y=random.uniform(-260, -10),
                vx=random.uniform(-60, 60),
                vy=random.uniform(140, 320),
                size=random.uniform(7, 13),
                angle=random.uniform(0, 360),
                spin=random.uniform(-360, 360),
                phase=random.uniform(0, math.tau),
                color=random.choice(ACCENTS),
            )
            for _ in range(100)
        ]
        self.show()
        self.raise_()
        self._timer.start()

    def _step(self) -> None:
        dt = 0.016
        for piece in self.pieces:
            piece.x += piece.vx * dt
            piece.y += piece.vy * dt
            piece.vx *= 0.995
            piece.angle += piece.spin * dt
            piece.phase += 7 * dt
        self.pieces = [i for i in self.pieces if i.y < self.height() + 20]
        if not self.pieces:
            self._timer.stop()
            self.hide()
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        for piece in self.pieces:
            painter.save()
            painter.translate(piece.x, piece.y)
            painter.rotate(piece.angle)
            painter.scale(1, max(0.15, abs(math.cos(piece.phase))))
            painter.setOpacity(clamp((self.height() - piece.y) / 120))
            painter.setBrush(QColor(piece.color))
            painter.drawRoundedRect(
                QRectF(-piece.size / 2, -piece.size / 4, piece.size, piece.size / 2),
                1.5,
                1.5,
            )
            painter.restore()
        painter.end()
