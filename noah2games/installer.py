"""Installation von SteamCMD und Serverdateien (auch vom Installer genutzt)."""
from __future__ import annotations

import os
import shutil
import subprocess
import tarfile
import time
import urllib.request

from .instance import Instance

STEAMCMD_DIR = os.path.expanduser("~/steamcmd")
STEAMCMD_URL = "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz"
APP_ID = "2430930"  # Vorgabe (ARK); je Instanz entscheidet das Spielprofil


def steamcmd_path() -> str | None:
    """Pfad zu steamcmd.sh - erst im Standardordner, dann im PATH."""
    local = os.path.join(STEAMCMD_DIR, "steamcmd.sh")
    if os.path.exists(local):
        return local
    return shutil.which("steamcmd")


def ensure_steamcmd(log=print) -> str:
    """SteamCMD herunterladen, falls nicht vorhanden. Gibt den Pfad zurueck."""
    found = steamcmd_path()
    if found:
        return found
    log("SteamCMD nicht gefunden - lade nach %s" % STEAMCMD_DIR)
    os.makedirs(STEAMCMD_DIR, exist_ok=True)
    archive = os.path.join(STEAMCMD_DIR, "steamcmd_linux.tar.gz")
    urllib.request.urlretrieve(STEAMCMD_URL, archive)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(STEAMCMD_DIR)
    os.unlink(archive)
    target = os.path.join(STEAMCMD_DIR, "steamcmd.sh")
    if not os.path.exists(target):
        raise RuntimeError("SteamCMD-Entpacken fehlgeschlagen")
    os.chmod(target, 0o755)
    log("SteamCMD bereit: %s" % target)
    return target


def install_server(inst: Instance, log=None) -> dict:
    """Serverdateien ueber SteamCMD holen; Ausgabe landet in <dir>/.install.log."""
    emit = log or (lambda _msg: None)
    cmd = ensure_steamcmd(log=emit)
    log_path = os.path.join(inst.directory, ".install.log")
    os.makedirs(inst.directory, exist_ok=True)
    argv = [cmd, "+force_install_dir", inst.directory, "+login", "anonymous",
            "+app_update", inst.profile.server_app_id, "validate", "+quit"]
    with open(log_path, "w", buffering=1) as fh:
        fh.write("Installation gestartet %s\n" % time.strftime("%F %T"))
        proc = subprocess.Popen(argv, cwd=os.path.dirname(cmd),
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:  # type: ignore[union-attr]
            fh.write(line)
            emit(line.rstrip())
        proc.wait()
        fh.write("Installation beendet (exit %s)\n" % proc.returncode)
    if proc.returncode == 0:
        try:
            inst.profile.post_install(inst, log=emit)   # z. B. .NET fuer Space Engineers
        except Exception as exc:                        # noqa: BLE001 - Installation bleibt gueltig
            emit("Nachbereitung fehlgeschlagen: %s" % exc)
    return {"ok": proc.returncode == 0, "log": log_path, "exit": proc.returncode}
