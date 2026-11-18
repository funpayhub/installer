from __future__ import annotations

import posixpath
import stat

import paramiko
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QInputDialog,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStyle,
    QVBoxLayout,
    QWidget,
)

from dothub_installer.config import APP_TITLE, KNOWN_HOSTS
from dothub_installer.core.target import Target


class RemoteDirDialog(QDialog):
    def __init__(self, parent: QWidget, sftp: paramiko.SFTPClient, start: str) -> None:
        super().__init__(parent)
        self.setWindowTitle("Выберите директорию установки")
        self.resize(520, 420)
        self.sftp = sftp
        self.path = "/"

        self.path_edit = QLineEdit()
        self.path_edit.returnPressed.connect(
            lambda: self.go(self.path_edit.text().strip())
        )
        up_button = QPushButton(
            icon=self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent),
            toolTip="Наверх",
            clicked=lambda: self.go(posixpath.dirname(self.path)),
        )
        new_button = QPushButton(
            icon=self.style().standardIcon(
                QStyle.StandardPixmap.SP_FileDialogNewFolder
            ),
            toolTip="Новая директория",
            clicked=self.new_folder,
        )

        self.folders = QListWidget()
        self.folders.itemDoubleClicked.connect(
            lambda item: self.go(self.child(item.text()))
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Выбрать")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Отмена")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        top = QHBoxLayout()
        top.addWidget(self.path_edit, 1)
        top.addWidget(up_button)
        top.addWidget(new_button)
        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.folders, 1)
        layout.addWidget(buttons)

        home = sftp.normalize(".")
        start = (
            home + start[1:] if start.startswith("~") else posixpath.join(home, start)
        )
        while not self.go(start, quiet=True) and start != "/":
            start = posixpath.dirname(start)

    def child(self, name: str) -> str:
        return posixpath.join(self.path, name)

    def go(self, path: str, quiet: bool = False) -> bool:
        try:
            path = self.sftp.normalize(path or "/")
            entries = self.sftp.listdir_attr(path)
        except OSError as e:
            if not quiet:
                QMessageBox.warning(self, APP_TITLE, f"Не удалось открыть {path}: {e}")
            return False

        self.path = path
        self.path_edit.setText(path)
        self.folders.clear()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        names = sorted(
            (
                i.filename
                for i in entries
                if stat.S_ISDIR(i.st_mode or 0) and not i.filename.startswith(".")
            ),
            key=str.lower,
        )
        for name in names:
            self.folders.addItem(QListWidgetItem(icon, name))
        return True

    def new_folder(self) -> None:
        name, ok = QInputDialog.getText(self, "Новая папка", "Имя папки")
        name = name.strip()
        if not ok or not name:
            return
        try:
            self.sftp.mkdir(self.child(name))
        except OSError as e:
            QMessageBox.warning(self, APP_TITLE, f"Не удалось создать папку: {e}")
            return
        self.go(self.path)
        for item in self.folders.findItems(name, Qt.MatchFlag.MatchExactly):
            self.folders.setCurrentItem(item)

    def selected_path(self) -> str:
        item = self.folders.currentItem()
        return (
            self.child(item.text())
            if item is not None and item.isSelected()
            else self.path
        )


def confirm_replace_host_key(
    parent: QWidget, target: Target, error: paramiko.BadHostKeyException
) -> tuple[bool, str]:
    box = QMessageBox(parent, icon=QMessageBox.Icon.Warning, windowTitle=APP_TITLE)
    box.setStyleSheet("QLabel#qt_msgbox_informativelabel { min-width: 440px; }")
    box.setText(f"<b>Ключ сервера {target.host} не совпадает с сохранённым!</b>")
    box.setInformativeText(
        "Так бывает, если на сервере переустановили ОС или сменили SSH ключ. "
        "Но это также может значить, что кто-то перехватывает подключение.<br><br>"
        f"Сохранённый ключ:<br>{error.expected_key.get_name()} {error.expected_key.fingerprint}<br>"
        f"Ключ сервера:<br>{error.key.get_name()} {error.key.fingerprint}<br><br>"
        "Если вы переустанавливали ОС на сервере, замените сохраненный ключ. "
        'Если нет - <span style="color: red"><b>бегите</b></span>.',
    )
    replace = box.addButton("Заменить ключ", QMessageBox.ButtonRole.DestructiveRole)
    replace.setObjectName("danger")
    cancel = box.addButton("Отмена", QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(cancel)
    box.exec()

    if box.clickedButton() is not replace:
        return False, "Подключение отменено: ключ сервера не совпадает с сохранённым"
    try:
        target.replace_host_key(error.key)
    except OSError as e:
        return False, f"Не удалось заменить ключ в {KNOWN_HOSTS}: {e}"
    return True, "Ключ сервера заменён"
