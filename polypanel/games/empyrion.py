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
OPTIONS = "gameoptions.yaml"

# Passwort-artige Schluessel werden im Formular maskiert
PASSWORT_MUSTER = ("password", "pwd", "secret", "token", "clientid")

# Deutsche Bezeichnungen; alles ohne Eintrag zeigt den YAML-Schluessel
LABEL = {
    "Srv_Name": "Server-Name", "Srv_Port": "Spielport (UDP)",
    "Srv_MaxPlayers": "Max. Spieler", "Srv_Password": "Server-Passwort",
    "Srv_Description": "Beschreibung", "Srv_Public": "In Serverliste zeigen",
    "Srv_ReservePlayfields": "Reserve-Playfields", "Srv_StopPeriod": "Auto-Neustart (Std.)",
    "Tel_Enabled": "Telnet an", "Tel_Port": "Telnet-Port", "Tel_Pwd": "Telnet-Passwort",
    "EACActive": "Easy Anti-Cheat", "SaveDirectory": "Speicherordner",
    "MaxAllowedSizeClass": "Max. Bauklasse", "AllowedBlueprints": "Erlaubte Blueprints",
    "HeartbeatServer": "Heartbeat Server (s)", "HeartbeatClient": "Heartbeat Client (s)",
    "LogFlags": "Log-Flags", "DisableSteamFamilySharing": "Steam Family Sharing sperren",
    "KickPlayerWithPing": "Kick ab Ping (ms)", "TimeoutBootingPfServer": "Start-Timeout (s)",
    "PlayerLoginParallelCount": "Parallele Logins", "PlayerLoginVipNames": "VIP-Logins",
    "EnableDLC": "DLC erlauben", "GameName": "Spielstand-Name", "Mode": "Modus",
    "Seed": "Welten-Seed", "CustomScenario": "Szenario", "Notes": "Notizen",
    "SharedDataURL": "Shared-Data-URL",
}


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


def _zeilen(pfad: str) -> list[str]:
    """Dateiinhalt als Zeilen (leer, wenn nicht lesbar)."""
    try:
        with open(pfad, encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


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


def yaml_hinweise(pfad: str) -> dict[tuple[str, str], str]:
    """Kommentartext hinter einem Schluessel - dient als Hinweis im Formular."""
    out: dict[tuple[str, str], str] = {}
    zeilen = _zeilen(pfad)
    for name, start, ende in _abschnitte(zeilen):
        for zeile in zeilen[start + 1:ende]:
            m = re.match(r"^\s+(#\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", zeile)
            if not m:
                continue
            rest = m.group(3)
            if "#" in rest:
                text = rest[rest.index("#") + 1:].strip() or rest[:rest.index("#")].strip()
                if text:
                    out[(name, m.group(2))] = text[:120]
    return out


def yaml_aktiv(pfad: str) -> set[tuple[str, str]]:
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


# ------------------------------------------------------- gameoptions.yaml (MP)
def _options_block(zeilen) -> tuple[int, int] | None:
    """Zeilengrenzen des Mehrspieler-Blocks (ValidFor enthaelt MP)."""
    start = None
    for i, zeile in enumerate(zeilen):
        m = re.match(r"^\s*-\s*ValidFor:\s*\[(.*?)\]", zeile)
        if not m:
            continue
        if start is not None:
            return start, i
        if "MP" in m.group(1).upper():
            start = i
    return (start, len(zeilen)) if start is not None else None


def gameoptions_lesen(pfad: str) -> dict[str, str]:
    zeilen = _zeilen(pfad)
    block = _options_block(zeilen)
    if not block:
        return {}
    start, ende = block
    werte = {}
    for zeile in zeilen[start:ende]:
        m = re.match(r"^\s+(#\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", zeile)
        if not m:
            continue
        wert = m.group(3)
        if "#" in wert:
            wert = wert[:wert.index("#")]
        werte[m.group(2)] = wert.strip().strip('"').strip("'")
    return werte


def gameoptions_hinweise(pfad: str) -> dict[str, str]:
    zeilen = _zeilen(pfad)
    block = _options_block(zeilen)
    out: dict[str, str] = {}
    if not block:
        return out
    start, ende = block
    for zeile in zeilen[start:ende]:
        m = re.match(r"^\s+(#\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$", zeile)
        if not m or "#" not in m.group(3):
            continue
        text = m.group(3)[m.group(3).index("#") + 1:].strip()
        if text:
            out.setdefault(m.group(2), text[:120])
    return out


def gameoptions_setzen(pfad: str, werte: dict[str, str]) -> int:
    zeilen = _zeilen(pfad)
    block = _options_block(zeilen)
    if not block:
        return 0
    start, ende = block
    geaendert = 0
    for i in range(start, ende):
        m = re.match(r"^(\s+)(#\s*)?([A-Za-z_][A-Za-z0-9_]*)(\s*:\s*)(.*)$", zeilen[i])
        if not m or m.group(3) not in werte:
            continue
        schluessel = m.group(3)
        rest = m.group(5)
        kommentar = ("  " + rest[rest.index("#"):]) if "#" in rest else ""
        zeilen[i] = "%s%s: %s%s" % (m.group(1), schluessel, werte.pop(schluessel), kommentar)
        geaendert += 1
    einzug = "    "
    for zeile in zeilen[start:ende]:
        m2 = re.match(r"^(\s+)\S", zeile)
        if m2:
            einzug = m2.group(1)
            break
    for schluessel, wert in list(werte.items()):
        zeilen.insert(ende, "%s%s: %s" % (einzug, schluessel, wert))
        ende += 1
        geaendert += 1
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen) + "\n")
    return geaendert


