from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QVariantAnimation
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
)
from PySide6.QtWidgets import QWidget

from dothub_installer.ui.theme import ACCENTS, BORDER, MUTED, SIDEBAR, TEXT, clamp, mix


class StepList(QWidget):
    PITCH = 42
    RADIUS = 14

    def __init__(self, titles: list[str]) -> None:
        super().__init__()
        self.titles = titles
        self.position = 0.0
        self.pulse = 0.0
        self.setFixedHeight(self.PITCH * (len(titles) - 1) + 2 * self.RADIUS)
        self._pulse = QVariantAnimation(
            self, startValue=0.0, endValue=1.0, duration=1500, loopCount=-1
        )
        self._pulse.valueChanged.connect(self._on_pulse)

    def set_position(self, position: float) -> None:
        self.position = position
        self.update()

    def set_pulse(self, on: bool) -> None:
        if on:
            self._pulse.start()
        else:
            self._pulse.stop()
            self.pulse = 0.0
            self.update()

    def _on_pulse(self, value: float) -> None:
        self.pulse = value
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.RADIUS
        font = painter.font()

        for index, (title, color) in enumerate(zip(self.titles, ACCENTS)):
            cy = r + index * self.PITCH
            done = clamp(self.position - index)
            active = clamp(1 - abs(self.position - index))
            lit = max(done, active)

            if (
                index < len(ACCENTS) - 1
            ):  # connector to the next badge, filled with the colors as the step completes
                y1, y2 = cy + r + 4, cy + self.PITCH - r - 4
                painter.setPen(
                    QPen(
                        QColor(BORDER),
                        2,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                    )
                )
                painter.drawLine(QPointF(r, y1), QPointF(r, y2))
                if done > 0:
                    gradient = QLinearGradient(0, y1, 0, y2)
                    gradient.setColorAt(0, QColor(color))
                    gradient.setColorAt(1, QColor(ACCENTS[index + 1]))
                    painter.setPen(
                        QPen(
                            QBrush(gradient),
                            2,
                            Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap,
                        )
                    )
                    painter.drawLine(QPointF(r, y1), QPointF(r, y1 + (y2 - y1) * done))

            center = QPointF(r, cy)
            if active > 0.5 and self._pulse.state() == QVariantAnimation.State.Running:
                ring = QColor(color)
                ring.setAlphaF((1 - self.pulse) * 0.6)
                painter.setPen(QPen(ring, 2))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(center, r + 10 * self.pulse, r + 10 * self.pulse)

            fill = QColor(color)
            fill.setAlphaF(active)
            painter.setPen(QPen(mix(BORDER, color, lit), 2))
            painter.setBrush(fill)
            painter.drawEllipse(center, r - 1, r - 1)

            badge = QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)
            font.setBold(True)
            font.setWeight(
                QFont.Weight.ExtraBold if active > 0.5 else QFont.Weight.Normal
            )
            painter.setFont(font)
            if done < 1:
                painter.setOpacity(1 - done)
                painter.setPen(mix(MUTED, SIDEBAR, active))
                painter.drawText(badge, Qt.AlignmentFlag.AlignCenter, str(index + 1))
            if done > 0:
                painter.save()
                painter.translate(center)
                painter.scale(0.6 + 0.4 * done, 0.6 + 0.4 * done)
                painter.setOpacity(done)
                painter.setPen(
                    QPen(
                        QColor(color),
                        2.4,
                        Qt.PenStyle.SolidLine,
                        Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin,
                    )
                )
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawPolyline(
                    QPolygonF([QPointF(-5, 0.5), QPointF(-1.5, 4), QPointF(5, -3.5)])
                )
                painter.restore()
            painter.setOpacity(1)

            font.setWeight(QFont.Weight.Bold if lit > 0.5 else QFont.Weight.Normal)
            painter.setFont(font)
            painter.setPen(mix(MUTED, TEXT, lit))
            painter.drawText(
                QRectF(2 * r + 12, cy - r, self.width() - 2 * r - 12, 2 * r),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                title,
            )
        painter.end()


class AccentStripe(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.position = 0.0
        self.setFixedSize(72, 4)

    def set_position(self, position: float) -> None:
        self.position = position
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()), 2, 2)
        painter.setClipPath(clip)
        width = self.width() / len(ACCENTS)
        for i, color in enumerate(ACCENTS):
            segment = QColor(color)
            segment.setAlphaF(0.22 + 0.78 * clamp(self.position - i + 1))
            painter.fillRect(QRectF(i * width, 0, width + 1, self.height()), segment)
        painter.end()
