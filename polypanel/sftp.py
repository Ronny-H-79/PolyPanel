"""SFTP-Zugang je Instanz.

Ein Dienst, ein Port pro Instanz, Chroot auf den Instanzordner. Benutzername, Passwort
und Port stehen in der Instanz-JSON (`sftp_enabled`, `sftp_user`, `sftp_password`,
`sftp_port`); ist `sftp_port` 0, wird `sftp_base_port + laufende Nummer` benutzt.

Der Dienst haengt nicht am Laufzeitzustand der Instanz: Dateien hochladen geht auch,
waehrend der Server aus ist (so macht es AMP auch).

`asyncssh` ist eine optionale Abhaengigkeit. Fehlt sie, laeuft das Panel normal weiter,
nur dieser Dienst startet nicht und sagt im Panel-Log, was fehlt.
"""
from __future__ import annotations

import asyncio
import json
import os
import secrets
import string
from typing import Any

from . import panellog, paths, registry

BASE_PORT_DEFAULT = 2225
HOSTKEY_NAME = "sftp_hostkey"


class FehltAbhaengigkeit(RuntimeError):
    """asyncssh ist nicht installiert."""


def _ssh() -> Any:
    try:
        import asyncssh  # noqa: PLC0415 - absichtlich spaet, damit das Panel ohne laeuft
    except ImportError as exc:  # pragma: no cover - Umgebungssache
        raise FehltAbhaengigkeit(
            "asyncssh fehlt (apt install python3-asyncssh oder pip install asyncssh)"
        ) from exc
    return asyncssh


def verfuegbar() -> bool:
    try:
        _ssh()
    except FehltAbhaengigkeit:
        return False
    return True


# --------------------------------------------------------------------- Helfer
def hostkey_path() -> str:
    return os.path.join(paths.CONF_DIR, HOSTKEY_NAME)


def ensure_hostkey() -> str:
    """Legt beim ersten Start einen Hostschluessel an (600, im Config-Verzeichnis)."""
    pfad = hostkey_path()
    if os.path.exists(pfad):
        return pfad
    ssh = _ssh()
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    key = ssh.generate_private_key("ssh-ed25519")
    fd = os.open(pfad, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(key.export_private_key())
    return pfad


def generate_password(laenge: int = 20) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(laenge))


def default_user(inst) -> str:
    roh = (inst.sftp_user or inst.name).strip().lower()
    erlaubt = "".join(c if (c.isalnum() or c in "-_") else "-" for c in roh)
    return erlaubt or "sftp"