# ------------------------------------------------------------- Adminrechte
def admins_pfad(inst) -> str:
    return os.path.join(inst.directory, "Saves", "adminconfig.yaml")


def admins_lesen(pfad: str) -> list[tuple[str, str]]:
    """Elevated-Eintraege als (SteamID64, Stufe)."""
    aus: list[tuple[str, str]] = []
    im_block = False
    for zeile in _zeilen(pfad):
        if re.match(r"^Elevated:\s*$", zeile):
            im_block = True
            continue
        if im_block and re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", zeile):
            break
        m = re.match(r"^\s*-?\s*Id:\s*(\d+)\s*(#.*)?$", zeile)
        if im_block and m:
            aus.append((m.group(1), ""))
            continue
        m = re.match(r"^\s*Permission:\s*(\d+)", zeile)
        if im_block and m and aus:
            aus[-1] = (aus[-1][0], m.group(1))
    return aus


def admins_setzen(pfad: str, eintraege: list[tuple[str, str]], vorlage: str = "") -> bool:
    """Elevated-Block neu schreiben; alles andere in der Datei bleibt."""
    zeilen = _zeilen(pfad)
    if not zeilen and vorlage and os.path.exists(vorlage):
        zeilen = _zeilen(vorlage)
    block = ["Elevated:"]
    for steamid, stufe in eintraege:
        block.append("- Id: %s" % steamid)
        block.append("  Permission: %s" % (stufe or "3"))

    start = next((i for i, z in enumerate(zeilen) if re.match(r"^Elevated:\s*$", z)), None)
    if start is None:
        zeilen = block + ([""] if zeilen else []) + zeilen
    else:
        ende = len(zeilen)
        for i in range(start + 1, len(zeilen)):
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*:\s*$", zeilen[i]):
                ende = i
                break
        zeilen[start:ende] = block + ([""] if ende < len(zeilen) else [])

    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen) + "\n")
    return True


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

    def options_path(self, inst) -> str:
        """gameoptions.yaml des eingestellten Szenarios (Spielregeln)."""
        szenario = (yaml_lesen(self.config_path(inst)).get("GameConfig", {})
                    .get("CustomScenario") or "Default Multiplayer")
        return os.path.join(inst.directory, "Content", "Scenarios", szenario, OPTIONS)

    def log_path(self, inst) -> str:
        for muster in ("Logs/*.log", "*.log"):
            treffer = sorted(glob.glob(os.path.join(inst.directory, muster)))
            if treffer:
                return treffer[-1]
        ordner = os.path.join(inst.directory, "Logs")
        os.makedirs(ordner, exist_ok=True)
        return os.path.join(ordner, "EmpyrionDedicated.log")

    # ---------------------------------------------------------- Einstellungen
    @staticmethod
    def _typ(schluessel: str, wert: str) -> str:
        if any(m in schluessel.lower() for m in PASSWORT_MUSTER):
            return "password"
        if re.fullmatch(r"-?\d+", wert or ""):
            return "int"
        return "text"

    def settings(self, inst) -> list[dict]:
        """dedicated.yaml (alle Schluessel), gameoptions.yaml (MP-Block) und Adminliste."""
        cfg_pfad = self.config_path(inst)
        datei = yaml_lesen(cfg_pfad) if os.path.exists(cfg_pfad) else {}
        hinweise = yaml_hinweise(cfg_pfad) if os.path.exists(cfg_pfad) else {}
        aktiv = yaml_aktiv(cfg_pfad) if os.path.exists(cfg_pfad) else set()

        out: list[dict] = []
        for abschnitt in ("ServerConfig", "GameConfig"):
            for schluessel, wert in datei.get(abschnitt, {}).items():
                typ = self._typ(schluessel, wert)
                if typ == "password" and (abschnitt, schluessel) not in aktiv:
                    wert = ""      # auskommentierter Vorlagenwert ist nicht gesetzt
                if not wert and schluessel in SPIEGEL:
                    wert = str(getattr(inst, SPIEGEL[schluessel], "") or "")
                out.append({"file": "instance", "section": abschnitt, "key": schluessel,
                            "label": LABEL.get(schluessel, schluessel),
                            "hint": hinweise.get((abschnitt, schluessel), ""),
                            "type": typ, "value": wert,
                            "group": "game" if abschnitt == "GameConfig" else "srv"})

        opt_pfad = self.options_path(inst)
        if os.path.exists(opt_pfad):
            opt_h = gameoptions_hinweise(opt_pfad)
            for schluessel, wert in gameoptions_lesen(opt_pfad).items():
                out.append({"file": "opts", "section": "Options (MP)", "key": schluessel,
                            "label": LABEL.get(schluessel, schluessel),
                            "hint": opt_h.get(schluessel, ""),
                            "type": self._typ(schluessel, wert), "value": wert,
                            "group": "game"})

        apfad = admins_pfad(inst)
        eintraege = admins_lesen(apfad)
        out.append({"file": "admins", "section": "", "key": "Elevated",
                    "label": "Admins", "type": "text",
                    "hint": "SteamID64:Stufe, mehrere durch Komma — 3 GameMaster, 6 Moderator, 9 Admin",
                    "value": ", ".join("%s:%s" % (i, s or "3") for i, s in eintraege),
                    "group": "srv"})
        return out

    def apply_settings(self, inst, items) -> int:
        """Werte in dedicated.yaml, gameoptions.yaml bzw. adminconfig.yaml schreiben."""
        cfg_pfad = self.config_path(inst)
        opt_pfad = self.options_path(inst)
        apfad = admins_pfad(inst)

        cfg_abschnitt: dict[str, str] = {}
        if os.path.exists(cfg_pfad):
            for abschnitt, werte in yaml_lesen(cfg_pfad).items():
                for schluessel in werte:
                    cfg_abschnitt[schluessel] = abschnitt
        opt_keys = set(gameoptions_lesen(opt_pfad)) if os.path.exists(opt_pfad) else set()

        cfg_werte: list[tuple[str, str, str]] = []
        opt_werte: dict[str, str] = {}
        admin_text = None
        geaendert = 0

        for item in items:
            schluessel = str(item.get("key") or "")
            wert = str(item.get("value", "")).strip()

            if schluessel == "Elevated":
                admin_text = wert
                geaendert += 1
                continue

            if schluessel in cfg_abschnitt:
                typ = self._typ(schluessel, wert)
                if typ == "password" and not wert:
                    continue
                if typ == "int" and not re.fullmatch(r"-?\d+", wert):
                    continue
                if typ == "text" and not re.fullmatch(r"(true|false|-?\d+)", wert, re.I) \
                        and schluessel not in ("Srv_Description", "Notes", "AllowedBlueprints",
                                               "PlayerLoginVipNames", "SharedDataURL", "Mode",
                                               "CustomScenario", "GameName", "SaveDirectory"):
                    wert = '"%s"' % wert.replace('"', "")
                cfg_werte.append((cfg_abschnitt[schluessel], schluessel, wert))
                inst_feld = SPIEGEL.get(schluessel)
                if inst_feld:
                    alt = getattr(inst, inst_feld, "")
                    setattr(inst, inst_feld,
                            int(wert) if isinstance(alt, int) and wert.lstrip("-").isdigit()
                            else wert.strip('"'))
                geaendert += 1
                continue

            if schluessel in opt_keys:
                typ = self._typ(schluessel, wert)
                if typ == "password" and not wert:
                    continue
                if typ == "int" and not re.fullmatch(r"-?\d+", wert):
                    continue
                if typ == "text" and not re.fullmatch(r"(true|false|None|-?\d+)", wert, re.I) \
                        and " " not in wert and not re.fullmatch(r"[A-Za-z0-9_,.]+", wert):
                    wert = '"%s"' % wert.replace('"', "")
                opt_werte[schluessel] = wert
                geaendert += 1

        if cfg_werte:
            yaml_setzen(cfg_pfad, cfg_werte)
        if opt_werte:
            gameoptions_setzen(opt_pfad, dict(opt_werte))
        if admin_text is not None:
            liste: list[tuple[str, str]] = []
            for teil in re.split(r"[,;\n]", admin_text):
                teil = teil.strip()
                if not teil:
                    continue
                m = re.match(r"^(\d{10,20})\s*[:/ ]\s*(\d+)$", teil)
                if m:
                    liste.append((m.group(1), m.group(2)))
                elif re.fullmatch(r"\d{10,20}", teil):
                    liste.append((teil, "9"))
            admins_setzen(apfad, liste,
                          vorlage=os.path.join(inst.directory, "Saves",
                                               "adminconfig.example.yaml"))
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
