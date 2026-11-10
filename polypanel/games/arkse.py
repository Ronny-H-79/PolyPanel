"""ARK: Survival Evolved, Dedicated Server (Linux, nativ).

Steam-App-ID 376030. Anders als ARK: Survival Ascended laeuft ASE nativ unter
Linux (`ShooterGameServer`), kennt aber dieselbe Konfiguration:

  ShooterGame/Saved/Config/LinuxServer/GameUserSettings.ini   [ServerSettings] ...
  ShooterGame/Saved/Config/LinuxServer/Game.ini               [/script/shootergame.shootergamemode]

Steuerung ueber Source-RCON (Port aus GameUserSettings.ini, Passwort =
ServerAdminPassword). Mods sind Steam-Workshop-IDs, die ASE beim Start ueber
`-automanagedmods` selbst laedt.
"""
from __future__ import annotations

import configparser
import glob
import os
import re

from .base import GameProfile, _tcp_open
from .arkse_labels import GROUPS, LABELS

BIN_REL = os.path.join("ShooterGame", "Binaries", "Linux", "ShooterGameServer")
CONFIG_REL = os.path.join("ShooterGame", "Saved", "Config", "LinuxServer")
LOG_REL = os.path.join("ShooterGame", "Saved", "Logs", "ShooterGame.log")
SECTION_GAME = "/script/shootergame.shootergamemode"

TEMPLATE_GUS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arkse_template_gus.ini")
TEMPLATE_GAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arkse_template_game.ini")


def _load_template(path: str) -> list[tuple[str, list[tuple[str, str]]]]:
    """Default-Werte aus der mitgelieferten ASE-Vorlage (eine Sektion je Eintrag)."""
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    cp.read(path, encoding="utf-8")
    return [(section, list(cp.items(section))) for section in cp.sections()]


# Vollstaendige ASE-Eigenschaften (ServerSettings 160, SessionSettings 3, MOTD 2, Game.ini 100)
GUS_TEMPLATE = _load_template(TEMPLATE_GUS)
GAME_TEMPLATE = _load_template(TEMPLATE_GAME)

# Instanz-Attribut <-> INI-Eigenschaft
ALIASES = {
    "SessionName": "session_name",
    "Port": "port",
    "QueryPort": "query_port",
    "RCONPort": "rcon_port",
    "MaxPlayers": "max_players",
}

# ASE schreibt Schluessel in gemischter Schreibweise (serverPVE, globalVoiceChat) -
# Nachschlagen deshalb immer ueber die Kleinschreibung.
_LABELS = {k.lower(): v for k, v in LABELS.items()}
_GROUPS = {k.lower(): v for k, v in GROUPS.items()}
_ALIASES = {k.lower(): v for k, v in ALIASES.items()}


