from __future__ import annotations

from dataclasses import dataclass

import pyte
from wcwidth import wcwidth


@dataclass(frozen=True)
class Style:
    fg: str = "default"
    bg: str = "default"
    bold: bool = False
    underline: bool = False
    reverse: bool = False


@dataclass(frozen=True)
class Segment:
    column: int
    text: str
    width: int  # in cells
    style: Style


class Screen:
    """Terminal emulator: turns the byte stream of a process into rows of styled text, with scrollback"""

    def __init__(self, rows: int = 30, columns: int = 100, history: int = 5000) -> None:
        self._screen = pyte.HistoryScreen(columns, rows, history=history, ratio=1)
        self._stream = pyte.ByteStream(self._screen)

    @property
    def columns(self) -> int:
        return self._screen.columns

    def feed(self, data: bytes) -> None:
        self._stream.feed(data)

    def resize(self, rows: int, columns: int) -> None:
        self._screen.resize(rows, columns)

    def reset(self) -> None:
        self._screen.reset()
        self._screen.history.top.clear()

    def _used_rows(self) -> int:
        """Rows of the live screen up to the last one with text or the cursor, so the view grows like a log"""
        screen = self._screen
        last = screen.cursor.y
        for y in sorted(screen.buffer, reverse=True):
            if y > last and any(
                char.data.strip() for char in screen.buffer[y].values()
            ):
                last = y
                break
        return last + 1

    def __len__(self) -> int:
        return len(self._screen.history.top) + self._used_rows()

    def segments(self, index: int) -> list[Segment]:
        history = self._screen.history.top
        row = (
            history[index]
            if index < len(history)
            else self._screen.buffer[index - len(history)]
        )

        segments: list[Segment] = []
        for column in range(self._screen.columns):
            char = row[column]
            if not char.data:  # the second half of a wide character
                continue
            style = Style(char.fg, char.bg, char.bold, char.underscore, char.reverse)
            width = max(1, wcwidth(char.data))
            last = segments[-1] if segments else None
            if (
                last
                and char.data.isascii()
                and last.text.isascii()
                and last.style == style
                and last.column + last.width == column
            ):
                segments[-1] = Segment(
                    last.column, last.text + char.data, last.width + width, style
                )
            else:
                segments.append(Segment(column, char.data, width, style))

        while (
            segments
            and not segments[-1].text.strip()
            and segments[-1].style.bg == "default"
            and not segments[-1].style.reverse
        ):
            segments.pop()  # trailing blanks have nothing to draw
        return segments

    def plain_text(self) -> str:
        lines = []
        for index in range(len(self)):
            line, column = "", 0
            for segment in self.segments(index):
                line += " " * (segment.column - column) + segment.text
                column = segment.column + segment.width
            lines.append(line.rstrip())
        return "\n".join(lines).rstrip() + "\n"
