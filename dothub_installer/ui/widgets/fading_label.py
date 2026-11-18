from __future__ import annotations

from typing import Any

from PySide6.QtCore import QVariantAnimation
from PySide6.QtWidgets import QGraphicsOpacityEffect, QLabel


class FadingLabel(QLabel):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)
        self._pending = ""
        self._swapped = True
        self._fade = QVariantAnimation(self, startValue=0.0, endValue=1.0, duration=320)
        self._fade.valueChanged.connect(self._tick)

    def fade_to(self, text: str) -> None:
        if text == self._pending:
            return
        self._pending = text
        self._fade.stop()
        if not self.isVisible():
            self.setText(text)
            self._effect.setOpacity(1)
            return
        self._swapped = False
        self._fade.start()

    def _tick(self, value: float) -> None:
        if value < 0.5:
            self._effect.setOpacity(1 - value * 2)
            return
        if not self._swapped:
            self._swapped = True
            self.setText(self._pending)
        self._effect.setOpacity((value - 0.5) * 2)
