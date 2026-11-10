"""Startet den ARK-Server mit einem echten PTY.

Ein PTY verhindert, dass Wine ein eigenes Konsolenfenster aufmacht (das passiert,
wenn ein Windows-Konsolenprogramm ohne Terminal gestartet wird). Die Ausgabe wird
zugleich in die Konsole-Logdatei geschrieben. Befehle nimmt der Prozess ueber einen
Unix-Socket entgegen (falls ASA stdin doch einmal auswertet).
"""
from __future__ import annotations

import fcntl
import os
import pty
import socket
import struct
import subprocess
import sys
import termios
import threading
import time

from .instance import Instance
from . import runner


def _argv(inst: Instance) -> list[str]:
    argv = inst.launch_argv()
    if not inst.profile.needs_wine:
        # native Spiele starten direkt (Satisfactory, 7 Days to Die)
        return argv
    if "proton" in os.path.basename(inst.wine_bin).lower():
        return [inst.wine_bin, "run"] + argv
    return [inst.wine_bin] + argv


def _pump(master: int, out) -> None:
    while True:
        try:
            data = os.read(master, 65536)
        except OSError:
            break
        if not data:
            break
        try:
            out.write(data)
        except (OSError, ValueError):
            break


def main(name: str) -> int:
    conf = os.path.expanduser("~/.config/noah2games/%s.json" % name)
    inst = Instance.load(conf)
    inst.write_ini()

    sock_path = os.path.join(inst.directory, ".noah2games-console.sock")
    try:
        os.unlink(sock_path)
    except OSError:
        pass

    console = open(inst.console_log, "ab", buffering=0)
    console.write(("\n=== noah2games start %s (%s) ===\n"
                   % (time.strftime("%F %T"), "pty" if inst.profile.use_pty else "direkt")).encode())

    use_pty = getattr(inst.profile, "use_pty", True)
    if use_pty:
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 50, 200, 0, 0))
        proc = subprocess.Popen(
            _argv(inst), cwd=inst.profile.workdir(inst), env=runner._env(inst),
            stdin=slave, stdout=slave, stderr=slave, start_new_session=True,
        )
        os.close(slave)
    else:
        # .NET-Server (Space Engineers) brechen an einem PTY sofort ab
        master = None
        proc = subprocess.Popen(
            _argv(inst), cwd=inst.profile.workdir(inst), env=runner._env(inst),
            stdin=subprocess.PIPE, stdout=console, stderr=console,
            start_new_session=True,
        )
    with open(inst.pid_file, "w") as fh:
        fh.write(str(proc.pid))

    if master is not None:
        threading.Thread(target=_pump, args=(master, console), daemon=True).start()

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    os.chmod(sock_path, 0o600)
    srv.listen(8)
    srv.settimeout(3)

    def _handle(conn: socket.socket) -> None:
        try:
            data = conn.recv(4096).decode("utf-8", "replace").strip()
            if data:
                if master is not None:
                    os.write(master, (data + "\n").encode())
                else:
                    proc.stdin.write((data + "\n").encode())
                    proc.stdin.flush()
                console.write(("[noah2games] >> %s\n" % data).encode())
                conn.sendall(b"ok")
            else:
                conn.sendall(b"leer")
        except Exception as exc:  # noqa: BLE001
            try:
                conn.sendall(("fehler: %s" % exc).encode())
            except OSError:
                pass
        finally:
            conn.close()

    while proc.poll() is None:
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        except OSError:
            break
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()

    srv.close()
    try:
        os.unlink(sock_path)
    except OSError:
        pass
    runner._cleanup(inst)
    console.write(("=== noah2games: Server beendet (exit %s) ===\n" % proc.returncode).encode())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "test"))
