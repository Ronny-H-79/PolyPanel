"""Installation von SteamCMD und Serverdateien (auch vom Installer genutzt)."""
from __future__ import annotations

import os
import re
import signal
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


ASA_APP = "2430930"


def _plattform_flagge(app_id: str) -> list[str]:
    """ARR Ascended hat keinen Linux-Server: SteamCMD muss den Windows-Zweig laden.

    Ohne diesen Schalter endet die Installation mit "Failed to install app ... (Missing configuration)".
    """
    if str(app_id) == ASA_APP:
        return ["""+@sSteamCmdForcePlatformType windows"""]
    return []


def _steamcmd_bereit(cmd: str, log=print) -> bool:
    """SteamCMD vor dem ersten Zugriff aktualisieren (sonst "Missing configuration").

    Der Client laedt sich beim Aufruf selbst nach; bricht das ab, ist das Verzeichnis
    halbfertig und jede Installation scheitert. Dann wird der Client neu geholt.
    """
    try:
        r = subprocess.run([cmd, "+quit"], cwd=os.path.dirname(cmd),
                           capture_output=True, text=True, timeout=900)
        if r.returncode == 0:
            return True
        log("SteamCMD-Selbsttest fehlgeschlagen (exit %s) - Client wird neu geladen" % r.returncode)
    except (OSError, subprocess.SubprocessError) as exc:
        log("SteamCMD-Selbsttest nicht moeglich (%s) - Client wird neu geladen" % exc)
    shutil.rmtree(STEAMCMD_DIR, ignore_errors=True)
    return bool(ensure_steamcmd(log=log))


ACTIVE: dict[str, "subprocess.Popen[bytes]"] = {}


def cancel(name: str) -> dict[str, object]:
    """Laufende Installation abbrechen: SteamCMD-Prozessgruppe beenden."""
    proc = ACTIVE.get(name)
    if proc is None:
        return {"ok": False, "error": "keine laufende Installation"}
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except OSError:
        try:
            proc.terminate()
        except OSError:
            pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            pass
    ACTIVE.pop(name, None)
    return {"ok": True}


_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]|\x1b\][^\x07]*\x07")


def pump_output(stream, emit) -> None:
    """Zeilen aus der SteamCMD-Ausgabe ziehen - auch solche, die nur mit \\r enden.

    SteamCMD meldet Fortschritt mit Wagenruecklauf ohne Zeilenumbruch. Wer zeilenweise
    liest, bekommt deshalb waehrend des gesamten Downloads nichts zu sehen. Hier wird
    blockweise gelesen und an \\r und \\n getrennt, jeder Teil sofort gemeldet.
    """
    pending = ""
    while True:
        chunk = stream.read1(4096)
        if not chunk:
            break
        text = pending + chunk.decode("utf-8", "replace")
        parts = re.split(r"[\r\n]+", text)
        pending = parts.pop()
        for part in parts:
            part = _ANSI.sub("", part).strip()
            if part:
                emit(part)
    rest = _ANSI.sub("", pending).strip()
    if rest:
        emit(rest)


def install_server(inst: Instance, log=None) -> dict:
    """Serverdateien ueber SteamCMD holen; Ausgabe landet in <dir>/.install.log."""
    os.makedirs(inst.directory, exist_ok=True)
    log_path = os.path.join(inst.directory, ".install.log")
    extra = log or (lambda _msg: None)

    with open(log_path, "w", buffering=1) as fh:
        def emit(text: str) -> None:
            text = _ANSI.sub("", str(text)).rstrip()
            if not text:
                return
            fh.write(text + "\n")
            fh.flush()
            extra(text)

        emit("Installation gestartet %s" % time.strftime("%F %T"))
        cmd = ensure_steamcmd(log=emit)
        argv = ([cmd] + _plattform_flagge(inst.profile.server_app_id) +
                ["+force_install_dir", inst.directory, "+login", "anonymous",
                 "+app_update", inst.profile.server_app_id, "validate", "+quit"])
        _steamcmd_bereit(cmd, log=emit)
        emit("steamcmd %s" % " ".join(argv[1:]))
        proc = subprocess.Popen(argv, cwd=os.path.dirname(cmd), start_new_session=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ACTIVE[inst.name] = proc
        pump_output(proc.stdout, emit)
        proc.wait()
        if proc.returncode != 0:
            try:
                with open(log_path, encoding="utf-8", errors="replace") as lf:
                    letzte = lf.read()[-4000:]
            except OSError:
                letzte = ""
            if "Missing configuration" in letzte or "Failed to install app" in letzte:
                emit("SteamCMD meldet eine defekte Konfiguration - Client wird neu geladen und der Versuch wiederholt")
                shutil.rmtree(STEAMCMD_DIR, ignore_errors=True)
                cmd = ensure_steamcmd(log=emit)
                _steamcmd_bereit(cmd, log=emit)
                argv[0] = cmd
                emit("steamcmd %s" % " ".join(argv[1:]))
                proc = subprocess.Popen(argv, cwd=os.path.dirname(cmd), start_new_session=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                ACTIVE[inst.name] = proc
                pump_output(proc.stdout, emit)
                proc.wait()
        ACTIVE.pop(inst.name, None)
        emit("Installation beendet (exit %s)" % proc.returncode)

    if proc.returncode == 0:
        # Nachbereitung (z. B. Wine/.NET fuer Space Engineers) braucht ein EIGENES Log-Handle:
        # der with-Block oben hat fh schon geschlossen, `emit` wuerde mit
        # "I/O operation on closed file" abbrechen - und die Fehlermeldung gleich mit.
        try:
            with open(log_path, "a", buffering=1) as fh2:
                def nach(text: str) -> None:
                    sauber = _ANSI.sub("", str(text)).rstrip()
                    if not sauber:
                        return
                    fh2.write("Laufzeit: %s\n" % sauber)
                    fh2.flush()
                try:
                    inst.profile.post_install(inst, log=nach)
                except Exception as exc:                # noqa: BLE001 - Installation bleibt gueltig
                    nach("Nachbereitung fehlgeschlagen: %s" % exc)
        except OSError:
            pass

    return {"ok": proc.returncode == 0, "log": log_path, "exit": proc.returncode}
