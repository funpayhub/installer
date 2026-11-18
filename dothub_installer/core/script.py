from __future__ import annotations

from dothub_installer.core.target import Target


def script_args(
    target: Target,
    *,
    token: str,
    password: str,
    directory: str,
    proxy: str,
    service: bool,
    check: bool,
) -> list[str]:
    if target.linux:
        args = [
            "--token",
            token,
            "--password",
            password,
            "--dir",
            directory,
            "--sudo-password-stdin",
        ]
        args += ["--service", "yes" if service else "no"]
        args += ["--proxy", proxy] if proxy else []
        args += ["--check"] if check else []
    else:
        args = ["-Token", token, "-Password", password, "-Dir", directory]
        args += ["-Proxy", proxy] if proxy else []
        args += ["-Check"] if check else []
    return args
