from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dothub_installer.config import IS_ROOT, IS_WINDOWS
from dothub_installer.core.target import Target
from dothub_installer.ui.widgets.cards import OptionCard


class TargetPage(QWidget):
    """Where to install: this computer or a server over SSH"""

    def __init__(self) -> None:
        super().__init__()
        local_card = OptionCard(
            "Этот компьютер", "Windows или Linux, на котором открыт установщик"
        )
        remote_card = OptionCard(
            "Сервер по SSH", "Linux-сервер: Arch, Debian или Ubuntu"
        )
        self.local_radio = local_card.radio
        self.remote_radio = remote_card.radio
        group = QButtonGroup(self)
        group.addButton(self.local_radio)
        group.addButton(self.remote_radio)
        self.local_radio.setChecked(True)
        self.remote_radio.toggled.connect(self._update)
        cards = QHBoxLayout(spacing=14)
        cards.addWidget(local_card)
        cards.addWidget(remote_card)

        self.ssh_host = QLineEdit(placeholderText="1.2.3.4 или example.com")
        self.ssh_port = QLineEdit("22")
        self.ssh_port.setValidator(QIntValidator(1, 65535, self.ssh_port))
        self.ssh_port.setFixedWidth(76)
        self.ssh_user = QLineEdit("root")
        self.ssh_password = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.ssh_key = QLineEdit(placeholderText="Необязательно")
        key_button = QPushButton("Обзор…")
        key_button.clicked.connect(self._choose_key)

        host_row = QHBoxLayout()
        host_row.setSpacing(10)
        host_row.addWidget(self.ssh_host, 1)
        host_row.addSpacing(6)
        host_row.addWidget(QLabel("Порт"))
        host_row.addWidget(self.ssh_port)
        key_row = QHBoxLayout()
        key_row.setSpacing(10)
        key_row.addWidget(self.ssh_key, 1)
        key_row.addWidget(key_button)

        self.ssh_box = QWidget()
        ssh_form = QFormLayout(self.ssh_box)
        ssh_form.setContentsMargins(0, 0, 0, 0)
        ssh_form.setVerticalSpacing(10)
        ssh_form.setHorizontalSpacing(16)
        ssh_form.addRow("Сервер", host_row)
        ssh_form.addRow("Пользователь", self.ssh_user)
        ssh_form.addRow("Пароль", self.ssh_password)
        ssh_form.addRow("SSH-ключ", key_row)

        self.sudo_password = QLineEdit(echoMode=QLineEdit.EchoMode.Password)
        self.sudo_hint = QLabel(objectName="hint", wordWrap=True)
        self.sudo_box = QWidget()
        sudo_form = QFormLayout(self.sudo_box)
        sudo_form.setContentsMargins(0, 0, 0, 0)
        sudo_form.setVerticalSpacing(6)
        sudo_form.setHorizontalSpacing(16)
        sudo_form.addRow("Пароль sudo", self.sudo_password)
        sudo_form.addRow("", self.sudo_hint)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addLayout(cards)
        layout.addWidget(self.ssh_box)
        layout.addWidget(self.sudo_box)
        layout.addStretch()
        self._update()

    def target(self) -> Target:
        if not self.remote_radio.isChecked():
            return Target(sudo_password=self.sudo_password.text())
        return Target(
            host=self.ssh_host.text().strip(),
            port=int(self.ssh_port.text() or 22),
            user=self.ssh_user.text().strip(),
            password=self.ssh_password.text(),
            key_file=self.ssh_key.text().strip(),
            sudo_password=self.sudo_password.text() or self.ssh_password.text(),
        )

    def validate(self) -> str | None:
        if not self.remote_radio.isChecked():
            return None
        if not self.ssh_host.text().strip():
            return "Укажите адрес сервера"
        if not 1 <= int(self.ssh_port.text() or 22) <= 65535:
            return "Порт должен быть от 1 до 65535"
        if not self.ssh_user.text().strip():
            return "Укажите пользователя"
        key = self.ssh_key.text().strip()
        if key and not Path(key).is_file():
            return "Файл SSH-ключа не найден"
        return None

    def _update(self) -> None:
        remote = self.remote_radio.isChecked()
        self.ssh_box.setVisible(remote)
        self.sudo_box.setVisible(remote or (not IS_WINDOWS and not IS_ROOT))
        self.sudo_hint.setText(
            "Нужен, если пользователь не root и для установки пакетов нужны права администратора. "
            "Если не указан, используется пароль SSH"
            if remote
            else "Нужен для установки git и curl, если их ещё нет",
        )

    def _choose_key(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "SSH-ключ", str(Path.home() / ".ssh")
        )
        if path:
            self.ssh_key.setText(path)
