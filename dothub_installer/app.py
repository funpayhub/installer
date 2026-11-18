from __future__ import annotations

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from dothub_installer.config import APP_TITLE
from dothub_installer.ui.logo import logo_pixmap
from dothub_installer.ui.theme import apply_theme
from dothub_installer.ui.window import InstallerWindow


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    app.setWindowIcon(QIcon(logo_pixmap(256)))
    app.setApplicationName(APP_TITLE)
    window = InstallerWindow()
    window.show()
    return app.exec()
