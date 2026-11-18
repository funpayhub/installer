from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# install.sh / install.ps1 live next to the package (or in the PyInstaller bundle)
RESOURCES = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
IS_WINDOWS = sys.platform == "win32"
IS_ROOT = not IS_WINDOWS and os.geteuid() == 0
REMOTE_SCRIPT = ".dothub-install.sh"
KNOWN_HOSTS = Path.home() / ".ssh" / "known_hosts"
APP_TITLE = "Установщик .hub"
GITHUB_URL = "https://github.com/funpayhub/funpayhub"
TELEGRAM_URL = "https://t.me/funpayhub"

TOKEN_RE = re.compile(r"^\d+:[A-Za-z0-9_-]+$")
PROXY_RE = re.compile(r"^(socks5|http|https)://.+")
KAOMOJI_RE = re.compile(r"^\(\S+?\)\s+")

CHECK_ERRORS = {
    10: "Не удалось подключиться к Telegram через этот прокси",
    11: "Telegram не принял токен, проверьте его",
    12: "Не удалось подключиться к Telegram. Возможно, нужен прокси",
}
