from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


class AnimatedStack(QStackedWidget):
    OFFSET = 40

    def __init__(self) -> None:
        super().__init__()
        self._direction = 1

        # outgoing and incoming page while animating
        self._pages: tuple[QWidget, QWidget] | None = None

        self._animation = QVariantAnimation(
            self,
            startValue=0.0,
            endValue=1.0,
            duration=400,
            easingCurve=QEasingCurve.Type.OutCubic,
            valueChanged=self._tick,
            finished=self._finish,
        )

    def slide_to(self, index: int) -> None:
        self._finish()
        current = self.currentIndex()
        if index == current:
            return
        if not self.isVisible():
            self.setCurrentIndex(index)
            return

        self._direction = 1 if index > current else -1
        outgoing = self.currentWidget()
        self.setCurrentIndex(index)
        outgoing.show()
        incoming = self.currentWidget()
        incoming.raise_()
        for page in (outgoing, incoming):
            page.setGraphicsEffect(QGraphicsOpacityEffect(page))
        self._pages = (outgoing, incoming)
        self._tick(0.0)
        self._animation.start()

    def _tick(self, value: float) -> None:
        if self._pages is None:
            return
        outgoing, incoming = self._pages
        origin = self.contentsRect().topLeft()
        shift = self._direction * self.OFFSET
        outgoing.move(origin.x() - round(shift * value), origin.y())
        outgoing.graphicsEffect().setOpacity(1 - value)
        incoming.move(origin.x() + round(shift * (1 - value)), origin.y())
        incoming.graphicsEffect().setOpacity(value)

    def _finish(self) -> None:
        self._animation.stop()
        if self._pages is None:
            return
        outgoing, incoming = self._pages
        self._pages = None
        outgoing.hide()
        for page in (outgoing, incoming):
            page.setGraphicsEffect(None)
            page.move(self.contentsRect().topLeft())
