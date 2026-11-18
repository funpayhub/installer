from __future__ import annotations

import shutil
from dataclasses import dataclass

import paramiko

from dothub_installer.config import IS_WINDOWS, KNOWN_HOSTS


@dataclass
class Target:
    host: str = ""  # empty: this computer
    port: int = 22
    user: str = ""
    password: str = ""
    key_file: str = ""
    sudo_password: str = ""

    @property
    def remote(self) -> bool:
        return bool(self.host)

    @property
    def linux(self) -> bool:
        return self.remote or not IS_WINDOWS

    @property
    def known_hosts_name(self) -> str:
        return self.host if self.port == 22 else f"[{self.host}]:{self.port}"

    def connect(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            self.host,
            port=self.port,
            username=self.user,
            password=self.password or None,
            key_filename=self.key_file or None,
            timeout=5,
        )
        return client

    def replace_host_key(self, key: paramiko.PKey) -> None:
        lines = (
            KNOWN_HOSTS.read_text(encoding="utf-8").splitlines()
            if KNOWN_HOSTS.is_file()
            else []
        )

        kept = []
        for line in lines:
            fields = line.split(maxsplit=1)
            if not fields or fields[0].startswith(("#", "@")) or len(fields) < 2:
                kept.append(line)
                continue
            hosts = [
                i
                for i in fields[0].split(",")
                if not _host_matches(i, self.known_hosts_name)
            ]
            if hosts:
                kept.append(",".join(hosts) + " " + fields[1])

        KNOWN_HOSTS.parent.mkdir(parents=True, exist_ok=True)
        if KNOWN_HOSTS.exists():
            shutil.copy2(KNOWN_HOSTS, KNOWN_HOSTS.with_name("known_hosts.old"))
        kept.append(f"{self.known_hosts_name} {key.get_name()} {key.get_base64()}")
        KNOWN_HOSTS.write_text("\n".join(kept) + "\n", encoding="utf-8")


def _host_matches(pattern: str, hostname: str) -> bool:
    if pattern.startswith("|1|"):  # hashed: |1|salt|hash
        return paramiko.HostKeys.hash_host(hostname, pattern.split("|")[2]) == pattern
    return pattern == hostname
