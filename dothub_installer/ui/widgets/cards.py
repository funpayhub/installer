from __future__ import annotations

from PySide6.QtCore import QMargins, Qt
from PySide6.QtWidgets import QFrame, QLabel, QRadioButton, QVBoxLayout


class OptionCard(QFrame):
    def __init__(self, title: str, description: str) -> None:
        super().__init__(objectName="card", cursor=Qt.CursorShape.PointingHandCursor)
        self.radio = QRadioButton(title, objectName="cardTitle")
        description = QLabel(description, objectName="cardSubtitle", wordWrap=True)
        layout = QVBoxLayout(self, spacing=4, contentsMargins=QMargins(16, 14, 16, 14))
        layout.addWidget(self.radio)
        layout.addWidget(description)
        self.radio.toggled.connect(self._update)

    def mousePressEvent(self, event) -> None:
        self.radio.setChecked(True)

    def _update(self) -> None:
        self.setProperty("checked", self.radio.isChecked())
        self.style().unpolish(self)
        self.style().polish(self)
