from __future__ import annotations

import codecs
import os
import select
import shlex
import subprocess

import paramiko
from PySide6.QtCore import QThread, Signal

from dothub_installer.config import IS_WINDOWS, REMOTE_SCRIPT, RESOURCES
from dothub_installer.core.stream import StreamFilter
from dothub_installer.core.target import Target

TERM = "xterm-256color"


class Runner(QThread):
    output = Signal(str)  # finished lines without escape codes: for the status line
    data = Signal(bytes)  # everything the terminal should show

    def __init__(
        self,
        target: Target,
        args: list[str],
        stdin: bytes,
        size: tuple[int, int] = (30, 100),
    ) -> None:
        super().__init__()
        self.target = target
        self.args = args
        self.stdin = stdin
        self.size = size  # rows, columns
        self.code = -1
        self.markers: dict[str, str] = {}
        self.last_line = ""
        self.bad_host_key: paramiko.BadHostKeyException | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._client: paramiko.SSHClient | None = None
        self._channel: paramiko.Channel | None = None
        self._pty_master: int | None = None
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self._filter = StreamFilter(self._on_line, self.markers.__setitem__)
        self._cooked = False  # a pipe, not a terminal: lines end with \n only

    def run(self) -> None:
        try:
            self.code = self._run_ssh() if self.target.remote else self._run_local()
        except paramiko.BadHostKeyException as e:
            self.bad_host_key = e
            self._say("(x_x) Ключ сервера не совпадает с сохранённым")
        except paramiko.AuthenticationException:
            self._say(
                "(x_x) Не удалось войти на сервер: неверный пользователь, пароль или ключ"
            )
        except Exception as e:
            self._say(f"(x_x) Ошибка: {e}")

    def stop(self) -> None:
        if self._process is not None:
            self._process.kill()
        if self._client is not None:
            self._client.close()

    def resize(self, rows: int, columns: int) -> None:
        """The terminal widget changed its size"""
        self.size = (rows, columns)
        if self._pty_master is not None:
            self._set_pty_size(self._pty_master)
        if self._channel is not None:
            self._channel.resize_pty(width=columns, height=rows)

    # ---------- output ----------

    def _say(self, text: str) -> None:
        """A line of our own, not from the script"""
        self._feed((text + "\r\n").encode())

    def _feed(self, raw: bytes) -> None:
        text = self._filter.feed(self._decoder.decode(raw))
        if self._cooked:
            text = text.replace("\n", "\r\n")
        if text:
            self.data.emit(text.encode())

    def _on_line(self, line: str) -> None:
        self.last_line = line
        self.output.emit(line)

    # ---------- local ----------

    def _command(self) -> list[str]:
        if IS_WINDOWS:
            script = RESOURCES / "install.ps1"
            command = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ]
        else:
            command = ["bash", str(RESOURCES / "install.sh")]
        return [*command, *self.args]

    def _run_local(self) -> int:
        if IS_WINDOWS:
            return self._run_pipe()
        import pty

        master, slave = pty.openpty()
        self._set_pty_size(master)
        # The script reads the sudo password from the stdin pipe, the pty is only stdout and stderr:
        # nothing gets echoed back and `-t 1` checks in the script see a terminal
        self._process = subprocess.Popen(
            self._command(),
            stdin=subprocess.PIPE,
            stdout=slave,
            stderr=slave,
            env={**os.environ, "TERM": TERM},
        )
        os.close(slave)
        self._pty_master = master
        try:
            assert self._process.stdin is not None
            self._process.stdin.write(self.stdin)
            self._process.stdin.close()
            while True:
                ready, _, _ = select.select([master], [], [], 0.2)
                if ready:
                    try:
                        chunk = os.read(master, 4096)
                    except OSError:  # EIO: the other end is closed
                        break
                    if not chunk:
                        break
                    self._feed(chunk)
                elif self._process.poll() is not None:
                    break
            return self._process.wait()
        finally:
            self._pty_master = None
            os.close(master)

    def _set_pty_size(self, fd: int) -> None:
        import fcntl
        import struct
        import termios

        rows, columns = self.size
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))

    def _run_pipe(self) -> int:
        self._cooked = True
        self._process = subprocess.Popen(
            self._command(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        assert self._process.stdin is not None and self._process.stdout is not None
        self._process.stdin.write(self.stdin)
        self._process.stdin.close()
        while chunk := self._process.stdout.read1(4096):
            self._feed(chunk)
        return self._process.wait()

    # ---------- ssh ----------

    def _run_ssh(self) -> int:
        t = self.target
        self._say(f"(・ω・) Подключаюсь к {t.user}@{t.host}:{t.port}")
        self._client = client = t.connect()
        try:
            with client.open_sftp() as sftp:
                sftp.put(str(RESOURCES / "install.sh"), REMOTE_SCRIPT)

            transport = client.get_transport()
            assert transport is not None
            rows, columns = self.size
            self._channel = channel = transport.open_session()
            channel.get_pty(term=TERM, width=columns, height=rows)
            channel.settimeout(0.2)
            # Here stdin is the terminal too, so its echo is turned off first and the password is sent only
            # when the shell says it is ready: otherwise the password would be shown in the log
            channel.exec_command(
                f"stty -echo; echo @@READY=1; bash {REMOTE_SCRIPT} {shlex.join(self.args)}"
            )

            sent = False
            while True:
                try:
                    chunk = channel.recv(4096)
                except TimeoutError:
                    chunk = None
                if chunk == b"":
                    break
                if chunk:
                    self._feed(chunk)
                if not sent and "READY" in self.markers:
                    channel.sendall(self.stdin)
                    sent = True
            code = channel.recv_exit_status()

            _, stdout, _ = client.exec_command(f"rm -f {REMOTE_SCRIPT}")
            stdout.channel.recv_exit_status()
            return code
        finally:
            self._channel = None
            client.close()
