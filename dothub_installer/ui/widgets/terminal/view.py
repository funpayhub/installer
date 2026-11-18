from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QFont, QFontMetricsF, QPainter
from PySide6.QtWidgets import QAbstractScrollArea, QApplication, QMenu

from dothub_installer.ui.widgets.terminal.colors import BACKGROUND, FOREGROUND, resolve
from dothub_installer.ui.widgets.terminal.screen import Screen

MARGIN = 6


class TerminalView(QAbstractScrollArea):
    """Read-only terminal: colors, progress bars redrawn with \\r and cursor movement, scrollback"""

    size_changed = Signal(
        int, int
    )  # rows, columns: the pty of the process has to follow

    def __init__(self) -> None:
        super().__init__(objectName="terminal")
        font = QFont()
        font.setFamilies(["Cascadia Mono", "Consolas", "DejaVu Sans Mono", "monospace"])
        font.setStyleHint(QFont.StyleHint.Monospace)
        font.setPointSizeF(9.5)
        self.setFont(font)
        metrics = QFontMetricsF(font)
        self.cell_width = metrics.horizontalAdvance("M")
        self.cell_height = metrics.lineSpacing()
        self.ascent = metrics.ascent()

        rows, columns = self.terminal_size()
        self.screen = Screen(rows, columns)
        self._follow = True
        self._size = (rows, columns)
        self._dirty = QTimer(self, interval=33, singleShot=True, timeout=self._refresh)
        self._resized = QTimer(
            self, interval=150, singleShot=True, timeout=self._apply_size
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        self.verticalScrollBar().valueChanged.connect(self._on_scroll)

    def terminal_size(self) -> tuple[int, int]:
        viewport = self.viewport().size()
        return (
            max(10, int((viewport.height() - 2 * MARGIN) / self.cell_height)),
            max(40, int((viewport.width() - 2 * MARGIN) / self.cell_width)),
        )

    def feed(self, data: bytes) -> None:
        self.screen.feed(data)
        if not self._dirty.isActive():
            self._dirty.start()

    def clear(self) -> None:
        self.screen.reset()
        self._follow = True
        self._refresh()

    def plain_text(self) -> str:
        return self.screen.plain_text()

    def _visible_rows(self) -> int:
        return int((self.viewport().height() - 2 * MARGIN) / self.cell_height)

    def _refresh(self) -> None:
        bar = self.verticalScrollBar()
        bar.blockSignals(True)
        bar.setRange(0, max(0, len(self.screen) - self._visible_rows()))
        bar.setPageStep(self._visible_rows())
        if self._follow:
            bar.setValue(bar.maximum())
        bar.blockSignals(False)
        self.viewport().update()

    def _on_scroll(self, value: int) -> None:
        self._follow = value >= self.verticalScrollBar().maximum()
        self.viewport().update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._refresh()
        self._resized.start()

    def _apply_size(self) -> None:
        size = self.terminal_size()
        if size != self._size:
            self._size = size
            self.screen.resize(*size)
            self._refresh()
            self.size_changed.emit(*size)

    def paintEvent(self, event) -> None:
        painter = QPainter(self.viewport())
        painter.fillRect(self.viewport().rect(), BACKGROUND)
        painter.setFont(self.font())

        first = self.verticalScrollBar().value()
        count = len(self.screen)
        for index in range(first, min(count, first + self._visible_rows() + 1)):
            top = MARGIN + (index - first) * self.cell_height
            for segment in self.screen.segments(index):
                style = segment.style
                fg, bg = resolve(style.fg, FOREGROUND), resolve(style.bg, BACKGROUND)
                if style.reverse:
                    fg, bg = bg, fg
                left = MARGIN + segment.column * self.cell_width
                width = segment.width * self.cell_width
                if bg != BACKGROUND:
                    painter.fillRect(QRectF(left, top, width, self.cell_height), bg)

                font = painter.font()
                font.setBold(style.bold)
                font.setUnderline(style.underline)
                painter.setFont(font)
                painter.setPen(fg)
                baseline = top + self.ascent
                if segment.text.isascii():
                    painter.drawText(
                        QRectF(left, top, width, self.cell_height),
                        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                        segment.text,
                    )
                else:  # fallback fonts have other widths: a wide character takes two cells
                    painter.drawText(
                        QRectF(left, baseline - self.ascent, width, self.cell_height),
                        Qt.AlignmentFlag.AlignCenter,
                        segment.text,
                    )
        painter.end()

    def _menu(self, position) -> None:
        menu = QMenu(self)
        copy = QAction("Копировать всё", menu)
        copy.triggered.connect(
            lambda: QApplication.clipboard().setText(self.plain_text())
        )
        menu.addAction(copy)
        menu.exec(self.viewport().mapToGlobal(position))