def _einstellungen() -> dict:
    try:
        with open(paths.SETTINGS_PATH, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (OSError, ValueError):
        return {}


def base_port() -> int:
    try:
        wert = int(_einstellungen().get("sftp_base_port", BASE_PORT_DEFAULT))
    except (TypeError, ValueError):
        wert = BASE_PORT_DEFAULT
    return wert if 1024 <= wert <= 65000 else BASE_PORT_DEFAULT


def port_for(inst, nummer: int = 0) -> int:
    return int(inst.sftp_port or (base_port() + nummer))


def adresse(inst, nummer: int = 0, host: str = "") -> str:
    """Fertige Adresse fuer Anzeige und Kopierknopf."""
    return "sftp://%s@%s:%d" % (default_user(inst), host or os.uname().nodename,
                                port_for(inst, nummer))


UNIT_TEXT = """[Unit]
Description=PolyPanel SFTP-Zugang (ein Port je Instanz)
After=network-online.target

[Service]
Type=simple
WorkingDirectory={dauer}
Environment=PYTHONPATH={dauer}
ExecStart={python} -m polypanel sftp
Restart=on-failure
RestartSec=10

[Install]
WantedBy={ziel}
"""


def _panel_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_service() -> tuple[bool, str]:
    """Legt die systemd-Unit an (falls noetig) und startet sie.

    Systemweite Installation (Web-Unit in /etc/systemd/system) wird als Systemdienst
    angelegt, sonst als Benutzerdienst - analog zu polypanel-web.
    """
    import subprocess
    import sys

    system = os.path.exists("/etc/systemd/system/polypanel-web.service")
    ziel = "multi-user.target" if system else "default.target"
    text = UNIT_TEXT.format(dauer=_panel_dir(), python=sys.executable or "/usr/bin/python3",
                            ziel=ziel)
    if system and os.geteuid() != 0:
        return False, "Systemdienst, aber keine root-Rechte"

    pfad = ("/etc/systemd/system/polypanel-sftp.service" if system
            else os.path.expanduser("~/.config/systemd/user/polypanel-sftp.service"))
    try:
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        alt = ""
        if os.path.exists(pfad):
            with open(pfad, encoding="utf-8") as fh:
                alt = fh.read()
        if alt != text:
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(text)
    except OSError as exc:
        return False, "Unit nicht schreibbar (%s)" % exc

    basis = ["systemctl"] if system else ["systemctl", "--user"]
    for befehl in (basis + ["daemon-reload"],
                   basis + ["enable", "--now", "polypanel-sftp.service"]):
        try:
            lauf = subprocess.run(befehl, capture_output=True, text=True, timeout=25)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, "systemctl fehlgeschlagen (%s)" % exc
        if lauf.returncode != 0:
            return False, (lauf.stderr or lauf.stdout or "").strip()[:200] or "systemctl-Fehler"
    return True, "SFTP-Dienst laeuft"


def setze_zugang(inst, nummer: int = 0) -> dict:
    """Aktiviert SFTP und fuellt Benutzer/Passwort/Port, falls leer."""
    inst.sftp_enabled = True
    inst.sftp_user = default_user(inst)
    if not inst.sftp_password:
        inst.sftp_password = generate_password()
    if not inst.sftp_port:
        inst.sftp_port = port_for(inst, nummer)
    return {
        "user": inst.sftp_user,
        "password": inst.sftp_password,
        "port": inst.sftp_port,
        "url": adresse(inst, nummer),
    }


# --------------------------------------------------------------------- Server
def _serverklasse(ssh, benutzer: str, passwort: str):
    class _SftpServer(ssh.SSHServer):
        """Passwortanmeldung gegen genau einen Benutzer dieser Instanz."""

        def begin_auth(self, username: str) -> bool:
            # Immer True: sonst gilt die Anmeldung ohne Passwort als erledigt.
            # Die Ablehnung passiert in validate_password (Benutzer + Passwort).
            return True

        def password_auth_supported(self) -> bool:
            return True

        def validate_password(self, username: str, password: str) -> bool:
            return username == benutzer and secrets.compare_digest(password, passwort)

    return _SftpServer


def _sftp_fabrik(ssh, basis: str):
    """Sitzungsfabrik fuer den SFTP-Subsystem: Chroot je Instanz."""

    def fabrik(chan):
        return ssh.SFTPServer(chan, chroot=os.fsencode(basis))

    return fabrik


def _instanzen() -> list:
    gefunden = []
    for name in registry.names():
        inst = registry.load(name)
        if inst is not None:
            gefunden.append(inst)
    return gefunden


async def _aufbauen() -> list:
    ssh = _ssh()
    key = ensure_hostkey()
    laufend: list = []
    for nummer, inst in enumerate(_instanzen()):
        if not getattr(inst, "sftp_enabled", False):
            continue
        passwort = getattr(inst, "sftp_password", "") or ""
        if not passwort:
            panellog.write("SFTP %s: kein Passwort gesetzt - uebersprungen" % inst.name)
            continue
        basis = os.path.abspath(inst.directory)
        if not os.path.isdir(basis):
            panellog.write("SFTP %s: Ordner fehlt (%s)" % (inst.name, basis))
            continue
        port = port_for(inst, nummer)
        benutzer = default_user(inst)
        try:
            laufend.append(
                await ssh.create_server(
                    lambda b=benutzer, p=passwort: _serverklasse(ssh, b, p)(),
                    "0.0.0.0",
                    port,
                    server_host_keys=[key],
                    sftp_factory=_sftp_fabrik(ssh, basis),
                )
            )
        except OSError as exc:
            panellog.write("SFTP %s: Port %d nicht moeglich (%s)" % (inst.name, port, exc))
            continue
        panellog.write("SFTP %s: Benutzer %s, Port %d, Chroot %s" % (inst.name, benutzer, port, basis))
    if not laufend:
        panellog.write("SFTP: keine Instanz aktiviert - warte auf Aenderung")
    return laufend


def run() -> int:
    """Vordergrund-Dienst; systemd-Unit `polypanel-sftp`."""
    try:
        _ssh()
    except FehltAbhaengigkeit as exc:
        panellog.write("SFTP: %s - Dienst nicht gestartet" % exc)
        return 2

    async def haupt() -> None:
        while True:
            dienste = await _aufbauen()
            await asyncio.sleep(30)          # Aenderungen an Port/Passwort greifen nach 30 s
            for dienst in dienste:
                dienst.close()
                try:
                    await dienst.wait_closed()
                except Exception:  # noqa: BLE001 - Abschluss darf nicht toeten
                    pass

    panellog.write("SFTP-Dienst startet (Basis-Port %d)" % base_port())
    try:
        asyncio.run(haupt())
    except KeyboardInterrupt:
        pass
    return 0
