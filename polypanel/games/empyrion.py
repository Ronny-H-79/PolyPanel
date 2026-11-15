"""Empyrion: Galactic Survival - Dedicated Server (Steam-App 530870).

Der offizielle Dedicated Server ist **nur fuer Windows** verfuegbar (Steam: kein
Linux-Depot), laeuft also unter Wine. Start ohne Grafik ueber
`EmpyrionDedicated_NoGraphics.exe`; die Variante mit Fenster braucht einen
X-Server, deshalb steht hier zusaetzlich xvfb davor.

Konfiguration: `dedicated.yaml` im Serverordner (YAML mit Kommentaren - die Datei
wird zeilenweise gepflegt, damit die Vorlage erhalten bleibt):
  Srv_Port (UDP, Standard 30000), Srv_Name, Srv_Password, Srv_MaxPlayers,
  Srv_Description, Srv_Public, GameName (Spielstandordner), Mode, CustomScenario,
  EACActive, Tel_Port (TCP 30004, nur lokal), Tel_Pwd.

Es gibt keinen RCON-Kanal wie bei ARK; Steuerung also nur ueber Prozess, Dateien und
den Telnet-Port. "Bereit" wird ueber den belegten UDP-Spielport erkannt.
"""
from __future__ import annotations

import glob
import os
import re
import shutil

from .base import GameProfile

EXE_NOGFX = "EmpyrionDedicated_NoGraphics.exe"
EXE_GUI = "EmpyrionDedicated.exe"
CFG_NAME = "dedicated.yaml"

# Schluessel, die das Panel schreibt (alles andere bleibt unangetastet).
FELDER = (
    ("session_name", "Server-Name", "Name in der Serverliste (Srv_Name)", "text"),
    ("max_players", "Max. Spieler", "Srv_MaxPlayers", "int"),
    ("port", "Spielport (UDP)", "Srv_Port, Standard 30000", "int"),
    ("server_password", "Server-Passwort", "Beitritt nur mit Passwort (leer = offen)", "password"),
)


def _udp_port_bound(port: int) -> bool:
    """Laeuft ein UDP-Listener auf diesem Port? (kein Handshake, /proc lesen)"""
    ziel = "%04X" % port
    for pfad in ("/proc/net/udp", "/proc/net/udp6"):
        try:
            with open(pfad, encoding="utf-8") as fh:
                next(fh, None)
                for zeile in fh:
                    teile = zeile.split()
                    if len(teile) > 1 and teile[1].split(":")[-1] == ziel:
                        return True
        except OSError:
            continue
    return False


def _xvfb() -> list[str]:
    """Unity/Wine ohne X-Server bricht ab - xvfb-run davor setzen."""
    if os.environ.get("DISPLAY"):
        return []
    xvfb = shutil.which("xvfb-run")
    return [xvfb, "-a"] if xvfb else []


class EmpyrionProfile(GameProfile):
    key = "empyrion"
    label = "Empyrion: Galactic Survival"
    server_app_id = "530870"

    needs_wine = True
    needs_display = True
    has_control = False              # kein RCON (nur Telnet auf 127.0.0.1)
    supports_mods = False            # Panel-Modverwaltung ist ARK-spezifisch
    supports_cluster = False
    supports_whitelist = False
    use_pty = False                  # Unity-Server moegen kein PTY

    default_game_port = 30000
    default_query_port = 30001
    default_control_port = 0
    default_max_players = 20

    install_note = ("Windows-Server unter Wine. Start ohne Grafik ueber "
                    "EmpyrionDedicated_NoGraphics.exe; Konfiguration in dedicated.yaml "
                    "(Srv_Name, Srv_Port, Srv_MaxPlayers, Srv_Password, GameName).")

    settings_fields = FELDER

    # ----------------------------------------------------------------- Pfade
    def exe(self, inst) -> str:
        for name in (EXE_NOGFX, EXE_GUI):
            pfad = os.path.join(inst.directory, name)
            if os.path.exists(pfad):
                return pfad
        for muster in ("*.exe", "*/*.exe"):
            treffer = [p for p in sorted(glob.glob(os.path.join(inst.directory, muster)))
                       if "EmpyrionDedicated" in os.path.basename(p)]
            if treffer:
                return treffer[0]
        return os.path.join(inst.directory, EXE_NOGFX)

    def workdir(self, inst) -> str:
        return inst.directory

    def config_path(self, inst) -> str:
        return os.path.join(inst.directory, CFG_NAME)

    def log_path(self, inst) -> str:
        for muster in ("Logs/*.log", "*.log"):
            treffer = sorted(glob.glob(os.path.join(inst.directory, muster)))
            if treffer:
                return treffer[-1]
        return os.path.join(inst.directory, "EmpyrionDedicated.log")

    # ------------------------------------------------------------ Startzeile
    def launch_prefix(self, inst) -> list[str]:
        return _xvfb()

    def launch_argv(self, inst) -> list[str]:
        argv = [self.exe(inst)]
        if getattr(inst, "extra_args", ""):
            argv.extend(inst.extra_args.split())
        return argv

    # ---------------------------------------------------------- Konfigdatei
    def write_config(self, inst) -> None:
        """dedicated.yaml zeilenweise pflegen - Kommentare und Reihenfolge bleiben."""
        pfad = self.config_path(inst)
        if not os.path.exists(pfad):
            return          # Vorlage fehlt (noch nicht installiert): nichts erfinden
        werte = [("Srv_Name", str(getattr(inst, "session_name", "") or inst.name)),
                 ("Srv_Port", str(getattr(inst, "port", self.default_game_port)
                                  or self.default_game_port)),
                 ("Srv_MaxPlayers", str(getattr(inst, "max_players",
                                                self.default_max_players)))]
        passwort = (getattr(inst, "server_password", "") or "").strip()
        if passwort:
            werte.append(("Srv_Password", passwort))

        with open(pfad, encoding="utf-8", errors="replace") as fh:
            zeilen = fh.read().splitlines()

        offen = {k for k, _ in werte}
        neu = []
        for zeile in zeilen:
            treffer = re.match(r"^(\s*)([A-Za-z_]+)(\s*:\s*)(.*)$", zeile)
            if treffer and treffer.group(2) in offen:
                schluessel = treffer.group(2)
                wert = dict(werte)[schluessel]
                rest = treffer.group(4)
                # Kommentar hinter dem Wert erhalten (z. B. "30000   # Spielport")
                kommentar = ""
                if "#" in rest:
                    kommentar = "  " + rest[rest.index("#"):]
                if passwort and schluessel == "Srv_Password":
                    wert_text = '"%s"' % wert
                elif schluessel in ("Srv_Port", "Srv_MaxPlayers"):
                    wert_text = wert
                else:
                    wert_text = '"%s"' % wert
                neu.append("%s%s%s%s%s" % (treffer.group(1), schluessel,
                                           treffer.group(3), wert_text, kommentar))
                offen.discard(schluessel)
            else:
                neu.append(zeile)
        for schluessel in sorted(offen):
            neu.append("%s: %s" % (schluessel, dict(werte)[schluessel]))

        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write("\n".join(neu) + "\n")

    # ---------------------------------------------------------- Steuerkanal
    def ready(self, inst) -> bool:
        return _udp_port_bound(int(getattr(inst, "port", self.default_game_port)))

    def players(self, inst):
        return None
