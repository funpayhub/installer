from __future__ import annotations

import re
from collections.abc import Callable

ANSI_RE = re.compile(
    r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)|\x1b[@-Z\\-_]"
)


def clean_line(text: str) -> str:
    return ANSI_RE.sub("", text).rstrip("\r").rsplit("\r", 1)[-1]


class StreamFilter:
    def __init__(
        self, on_line: Callable[[str], None], on_marker: Callable[[str, str], None]
    ) -> None:
        self.on_line = on_line
        self.on_marker = on_marker
        self._line = ""  # the current line so far
        self._held = ""  # the part of it that was not passed on yet

    def feed(self, text: str) -> str:
        out = []
        parts = text.split("\n")
        for i, part in enumerate(parts):
            self._line += part
            clean = clean_line(self._line)
            if i == len(parts) - 1:  # no newline yet
                if clean.startswith("@"):
                    self._held += part
                else:
                    out.append(self._held + part)
                    self._held = ""
                continue

            if clean.startswith("@@") and "=" in clean:
                key, value = clean[2:].split("=", 1)
                self.on_marker(key, value)
            else:
                out.append(self._held + part + "\n")
                if clean.strip():
                    self.on_line(clean)
            self._line = self._held = ""
        return "".join(out)
