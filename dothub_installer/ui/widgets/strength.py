from __future__ import annotations

import math
import string

from PySide6.QtCore import QMargins, QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from dothub_installer.ui.theme import ACCENTS, BORDER, MUTED

COMMON = {
    "password",
    "passw0rd",
    "qwerty",
    "qwertyuiop",
    "asdfgh",
    "zaq12wsx",
    "1q2w3e",
    "1q2w3e4r",
    "qwe123",
    "abc123",
    "admin",
    "letmein",
    "welcome",
    "iloveyou",
    "monkey",
    "dragon",
    "football",
    "пароль",
    "йцукен",
    "123456",
    "12345678",
    "123456789",
    "1234567890",
    "111111",
    "000000",
    "dothub",
    "funpay",
    "funpayhub",
    "telegram",
}

LEVELS = list(
    zip(
        ["Слабый пароль", "Средний пароль", "Хороший пароль", "Надёжный пароль"],
        ACCENTS,
    )
)


def password_strength(password: str) -> int:
    if not password:
        return 0
    lowered = password.lower()
    if (
        lowered in COMMON
        or lowered.rstrip(string.digits + string.punctuation) in COMMON
        or len(set(password)) < 3
    ):
        return 1

    pool = 0
    for kind in (str.islower, str.isupper):
        letters = [c for c in password if kind(c)]
        pool += (
            26
            if letters and all(c.isascii() for c in letters)
            else 33
            if letters
            else 0
        )
    pool += 10 if any(c.isdigit() for c in password) else 0
    pool += 33 if any(not c.isalnum() for c in password) else 0

    length = 1.0
    for previous, char in zip(password, password[1:]):
        length += 0.25 if abs(ord(char) - ord(previous)) <= 1 else 1
    bits = length * math.log2(pool)
    return 1 if bits < 30 else 2 if bits < 45 else 3 if bits < 60 else 4


class PasswordStrength(QWidget):
    SEGMENTS = 4
    SEGMENT_WIDTH = 26
    GAP = 4

    def __init__(self) -> None:
        super().__init__()
        self.level = 0
        self.joke = False  # the password is literally "пароль": no bar, just a clown
        self._bar_margin = QMargins(
            self.SEGMENTS * self.SEGMENT_WIDTH + (self.SEGMENTS - 1) * self.GAP + 10,
            0,
            0,
            0,
        )
        self.label = QLabel(objectName="hint")
        self._layout = QHBoxLayout(self, contentsMargins=self._bar_margin)
        self._layout.addWidget(self.label)
        self.set_password("")

    def set_password(self, password: str) -> None:
        self.level = password_strength(password)
        self.joke = password.lower() == "пароль"
        self._layout.setContentsMargins(QMargins() if self.joke else self._bar_margin)
        if self.joke:
            self.label.setText("🤡 очень смешно")
            self.label.setStyleSheet(f"color: {MUTED}")
        elif self.level:
            text, color = LEVELS[self.level - 1]
            self.label.setText(text)
            self.label.setStyleSheet(f"color: {color}")
        else:
            self.label.setText("Надёжность пароля")
            self.label.setStyleSheet(f"color: {MUTED}")
        self.update()

    def paintEvent(self, event) -> None:
        if self.joke:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        lit = QColor(LEVELS[self.level - 1][1]) if self.level else QColor(BORDER)
        top = (self.height() - 4) / 2
        for i in range(self.SEGMENTS):
            painter.setBrush(lit if i < self.level else QColor(BORDER))
            painter.drawRoundedRect(
                QRectF(i * (self.SEGMENT_WIDTH + self.GAP), top, self.SEGMENT_WIDTH, 4),
                2,
                2,
            )
        painter.end()
