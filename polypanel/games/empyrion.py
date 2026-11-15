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

# Das echte Serverprogramm liegt im Unterordner - im Wurzelverzeichnis stehen nur
# die Hersteller-Batchdateien (EmpyrionDedicated.cmd) und der Launcher.
EXE_SERVER = os.path.join("DedicatedServer", "EmpyrionDedicated.exe")
EXE_NOGFX = "EmpyrionDedicated_NoGraphics.exe"   # nur als Notnagel, falls vorhanden
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
        echt = os.path.join(inst.directory, EXE_SERVER)
        if os.path.exists(echt):
            return echt
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
        ordner = os.path.join(inst.directory, "Logs")
        os.makedirs(ordner, exist_ok=True)
        return os.path.join(ordner, "EmpyrionDedicated.log")

    # ------------------------------------------------------------ Startzeile
    def launch_prefix(self, inst) -> list[str]:
        return _xvfb()

    def launch_argv(self, inst) -> list[str]:
        # "-nographics requires -batchmode" - einzeln bricht Unity den Start ab.
        argv = [self.exe(inst), "-batchmode", "-nographics",
                "-logFile", self.log_path(inst)]
        if getattr(inst, "extra_args", ""):
            argv.extend(inst.extra_args.split())
        return argv

    # ---------------------------------------------------------- Konfigdatei
    def write_config(self, inst) -> None:
        """dedicated.yaml pflegen - Schluessel liegen unter `ServerConfig:`.

        Die Vorlage des Herstellers verschachtelt alles unter `ServerConfig:` und
        kommentiert die meisten Zeilen aus. Ein Anhaengen am Dateiende erzeugt
        deshalb YAML auf oberster Ebene: der Server liest die Werte nicht (und
        bricht bei ungueltigem Aufbau ganz ab). Deshalb werden vorhandene - auch
        auskommentierte - Zeilen ersetzt und fehlende innerhalb des Blocks mit
        derselben Einrueckung eingesetzt.
        """
        pfad = self.config_path(inst)
        if not os.path.exists(pfad):
            return          # Vorlage fehlt (noch nicht installiert): nichts erfinden

        passwort = (getattr(inst, "server_password", "") or "").strip()
        werte = {
            "Srv_Name": ('"%s"' % (getattr(inst, "session_name", "") or inst.name), True),
            "Srv_Port": (str(getattr(inst, "port", self.default_game_port)
                             or self.default_game_port), False),
            "Srv_MaxPlayers": (str(getattr(inst, "max_players", self.default_max_players)), False),
        }
        if passwort:
            werte["Srv_Password"] = ('"%s"' % passwort, True)

        with open(pfad, encoding="utf-8", errors="replace") as fh:
            zeilen = fh.read().splitlines()

        offen = dict(werte)
        neu = []
        for zeile in zeilen:
            treffer = re.match(r"^(\s*)(#\s*)?(Srv_[A-Za-z]+)(\s*:\s*)(.*)$", zeile)
            if treffer and treffer.group(3) in offen:
                schluessel = treffer.group(3)
                wert, _ = offen.pop(schluessel)
                rest = treffer.group(5)
                kommentar = ("  " + rest[rest.index("#"):]) if "#" in rest else ""
                neu.append("%s%s: %s%s" % (treffer.group(1), schluessel, wert, kommentar))
                continue
            # Streuner auf oberster Ebene entfernen: YamlDotNet verweigert den Start,
            # wenn ein Schluessel ausserhalb von ServerConfig/GameConfig steht
            # ("Make sure your config file is updated to the current server version").
            if re.match(r"^(Srv_|Tel_|EACActive|GameName|Mode|CustomScenario)[A-Za-z_]*\s*:", zeile):
                continue
            neu.append(zeile)

        if offen:
            block = next((i for i, z in enumerate(neu) if re.match(r"^ServerConfig:\s*$", z)), None)
            if block is None:
                neu.extend("%s: %s" % (k, v) for k, (v, _) in sorted(offen.items()))
            else:
                einzug = None
                ende = len(neu)
                for i in range(block + 1, len(neu)):
                    if neu[i].strip() and not neu[i].startswith((" ", "\t")):
                        ende = i
                        break
                    if einzug is None:
                        m2 = re.match(r"^(\s+)\S", neu[i])
                        if m2:
                            einzug = m2.group(1)
                einzug = einzug or "    "
                neu[ende:ende] = ["%s%s: %s" % (einzug, k, v)
                                  for k, (v, _) in sorted(offen.items())]

        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write("\n".join(neu) + "\n")

    # ---------------------------------------------------------- Steuerkanal
    def ready(self, inst) -> bool:
        return _udp_port_bound(int(getattr(inst, "port", self.default_game_port)))

    def players(self, inst):
        return None
