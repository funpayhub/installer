from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QFrame, QLabel, QVBoxLayout, QWidget

from dothub_installer.core.target import Target
from dothub_installer.ui.theme import GREEN, MUTED


class DonePage(QWidget):
    """Summary of the finished installation"""

    def __init__(self) -> None:
        super().__init__()
        self.label = QLabel(wordWrap=True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        card = QFrame(objectName="infoCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.addWidget(self.label)
        self.start_check = QCheckBox("Запустить .hub")
        self.start_check.setChecked(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(card)
        layout.addSpacing(16)
        layout.addWidget(self.start_check)
        layout.addStretch()

    def fill(
        self, target: Target, install_dir: str, service: str, bot_name: str
    ) -> None:
        rows = [
            ("Куда", f"сервер {target.host}" if target.remote else "этот компьютер"),
            ("Папка", install_dir),
        ]
        if service:
            rows += [
                ("Служба", f"{service} — запущена и стартует вместе с системой"),
                ("Логи", f"journalctl -u {service} -f"),
            ]
        elif target.linux:
            rows.append(("Запуск", f"{install_dir}/start.sh"))
        else:
            rows.append(("Запуск", str(Path(install_dir) / "start.bat")))
        if bot_name:
            rows.append(
                (
                    "Бот",
                    f"@{bot_name} — когда .hub запустится, напишите ему и отправьте пароль",
                )
            )

        self.label.setText(
            f'<p style="font-size: 13pt; font-weight: 700; color: {GREEN}">.hub установлен</p>'
            + "".join(
                f'<p><span style="color: {MUTED}">{name}</span><br>{html.escape(value)}</p>'
                for name, value in rows
            ),
        )
        self.start_check.setVisible(not target.linux)