class ArkSeProfile(GameProfile):
    key = "arkse"
    label = "ARK: Survival Evolved"
    server_app_id = "376030"
    control_kind = "source"
    needs_wine = False
    default_game_port = 7777
    default_query_port = 27015
    default_control_port = 27020
    supports_mods = True
    supports_cluster = True
    install_note = "nativ (Linux), ca. 20 GB"
    maps = (
        ("TheIsland", "The Island"),
        ("Ragnarok", "Ragnarok"),
        ("ScorchedEarth_P", "Scorched Earth"),
        ("TheCenter", "The Center"),
        ("Aberration_P", "Aberration"),
        ("Extinction", "Extinction"),
        ("Valguero_P", "Valguero"),
        ("Genesis", "Genesis"),
        ("CrystalIsles", "Crystal Isles"),
        ("Gen2", "Genesis 2"),
        ("LostIsland", "Lost Island"),
        ("Fjordur", "Fjordur"),
    )
    settings_fields = (
        ("session_name", "Spieleserver-Name", "erscheint in der Serverliste", "text"),
        ("map", "Karte", "Weltenname (z. B. TheIsland, Ragnarok, Fjordur)", "text"),
        ("max_players", "Max. Spieler", "gleichzeitige Spieler", "int"),
        ("port", "Spiel-Port", "UDP, Spielverbindung", "int"),
        ("query_port", "Query-Port", "UDP, Serverliste", "int"),
        ("rcon_port", "RCON-Port", "TCP, Steuerkanal", "int"),
        ("admin_password", "Admin-Passwort", "gilt auch fuer RCON", "password"),
    )

    # ---------------------------------------------------------------- Pfade
    def exe(self, inst) -> str:
        return os.path.join(inst.directory, BIN_REL)

    def workdir(self, inst) -> str:
        # ASE findet seine Bibliotheken nur im eigenen Verzeichnis.
        return os.path.dirname(self.exe(inst))

    def config_dir(self, inst) -> str:
        return os.path.join(inst.directory, CONFIG_REL)

    def gus_ini(self, inst) -> str:
        return os.path.join(self.config_dir(inst), "GameUserSettings.ini")

    def game_ini(self, inst) -> str:
        return os.path.join(self.config_dir(inst), "Game.ini")

    def log_path(self, inst) -> str:
        # ASE schreibt ShooterGame.log und rotiert nach ShooterGame-backup-*.log
        ordner = os.path.join(inst.directory, "ShooterGame", "Saved", "Logs")
        kandidaten = glob.glob(os.path.join(ordner, "ShooterGame*.log"))
        fest = os.path.join(inst.directory, LOG_REL)
        if os.path.exists(fest) and fest not in kandidaten:
            kandidaten.append(fest)
        if kandidaten:
            return max(kandidaten, key=os.path.getmtime)
        return inst.console_log

    def mods_path(self, inst) -> str:
        return os.path.join(inst.directory, "ShooterGame", "Content", "Mods")

    # ------------------------------------------------------------ Startzeile
    def admin_pw(self, inst) -> str:
        return inst.admin_password or inst.rcon_password

    def launch_argv(self, inst) -> list[str]:
        self.write_config(inst)
        url = "%s?listen?SessionName=%s?Port=%d?QueryPort=%d?RCONEnabled=True?RCONPort=%d" % (
            inst.map or self.maps[0][0], inst.session_name or "ARK", inst.port,
            inst.query_port, inst.rcon_port)
        if self.admin_pw(inst):
            url += "?ServerAdminPassword=" + self.admin_pw(inst)
        argv = [self.exe(inst), url, "-server", "-log", "-NoBattlEye",
                "-servergamelog", "-servergamelogincludetribelogs",
                "-MaxPlayers=%d" % inst.max_players]
        if inst.cluster_name:
            argv.append("-ClusterDirOverride=" + inst.cluster_path)
            argv.append("-clusterid=" + inst.cluster_name)
            if inst.cluster_transfer_filtering:
                argv.append("-NoTransferFromFiltering")
        if inst.mods:
            argv.append("-automanagedmods")
        if inst.exclusive_join:
            argv.append("-exclusivejoin")
        if inst.extra_args:
            argv.extend(inst.extra_args.split())
        return argv

    # ---------------------------------------------------------- Konfigdatei
    def _canonical(self) -> dict[str, str]:
        """Kleinschreibung -> offizielle Schreibweise aus den Vorlagen."""
        table: dict[str, str] = {}
        for _section, liste in GUS_TEMPLATE + GAME_TEMPLATE:
            for key, _val in liste:
                table.setdefault(key.lower(), key)
        return table

    def _read_ini(self, path: str) -> configparser.ConfigParser:
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        cp.optionxform = str
        if os.path.exists(path):
            try:
                cp.read(path, encoding="utf-8-sig")
            except (configparser.Error, OSError):
                pass
        self._dedupe_case(cp)
        return cp

    def _dedupe_case(self, cp: configparser.ConfigParser) -> None:
        """Doppelte Schluessel mit anderer Schreibweise zusammenfassen.

        ASE liest Konfigurationsschluessel ohne Ruecksicht auf Gross-/Kleinschreibung.
        Stehen `ServerPVE` und `serverPVE` nebeneinander (etwa aus einer aelteren
        Vorlage), ist unklar, welcher Wert gilt - hier bleibt der offizielle Name
        mit dem zuletzt gelesenen Wert stehen.
        """
        table = self._canonical()
        for section in cp.sections():
            werte: dict[str, str] = {}
            for key, value in cp.items(section):
                werte[self._canonical_key(key, table)] = value      # letzter gewinnt
            if [k for k, _v in cp.items(section)] == list(werte):
                continue
            cp.remove_section(section)
            cp.add_section(section)
            for key, value in werte.items():
                cp.set(section, key, value)

    @staticmethod
    def _canonical_key(key: str, table: dict[str, str]) -> str:
        return table.get(key.lower(), key)

    def write_config(self, inst) -> None:
        """Ports, RCON, Name und Mods in die INIs schreiben (idempotent)."""
        os.makedirs(self.config_dir(inst), exist_ok=True)
        werte = {
            "RCONPort": str(inst.rcon_port),
            "ServerAdminPassword": self.admin_pw(inst),
            "MaxPlayers": str(inst.max_players),
        }
        cp = self._read_ini(self.gus_ini(inst))
        for section, liste in GUS_TEMPLATE:
            if not cp.has_section(section):
                cp.add_section(section)
            for key, val in liste:
                if key in werte:
                    val = werte[key]
                if not cp.has_option(section, key):
                    cp.set(section, key, val)
        # Kernwerte immer aus der Instanz ziehen
        port_werte = {
            "SessionSettings": {
                "SessionName": inst.session_name or "ARK",
                "Port": str(inst.port),
                "QueryPort": str(inst.query_port),
            },
            "ServerSettings": {
                "ActiveMods": ",".join(str(m) for m in inst.mods),   # ASE liest Mods hier
                "RCONEnabled": "True",
                "RCONPort": str(inst.rcon_port),
                "ServerAdminPassword": self.admin_pw(inst),
                "MaxPlayers": str(inst.max_players),
            },
        }
        for section, kv in port_werte.items():
            if not cp.has_section(section):
                cp.add_section(section)
            for key, val in kv.items():
                cp.set(section, key, val)
        with open(self.gus_ini(inst), "w", encoding="utf-8") as fh:
            cp.write(fh, space_around_delimiters=False)

        cp2 = self._read_ini(self.game_ini(inst))
        for section, liste in GAME_TEMPLATE:
            if not cp2.has_section(section):
                cp2.add_section(section)
            for key, val in liste:
                if not cp2.has_option(section, key):
                    cp2.set(section, key, val)
        with open(self.game_ini(inst), "w", encoding="utf-8") as fh:
            cp2.write(fh, space_around_delimiters=False)

    # ---------------------------------------------------------- Einstellungen
    def _gruppierung(self, key: str) -> str:
        return _GROUPS.get(str(key).lower(), "weitere")

    def _typ(self, key: str, value: str) -> str:
        if "password" in key.lower() or "token" in key.lower():
            return "password"
        text = str(value).strip().strip('"')
        if re.fullmatch(r"-?\d+", text):
            return "int"
        if re.fullmatch(r"-?\d+[.,]\d+", text):
            return "text"
        if text.lower() in ("true", "false"):
            return "bool"
        return "text"

    def settings(self, inst) -> list[dict]:
        out: list[dict] = []
        dateien = (("gus", self.gus_ini(inst)), ("game", self.game_ini(inst)))
        if not any(os.path.exists(p) for _f, p in dateien):
            return super().settings(inst)          # vor dem ersten Start
        # Die Karte steht nur in der Startzeile, nicht in einer INI
        out.append({"file": "instance", "section": "Startzeile", "key": "map",
                    "label": "Karte", "hint": "Weltenname in der Startzeile (Neustart nötig)",
                    "type": "text", "value": str(inst.map), "group": "srv"})
        for filekey, pfad in dateien:
            cp = self._read_ini(pfad)
            for section in cp.sections():
                for key, value in cp.items(section):
                    if key.lower() == "activemods":
                        value = ",".join(str(m) for m in inst.mods)
                    alias = _ALIASES.get(str(key).lower())
                    if alias:
                        value = str(getattr(inst, alias, value))
                    label, hint = _LABELS.get(str(key).lower(), (key, ""))
                    out.append({"file": filekey, "section": section, "key": key,
                                "label": label, "hint": hint,
                                "type": self._typ(key, value), "value": str(value),
                                "group": self._gruppierung(key)})
        return out

    def apply_settings(self, inst, items) -> int:
        """Werte in die jeweilige INI schreiben und die Kernfelder nachziehen."""
        dateien = {"gus": self.gus_ini(inst), "game": self.game_ini(inst)}
        geaendert = 0
        geoeffnet: dict[str, configparser.ConfigParser] = {}
        for item in items:
            key = item.get("key")
            if not key:
                continue
            filekey = item.get("file") or "gus"
            if filekey == "instance":                  # Kernfelder (z. B. map)
                geaendert += super().apply_settings(inst, [item])
                continue
            section = item.get("section") or ("ServerSettings" if filekey == "gus" else SECTION_GAME)
            val = str(item.get("value", ""))
            pfad = dateien.get(filekey, dateien["gus"])
            if not os.path.exists(pfad):
                continue
            cp = geoeffnet.setdefault(pfad, self._read_ini(pfad))
            if not cp.has_section(section):
                cp.add_section(section)
            cp.set(section, key, val)
            alias = _ALIASES.get(str(key).lower())
            if alias:
                cur = getattr(inst, alias, "")
                try:
                    setattr(inst, alias, int(val) if isinstance(cur, int) else val)
                except (TypeError, ValueError):
                    pass
            if key.lower() == "activemods":
                inst.mods = [int(p) for p in val.replace(" ", "").split(",") if p.isdigit()]
            if key.lower() == "serveradminpassword":
                inst.admin_password = val
            geaendert += 1
        for pfad, cp in geoeffnet.items():
            with open(pfad, "w", encoding="utf-8") as fh:
                cp.write(fh, space_around_delimiters=False)
        if geaendert == 0:
            return super().apply_settings(inst, items)
        return geaendert

    # ---------------------------------------------------------- Steuerkanal
    def control(self, inst, timeout: float = 10.0):
        from ..rcon import RconClient
        return RconClient("127.0.0.1", inst.rcon_port, self.admin_pw(inst), timeout=timeout)

    def ready(self, inst) -> bool:
        """RCON nimmt Verbindungen an, sobald die Welt geladen ist."""
        return _tcp_open("127.0.0.1", inst.rcon_port, timeout=2)

    def graceful_stop(self, inst) -> list[str]:
        steps: list[str] = []
        with self.control(inst, timeout=15) as rc:
            rc.command("SaveWorld", timeout=25)
            steps.append("SaveWorld ok")
            rc.command("DoExit", timeout=8)
            steps.append("DoExit gesendet")
        return steps

    # ------------------------------------------------------------- Mods
    WORKSHOP_APP = "346110"       # Steam-Workshop von ARK: Survival Evolved
    WORKSHOP_URL = "https://steamcommunity.com/workshop/browse/"

    def _workshop(self, query: str, page: int = 1) -> dict:
        """Steam-Workshop durchsuchen (Volltext) und die Trefferliste liefern.

        Die Workshop-Seite bettet ihren Zustand als JSON in `valve-ssr-data` ein;
        darin steht unter `renderContext.queryData` die Antwort von Steam. Kein
        API-Key nötig, kein Login - deshalb der kleine Umweg über das HTML.
        """
        import json as _json
        import re as _re
        import urllib.parse
        import urllib.request

        url = (self.WORKSHOP_URL + "?appid=%s&searchtext=%s&browsesort=textsearch"
               "&section=readytouseitems&p=%d"
               % (self.WORKSHOP_APP, urllib.parse.quote_plus(query), max(1, page)))
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) PolyPanel",
            "Accept-Language": "de,en;q=0.8"})
        with urllib.request.urlopen(req, timeout=25) as resp:
            html = resp.read().decode("utf-8", "replace")
        m = _re.search(r'id="valve-ssr-data"[^>]*>(.*?)</script>', html, _re.S)
        if not m:
            raise RuntimeError("Workshop-Seite ohne Daten (Steam liefert eine andere Seite)")
        ssr = _json.loads(m.group(1))
        raw = ssr.get("renderContext", {}).get("queryData")
        if not raw:
            raise RuntimeError("Workshop-Antwort ohne Trefferliste")
        qd = _json.loads(raw)
        for q in qd.get("queries") or []:
            data = (q.get("state") or {}).get("data")
            if isinstance(data, dict) and isinstance(data.get("results"), list):
                return data
        return {"results": [], "total_count": 0}

    @staticmethod
    def _clean(text: str, limit: int = 150) -> str:
        """BBCode/HTML/Markdown-Reste aus der Workshop-Beschreibung entfernen."""
        import re as _re
        text = _re.sub(r"\[/?[a-zA-Z0-9=*#;:,\.\s\"'\-]+\]", " ", str(text or ""))
        text = _re.sub(r"<[^>]+>", " ", text)
        text = _re.sub(r"\*{1,3}|_{2,}|`{1,3}", "", text)     # **fett**, __unterstrichen__, `code`
        text = _re.sub(r"https?://\S+", "", text)             # nackte Links weg
        text = _re.sub(r"\s+", " ", text).strip()
        return text[:limit]

    def workshop_ids(self, inst) -> list[str]:
        return [str(m) for m in inst.mods]

    def mods_search(self, inst, query: str) -> dict:
        """Steam-Workshop von ARK Evolved durchsuchen (App 346110, ohne Key)."""
        from . import steam_workshop
        data = steam_workshop.hits(self.WORKSHOP_APP, query, limit=24)
        vorhanden = set(self.workshop_ids(inst))
        for treffer in data.get("results") or []:
            treffer["installed"] = str(treffer.get("id")) in vorhanden
        return data

    def mods_install(self, inst, mod_id: str, log=print) -> str:
        """Workshop-ID eintragen (ASE lädt die Mod beim Start selbst)."""
        from ..control import ControlError
        mid = str(mod_id).strip()
        if not mid.isdigit():
            raise ControlError("Das ist keine Workshop-ID (nur Ziffern)")
        nummer = int(mid)
        if nummer in inst.mods:
            return "Mod %s ist bereits eingetragen." % mid
        inst.mods.append(nummer)
        self.write_config(inst)
        log("Workshop-ID %s eingetragen" % mid)
        return ("Workshop-ID %s eingetragen - ARK Evolved lädt die Mod beim nächsten Start "
                "(-automanagedmods)." % mid)
