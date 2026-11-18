from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from dothub_installer.ui.widgets.terminal import TerminalView


class InstallPage(QWidget):
    """The terminal with the live output of the install script"""

    def __init__(self) -> None:
        super().__init__()
        self.terminal = TerminalView()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.terminal, 1)

    def start(self) -> None:
        self.terminal.clear()
