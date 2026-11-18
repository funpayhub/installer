from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMargins, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

from dothub_installer.config import PROXY_RE, TOKEN_RE
from dothub_installer.core.target import Target
from dothub_installer.ui.theme import BLUE
from dothub_installer.ui.widgets.strength import PasswordStrength


class SettingsPage(QWidget):
    """Install directory, bot token and password, proxy and service"""

    browse_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._for_remote: bool | None = None

        self.dir_edit = QLineEdit()
        dir_button = QPushButton("Обзор…")
        # PySide6 can't take a signal as a `clicked=` keyword (it tries to call it), so it is connected explicitly
        dir_button.clicked.connect(self.browse_requested)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(10)
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(dir_button)

        self.token_edit = QLineEdit(
            placeholderText="123456789:AAHg7K...", echoMode=QLineEdit.EchoMode.Password
        )
        token_hint = QLabel(
            f'Токен можно получить у <a style="color: {BLUE}; text-decoration: none" '
            'href="https://t.me/BotFather">@BotFather</a>',
            objectName="hint",
        )
        token_hint.setOpenExternalLinks(True)

        self.password_edit = QLineEdit(
            placeholderText="Придумайте пароль", echoMode=QLineEdit.EchoMode.Password
        )
        self.password_strength = PasswordStrength()
        self.password_edit.textChanged.connect(
            lambda text: self.password_strength.set_password(text.strip())
        )
        self.confirm_edit = QLineEdit(
            placeholderText="Ещё раз", echoMode=QLineEdit.EchoMode.Password
        )
        self.password_edit.textChanged.connect(self._check_confirm)
        self.confirm_edit.textChanged.connect(self._check_confirm)
        password_hint = QLabel(
            "Его нужно будет отправить боту при первом обращении", objectName="hint"
        )

        self.proxy_edit = QLineEdit(
            placeholderText="socks5://user:pass@host:port — необязательно"
        )
        proxy_hint = QLabel(
            "Нужен, если Telegram недоступен с этого компьютера или сервера",
            objectName="hint",
        )

        self.service_check = QCheckBox(
            "Установить как службу systemd (автозапуск и перезапуск при сбоях)"
        )
        self.service_check.setChecked(True)

        form = QFormLayout(self, contentsMargins=QMargins(0, 0, 0, 0))
        form.setVerticalSpacing(8)
        form.setHorizontalSpacing(16)
        form.addRow("Директория установки", dir_row)
        form.addRow("Токен Telegram-бота", self.token_edit)
        form.addRow("", token_hint)
        form.addRow("Пароль для бота", self.password_edit)
        form.addRow("", self.password_strength)
        form.addRow("Повторите пароль", self.confirm_edit)
        form.addRow("", password_hint)
        form.addRow("Прокси для Telegram", self.proxy_edit)
        form.addRow("", proxy_hint)
        form.addRow("", self.service_check)

    @property
    def directory(self) -> str:
        return self.dir_edit.text().strip()

    @property
    def token(self) -> str:
        return self.token_edit.text().strip()

    @property
    def password(self) -> str:
        # Telegram trims messages, so spaces at the ends could never be typed to the bot
        return self.password_edit.text().strip()

    def _check_confirm(self) -> None:
        """Red border on the repeat field while it doesn't match; nothing while it is still empty"""
        confirm = self.confirm_edit.text().strip()
        mismatch = bool(confirm) and confirm != self.password
        if self.confirm_edit.property("error") != mismatch:
            self.confirm_edit.setProperty("error", mismatch)
            self.confirm_edit.style().unpolish(self.confirm_edit)
            self.confirm_edit.style().polish(self.confirm_edit)

    @property
    def proxy(self) -> str:
        return self.proxy_edit.text().strip()

    @property
    def service(self) -> bool:
        return self.service_check.isChecked()

    def prepare(self, target: Target) -> None:
        """Called before the page is shown: resets the default directory when the kind of target changed"""
        if self._for_remote != target.remote:
            self._for_remote = target.remote
            self.dir_edit.setText(
                "~/dothub" if target.remote else str(Path.home() / "dothub")
            )
        self.service_check.setVisible(target.linux)

    def validate(self) -> str | None:
        if not self.directory:
            return "Укажите папку установки"
        if self.proxy and not PROXY_RE.match(self.proxy):
            return "Прокси должен начинаться с socks5://, http:// или https://"
        if not TOKEN_RE.match(self.token):
            return "Это не похоже на токен Telegram-бота"
        if not self.password:
            return "Придумайте пароль для доступа к боту"
        if self.confirm_edit.text().strip() != self.password:
            return "Пароли не совпадают"
        return None
