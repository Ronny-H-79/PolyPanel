"""Empyrion: Galactic Survival - Dedicated Server (Steam-App 530870).

Der offizielle Dedicated Server ist **nur fuer Windows** verfuegbar (Steam: kein
Linux-Depot), laeuft also unter Wine. Gestartet wird direkt
`DedicatedServer/EmpyrionDedicated.exe` - im Wurzelordner stehen nur die
Hersteller-Batchdateien und der Launcher. Unity verlangt `-batchmode` **und**
`-nographics` zusammen, sonst bricht der Start mit "-nographics requires
-batchmode" ab; ohne X-Server kommt xvfb-run davor.

Konfiguration: `dedicated.yaml` im Serverordner. Die Datei ist verschachtelt
(`ServerConfig:` und `GameConfig:` mit vier Leerzeichen Einrueckung) und
kommentiert die meisten Schluessel aus. Sie wird deshalb zeilenweise gepflegt:
vorhandene (auch auskommentierte) Zeilen werden ersetzt, fehlende im richtigen
Block eingesetzt. Schluessel auf oberster Ebene lehnt der Server mit
"Make sure your config file is updated to the current server version" ab -
solche Streuner werden entfernt.

Kein RCON; Steuerung ueber Prozess, Dateien und optional Telnet (nur lokal).
"Bereit" wird ueber den belegten UDP-Spielport erkannt.
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

# Alle Einstellungen, die der Reiter "Einstellungen" anbietet.
# (Sektion, Schluessel, Label, Hinweis, Typ, Gruppe)
FELDER = (
    ("ServerConfig", "Srv_Name", "Server-Name", "Name in der Serverliste", "text", "srv"),
    ("ServerConfig", "Srv_Port", "Spielport (UDP)", "Standard 30000", "int", "srv"),
    ("ServerConfig", "Srv_MaxPlayers", "Max. Spieler", "", "int", "srv"),
    ("ServerConfig", "Srv_Password", "Server-Passwort", "leer = offen", "password", "srv"),
    ("ServerConfig", "Srv_Description", "Beschreibung", "max. 127 Zeichen", "text", "srv"),
    ("ServerConfig", "Srv_Public", "In Serverliste zeigen", "true / false", "text", "srv"),
    ("ServerConfig", "Srv_ReservePlayfields", "Reserve-Playfields", "0 – 10", "int", "srv"),
    ("ServerConfig", "Srv_StopPeriod", "Auto-Neustart alle n Std.", "leer = nie", "int", "srv"),
    ("ServerConfig", "EACActive", "Easy Anti-Cheat", "true / false – Client muss passen",
     "text", "srv"),
    ("ServerConfig", "MaxAllowedSizeClass", "Max. Bauklasse", "Standard 10", "int", "srv"),
    ("ServerConfig", "AllowedBlueprints", "Erlaubte Blueprints", "z. B. All", "text", "srv"),
    ("ServerConfig", "HeartbeatServer", "Heartbeat (s)", "", "int", "srv"),
    ("ServerConfig", "TimeoutBootingPfServer", "Start-Timeout Playfield (s)", "", "int", "srv"),
    ("ServerConfig", "Tel_Enabled", "Telnet an", "true / false (nur lokal)", "text", "srv"),
    ("ServerConfig", "Tel_Port", "Telnet-Port", "Standard 30004", "int", "srv"),
    ("ServerConfig", "Tel_Pwd", "Telnet-Passwort", "", "password", "srv"),
    ("GameConfig", "GameName", "Spielstand-Name", "Ordner unter Saves", "text", "game"),
    ("GameConfig", "Mode", "Modus", "Survival oder Creative", "text", "game"),
    ("GameConfig", "CustomScenario", "Szenario", "z. B. Default Multiplayer", "text", "game"),
    ("GameConfig", "SaveDirectory", "Speicherordner", "leer = Standard", "text", "game"),
)

# Panel-Felder, die zusaetzlich in der Instanz gespiegelt werden.
SPIEGEL = {"Srv_Name": "session_name", "Srv_Port": "port",
           "Srv_MaxPlayers": "max_players", "Srv_Password": "server_password"}


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


def _abschnitte(zeilen) -> list[tuple[str, int, int]]:
    """Blöcke der YAML: (Name, Startzeile, Endzeile) fuer die oberste Ebene."""
    bloecke = []
    aktuell = None
    start = 0
    for i, zeile in enumerate(zeilen):
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*$", zeile)
        if m:
            if aktuell:
                bloecke.append((aktuell, start, i))
            aktuell, start = m.group(1), i
    if aktuell:
        bloecke.append((aktuell, start, len(zeilen)))
    return bloecke


def yaml_lesen(pfad: str) -> dict[str, dict[str, str]]:
    """Werte je Abschnitt lesen (auskommentierte Zeilen zaehlen mit)."""
    daten: dict[str, dict[str, str]] = {}
    try:
        with open(pfad, encoding="utf-8", errors="replace") as fh:
            zeilen = fh.read().splitlines()
    except OSError:
        return daten
    for name, start, ende in _abschnitte(zeilen):
        werte = {}
        for zeile in zeilen[start + 1:ende]:
            m = re.match(r"^\s+(#\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", zeile)
            if not m:
                continue
            wert = m.group(3)
            if "#" in wert:
                wert = wert[:wert.index("#")]
            wert = wert.strip().strip('"').strip("'")
            werte[m.group(2)] = wert
        daten[name] = werte
    return daten


def yaml_aktiv(pfad: str) -> set[tuple[str, str]]:
    """Welche Schluessel sind wirklich gesetzt (nicht nur als Kommentar vorhanden)?"""
    aktiv: set[tuple[str, str]] = set()
    try:
        with open(pfad, encoding="utf-8", errors="replace") as fh:
            zeilen = fh.read().splitlines()
    except OSError:
        return aktiv
    for name, start, ende in _abschnitte(zeilen):
        for zeile in zeilen[start + 1:ende]:
            m = re.match(r"^\s+([A-Za-z_][A-Za-z0-9_]*)\s*:\s*\S", zeile)
            if m:
                aktiv.add((name, m.group(1)))
    return aktiv


def yaml_setzen(pfad: str, werte: list[tuple[str, str, str]]) -> None:
    """Werte in ihre Abschnitte schreiben; Reihenfolge, Einrueckung und
    Kommentare der Vorlage bleiben erhalten."""
    with open(pfad, encoding="utf-8", errors="replace") as fh:
        zeilen = fh.read().splitlines()

    offen = list(werte)
    for abschnitt, schluessel, wert in list(werte):
        for name, start, ende in _abschnitte(zeilen):
            if name != abschnitt:
                continue
            for i in range(start + 1, ende):
                m = re.match(r"^(\s+)(#\s*)?([A-Za-z_][A-Za-z0-9_]*)(\s*:\s*)(.*)$", zeilen[i])
                if not m or m.group(3) != schluessel:
                    continue
                rest = m.group(5)
                kommentar = ("  " + rest[rest.index("#"):]) if "#" in rest else ""
                zeilen[i] = "%s%s: %s%s" % (m.group(1), schluessel, wert, kommentar)
                offen.remove((abschnitt, schluessel, wert))
                break
            break

    # fehlende Schluessel in ihren Abschnitt einsetzen
    for abschnitt, schluessel, wert in list(offen):
        block = next(((n, s, e) for n, s, e in _abschnitte(zeilen) if n == abschnitt), None)
        if not block:
            continue
        name, start, ende = block
        einzug = None
        for i in range(start + 1, ende):
            m2 = re.match(r"^(\s+)\S", zeilen[i])
            if m2:
                einzug = m2.group(1)
                break
        einzug = einzug or "    "
        zeilen[ende:ende] = ["%s%s: %s" % (einzug, schluessel, wert)]
        offen.remove((abschnitt, schluessel, wert))

    # Streuner auf oberster Ebene entfernen (Server verweigert sonst den Start)
    streuner = {"Srv_", "Tel_", "EACActive", "GameName", "Mode", "CustomScenario",
                "MaxAllowedSizeClass", "AllowedBlueprints", "SaveDirectory",
                "HeartbeatServer", "TimeoutBootingPfServer"}
    zeilen = [z for z in zeilen
              if not (re.match(r"^[A-Za-z_][A-Za-z0-9_]*\s*:", z)
                      and any(re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:", z).group(1).startswith(s)
                              for s in streuner))]

    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen) + "\n")


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
                    "DedicatedServer/EmpyrionDedicated.exe (-batchmode -nographics); "
                    "alle Einstellungen stehen in dedicated.yaml und im Reiter "
                    "\"Einstellungen\".")

    settings_fields = (
        ("session_name", "Server-Name", "Name in der Serverliste (Srv_Name)", "text"),
        ("max_players", "Max. Spieler", "Srv_MaxPlayers", "int"),
        ("port", "Spielport (UDP)", "Srv_Port, Standard 30000", "int"),
        ("server_password", "Server-Passwort", "Beitritt nur mit Passwort (leer = offen)",
         "password"),
    )

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

    # ---------------------------------------------------------- Einstellungen
    def settings(self, inst) -> list[dict]:
        """Alle Schluessel aus dedicated.yaml anbieten (nicht nur die vier Panel-Felder)."""
        pfad = self.config_path(inst)
        datei = yaml_lesen(pfad) if os.path.exists(pfad) else {}
        aktiv = yaml_aktiv(pfad) if os.path.exists(pfad) else set()
        out = []
        for abschnitt, schluessel, label, hinweis, typ, gruppe in FELDER:
            wert = datei.get(abschnitt, {}).get(schluessel, "")
            # Auskommentierte Vorlagenwerte nicht als "gesetzt" anzeigen - sonst
            # steht beim Passwort das Beispiel aus der Datei.
            if typ == "password" and (abschnitt, schluessel) not in aktiv:
                wert = ""
            if not wert and schluessel in SPIEGEL:
                wert = str(getattr(inst, SPIEGEL[schluessel], "") or "")
            out.append({"file": "instance", "section": abschnitt, "key": schluessel,
                        "label": label, "hint": hinweis, "type": typ,
                        "value": wert, "group": gruppe})
        return out

    def apply_settings(self, inst, items) -> int:
        """Werte aus dem Formular in dedicated.yaml schreiben."""
        pfad = self.config_path(inst)
        if not os.path.exists(pfad):
            return 0
        erlaubt = {(a, s): (t, g) for a, s, _l, _h, t, g in FELDER}
        werte: list[tuple[str, str, str]] = []
        geaendert = 0
        for item in items:
            schluessel = str(item.get("key") or "")
            treffer = next((k for k in erlaubt if k[1] == schluessel), None)
            if not treffer:
                continue
            abschnitt, typ = treffer[0], erlaubt[treffer][0]
            wert = str(item.get("value", "")).strip()
            if typ in ("int",):
                if not wert:
                    continue
                if not re.fullmatch(r"-?\d+", wert):
                    continue
            elif typ == "text" and schluessel not in ("Srv_Description", "AllowedBlueprints"):
                if re.fullmatch(r"(true|false)", wert, re.I):
                    pass
                elif not wert:
                    continue
            if typ == "password" and not wert:
                continue          # leeres Feld ueberschreibt kein vorhandenes Passwort
            if typ in ("text", "password") and not re.fullmatch(r"-?\d+", wert):
                if not re.fullmatch(r"(true|false)", wert, re.I):
                    wert = '"%s"' % wert.replace('"', "")
            werte.append((abschnitt, schluessel, wert))
            inst_feld = SPIEGEL.get(schluessel)
            if inst_feld:
                alt = getattr(inst, inst_feld, "")
                setattr(inst, inst_feld, int(wert) if isinstance(alt, int) and wert.isdigit()
                        else wert.strip('"'))
            geaendert += 1
        if werte:
            yaml_setzen(pfad, werte)
        return geaendert

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
        """Nur die Panel-Felder schreiben; alles andere bleibt, wie es ist."""
        pfad = self.config_path(inst)
        if not os.path.exists(pfad):
            return          # Vorlage fehlt (noch nicht installiert): nichts erfinden
        passwort = (getattr(inst, "server_password", "") or "").strip()
        werte = [
            ("ServerConfig", "Srv_Name",
             '"%s"' % (getattr(inst, "session_name", "") or inst.name)),
            ("ServerConfig", "Srv_Port",
             str(getattr(inst, "port", self.default_game_port) or self.default_game_port)),
            ("ServerConfig", "Srv_MaxPlayers",
             str(getattr(inst, "max_players", self.default_max_players))),
        ]
        if passwort:
            werte.append(("ServerConfig", "Srv_Password", '"%s"' % passwort))
        yaml_setzen(pfad, werte)

    # ---------------------------------------------------------- Steuerkanal
    def ready(self, inst) -> bool:
        return _udp_port_bound(int(getattr(inst, "port", self.default_game_port)))

    def players(self, inst):
        return None
