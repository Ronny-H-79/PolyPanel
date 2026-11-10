"""systemd-Dienste fuer den Supervisor schreiben und aktivieren.

Auf einem Server (root) entsteht ein Systemdienst in /etc/systemd/system - der laeuft beim Booten,
ohne Login und ohne `loginctl enable-linger`. Als normaler Benutzer wird daraus ein User-Dienst.
"""
from __future__ import annotations

import os
import pwd
import shutil
import subprocess
import sys

SYSTEM_DIR = "/etc/systemd/system"
USER_DIR = os.path.expanduser("~/.config/systemd/user")


def python_bin() -> str:
    """System-Python bevorzugen - ein venv-Interpreter wuerde den Dienst sterben lassen."""
    for candidate in ("/usr/bin/python3", os.path.join(sys.base_prefix, "bin", "python3")):
        if os.path.exists(candidate):
            return candidate
    return shutil.which("python3") or "python3"


def project_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def render(inst, system: bool) -> str:
    lines = [
        "[Unit]",
        "Description=noah2games supervisor (%s)" % inst.name,
        "After=network-online.target",
        "Wants=network-online.target",
        "",
        "[Service]",
        "Type=simple",
    ]
    if system:
        try:
            lines.append("User=%s" % pwd.getpwuid(os.geteuid()).pw_name)
        except KeyError:
            pass
    lines += [
        "WorkingDirectory=%s" % project_dir(),
        "Environment=PYTHONPATH=%s" % project_dir(),
        "ExecStart=%s -m noah2games supervise --all" % python_bin(),
        "Restart=always",
        "RestartSec=15",
        "",
        "[Install]",
        "WantedBy=%s" % ("multi-user.target" if system else "default.target"),
    ]
    return "\n".join(lines) + "\n"


def install(inst, system: bool | None = None) -> dict:
    """Dienst schreiben, aktivieren und starten. Gibt Auskunft darueber, was passiert ist."""
    if system is None:
        system = os.geteuid() == 0 and os.path.isdir(SYSTEM_DIR)

    path = os.path.join(SYSTEM_DIR if system else USER_DIR, "noah2games-%s.service" % inst.name)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(render(inst, system))
    except OSError as exc:
        return {"ok": False, "system": system, "path": path, "error": str(exc)}

    scope = [] if system else ["--user"]
    try:
        subprocess.run(["systemctl", *scope, "daemon-reload"], capture_output=True, timeout=30)
        done = subprocess.run(["systemctl", *scope, "enable", "--now", os.path.basename(path)],
                              capture_output=True, text=True, timeout=30)
        ok = done.returncode == 0
        message = (done.stdout or done.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return {"ok": False, "system": system, "path": path, "error": str(exc)}

    linger = ""
    if ok and not system:
        try:
            subprocess.run(["loginctl", "enable-linger", pwd.getpwuid(os.geteuid()).pw_name],
                           capture_output=True, timeout=20)
            linger = "linger aktiv"
        except (OSError, subprocess.SubprocessError):
            pass
    return {"ok": ok, "system": system, "path": path, "message": message, "linger": linger}
