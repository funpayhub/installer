from __future__ import annotations

import os
from pathlib import Path

import paramiko
from PySide6.QtCore import QEasingCurve, QMargins, Qt, QUrl, QVariantAnimation
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dothub_installer.config import (
    APP_TITLE,
    CHECK_ERRORS,
    GITHUB_URL,
    KAOMOJI_RE,
    TELEGRAM_URL,
)
from dothub_installer.core.runner import Runner
from dothub_installer.core.script import script_args
from dothub_installer.core.target import Target
from dothub_installer.ui.dialogs import RemoteDirDialog, confirm_replace_host_key
from dothub_installer.ui.logo import LogoWidget
from dothub_installer.ui.pages import (
    PAGE_DONE,
    PAGE_INSTALL,
    PAGE_SETTINGS,
    PAGE_SUBTITLES,
    PAGE_TARGET,
    PAGE_TITLES,
    STEP_TITLES,
)
from dothub_installer.ui.pages.done import DonePage
from dothub_installer.ui.pages.install import InstallPage
from dothub_installer.ui.pages.settings import SettingsPage
from dothub_installer.ui.pages.target import TargetPage
from dothub_installer.ui.theme import ERROR, MUTED
from dothub_installer.ui.widgets.backdrop import Backdrop
from dothub_installer.ui.widgets.confetti import Confetti
from dothub_installer.ui.widgets.fading_label import FadingLabel
from dothub_installer.ui.widgets.links import LinkButton
from dothub_installer.ui.widgets.stack import AnimatedStack
from dothub_installer.ui.widgets.steps import AccentStripe, StepList


class InstallerWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(windowTitle=APP_TITLE)
        self.resize(900, 620)

        self.runner: Runner | None = None
        self.bot_name = ""
        self.install_dir = ""
        self.service = ""
        self.position = 0.0

        self.title = FadingLabel(objectName="title")
        self.subtitle = FadingLabel(objectName="subtitle")
        self.stripe = AccentStripe()

        self.target_page = TargetPage()
        self.settings_page = SettingsPage()
        self.settings_page.browse_requested.connect(self._choose_dir)
        self.install_page = InstallPage()
        self.done_page = DonePage()
        self.pages = AnimatedStack()
        for page in (
            self.target_page,
            self.settings_page,
            self.install_page,
            self.done_page,
        ):
            self.pages.addWidget(page)

        self.status = QLabel(wordWrap=True)
        self.back_button = QPushButton("Назад", clicked=self.back)
        self.next_button = QPushButton("Далее", objectName="primary", clicked=self.next)
        self.next_button.setDefault(True)
        self.star_button = QPushButton(
            "⭐ Поставить звезду", objectName="star", clicked=self._open_github
        )
        self.star_button.setCursor(Qt.CursorShape.PointingHandCursor)

        buttons = QHBoxLayout(spacing=10)
        buttons.addWidget(self.status, 1)
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.star_button)
        buttons.addWidget(self.next_button)

        self.backdrop = Backdrop()
        content_layout = QVBoxLayout(
            self.backdrop, spacing=0, contentsMargins=QMargins(36, 30, 36, 24)
        )
        content_layout.addWidget(self.title)
        content_layout.addSpacing(4)
        content_layout.addWidget(self.subtitle)
        content_layout.addSpacing(14)
        content_layout.addWidget(self.stripe, alignment=Qt.AlignmentFlag.AlignLeft)
        content_layout.addSpacing(24)
        content_layout.addWidget(self.pages, 1)
        content_layout.addSpacing(16)
        content_layout.addLayout(buttons)

        logo = LogoWidget()
        logo.setFixedHeight(120)
        self.steps = StepList(STEP_TITLES)
        sidebar = QFrame(objectName="sidebar")
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar, contentsMargins=QMargins(26, 30, 26, 26))
        links = QHBoxLayout(spacing=18)
        links.addStretch()
        links.addWidget(LinkButton("GitHub", GITHUB_URL, "github"))
        links.addWidget(LinkButton("Telegram", TELEGRAM_URL, "telegram"))
        links.addStretch()
        sidebar_layout.addWidget(logo)
        sidebar_layout.addSpacing(10)
        sidebar_layout.addLayout(links)
        sidebar_layout.addSpacing(34)
        sidebar_layout.addWidget(self.steps)
        sidebar_layout.addStretch()

        layout = QHBoxLayout(self, spacing=0, contentsMargins=QMargins(0, 0, 0, 0))
        layout.addWidget(sidebar)
        layout.addWidget(self.backdrop, 1)

        self.install_page.terminal.size_changed.connect(self._on_terminal_resized)
        self.confetti = Confetti(self)
        self._position_animation = QVariantAnimation(
            self, easingCurve=QEasingCurve.Type.InOutCubic
        )
        self._position_animation.valueChanged.connect(self._set_position)

        self.show_page(PAGE_TARGET)

    # ---------- navigation ----------

    def _set_position(self, position: float) -> None:
        self.position = position
        self.steps.set_position(position)
        self.stripe.set_position(position)
        self.backdrop.set_position(position)

    def _go_to_step(self, index: int) -> None:
        self._position_animation.stop()
        if not self.isVisible():
            self._set_position(float(index))
            return
        self._position_animation.setStartValue(self.position)
        self._position_animation.setEndValue(float(index))
        self._position_animation.setDuration(
            int(450 + 150 * abs(index - self.position))
        )
        self._position_animation.start()

    def show_page(self, index: int) -> None:
        self.pages.slide_to(index)
        self.title.fade_to(PAGE_TITLES[index])
        self.subtitle.fade_to(PAGE_SUBTITLES[index])
        self._go_to_step(index)
        self.steps.set_pulse(index == PAGE_INSTALL)
        if index == PAGE_DONE:
            self.confetti.burst()
        self.set_status("")
        self.back_button.setVisible(index in (PAGE_SETTINGS, PAGE_INSTALL))
        self.star_button.setVisible(index == PAGE_DONE)
        self.next_button.setText("Готово" if index == PAGE_DONE else "Далее")
        self.set_busy(False)

    def back(self) -> None:
        self.show_page(self.pages.currentIndex() - 1)

    def next(self) -> None:
        index = self.pages.currentIndex()
        if index == PAGE_TARGET:
            if error := self.target_page.validate():
                self.set_status(error, error=True)
                return
            self.settings_page.prepare(self.target())
            self.show_page(PAGE_SETTINGS)
        elif index == PAGE_SETTINGS:
            if error := self.settings_page.validate():
                self.set_status(error, error=True)
                return
            self._start(check=True)
        elif index == PAGE_INSTALL:
            self._start(check=False)
        else:
            if not self.target().linux and self.done_page.start_check.isChecked():
                os.startfile(Path(self.install_dir) / "start.bat")  # type: ignore[attr-defined]
            self.close()

    @staticmethod
    def _open_github() -> None:
        QDesktopServices.openUrl(QUrl(GITHUB_URL))

    def set_busy(self, busy: bool) -> None:
        self.back_button.setEnabled(not busy)
        self.next_button.setEnabled(not busy)
        self.pages.currentWidget().setEnabled(
            not busy or self.pages.currentIndex() == PAGE_INSTALL
        )

    def set_status(self, text: str, error: bool = False) -> None:
        self.status.setText(KAOMOJI_RE.sub("", text))
        self.status.setStyleSheet(f"color: {ERROR}" if error else f"color: {MUTED}")

    def target(self) -> Target:
        return self.target_page.target()

    # ---------- ssh ----------

    def _choose_dir(self) -> None:
        edit = self.settings_page.dir_edit
        target = self.target()
        if not target.remote:
            path = QFileDialog.getExistingDirectory(
                self, "Папка установки", edit.text()
            )
            if path:
                edit.setText(str(Path(path)))
            return

        client = self._connect(target)
        if client is None:
            return
        try:
            dialog = RemoteDirDialog(self, client.open_sftp(), edit.text().strip())
            if dialog.exec() == QDialog.DialogCode.Accepted:
                edit.setText(dialog.selected_path())
        finally:
            client.close()

    def _connect(self, target: Target) -> paramiko.SSHClient | None:
        while True:
            self.set_status(f"Подключаюсь к {target.host}…")
            QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
            try:
                client = target.connect()
                self.set_status("")
                return client
            except paramiko.BadHostKeyException as e:
                bad_key = e
            except paramiko.AuthenticationException:
                self.set_status(
                    "Не удалось войти на сервер: неверный пользователь, пароль или ключ",
                    error=True,
                )
                return None
            except Exception as e:
                self.set_status(f"Не удалось подключиться к серверу: {e}", error=True)
                return None
            finally:
                QApplication.restoreOverrideCursor()

            if not self._replace_host_key(target, bad_key):
                return None

    def _replace_host_key(
        self, target: Target, error: paramiko.BadHostKeyException
    ) -> bool:
        replaced, message = confirm_replace_host_key(self, target, error)
        self.set_status(message, error=not replaced)
        return replaced

    # ---------- running the script ----------

    def _start(self, check: bool) -> None:
        target = self.target()
        settings = self.settings_page
        args = script_args(
            target,
            token=settings.token,
            password=settings.password,
            directory=settings.directory,
            proxy=settings.proxy,
            service=settings.service,
            check=check,
        )
        stdin = (target.sudo_password + "\n").encode() if target.linux else b""
        self.runner = Runner(
            target, args, stdin, self.install_page.terminal.terminal_size()
        )
        if check:
            self.set_status("Проверяю настройки…")
            self.runner.output.connect(self._on_check_output)
            self.runner.finished.connect(self._on_check_finished)
        else:
            self.install_page.start()
            self.set_status("Устанавливаю, это может занять несколько минут")
            self.runner.data.connect(self.install_page.terminal.feed)
            self.runner.finished.connect(self._on_install_finished)
        self.set_busy(True)
        self.runner.start()

    def _on_terminal_resized(self, rows: int, columns: int) -> None:
        if self.runner is not None:
            self.runner.resize(rows, columns)

    def _on_check_output(self, line: str) -> None:
        if line.strip():
            self.set_status(line)

    def _on_check_finished(self) -> None:
        assert self.runner is not None
        runner, self.runner = self.runner, None
        runner.wait()
        self.set_busy(False)
        if runner.bad_host_key is not None:
            if self._replace_host_key(runner.target, runner.bad_host_key):
                self._start(check=True)
            return
        if runner.code != 0:
            self.set_status(
                CHECK_ERRORS.get(runner.code)
                or runner.last_line
                or "Проверка не удалась",
                error=True,
            )
            return

        self.bot_name = runner.markers.get("BOT", "")
        state = runner.markers.get("DIR_STATE")
        if state in ("installed", "notempty"):
            text = (
                ".hub уже установлен в этой папке"
                if state == "installed"
                else "Папка установки не пустая"
            )
            answer = QMessageBox.question(
                self, APP_TITLE, f"{text}. Всё равно установить сюда?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                self.set_status("")
                return

        self.show_page(PAGE_INSTALL)
        self._start(check=False)

    def _on_install_finished(self) -> None:
        assert self.runner is not None
        runner, self.runner = self.runner, None
        runner.wait()
        self.set_busy(False)
        if runner.bad_host_key is not None and self._replace_host_key(
            runner.target, runner.bad_host_key
        ):
            self._start(check=False)
            return
        if runner.code != 0:
            self.next_button.setText("Повторить")
            if runner.bad_host_key is None:
                self.set_status(
                    "Установка не удалась, подробности в журнале", error=True
                )
            return

        self.install_dir = runner.markers.get("DIR", self.settings_page.directory)
        self.service = runner.markers.get("SERVICE", "")
        self.done_page.fill(
            self.target(), self.install_dir, self.service, self.bot_name
        )
        self.show_page(PAGE_DONE)

    def closeEvent(self, event) -> None:
        if self.runner is not None and self.runner.isRunning():
            answer = QMessageBox.question(
                self, APP_TITLE, "Установка ещё идёт. Прервать её и закрыть установщик?"
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.runner.stop()
            self.runner.wait(5000)
        event.accept()
