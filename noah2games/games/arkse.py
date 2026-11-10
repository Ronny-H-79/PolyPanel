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

# Werte, die beim ersten Schreiben angelegt werden. ASE ergaenzt beim ersten
# Start selbst viele weitere Eigenschaften - die Oberflaeche zeigt sie danach
# automatisch, weil sie die INI-Dateien vollstaendig liest.
GUS_TEMPLATE = {
    "ServerSettings": [
        ("RCONEnabled", "True"),
        ("RCONPort", ""),
        ("ServerAdminPassword", ""),
        ("ServerPassword", ""),
        ("MaxPlayers", "20"),
        ("ServerPVE", "True"),
        ("ServerHardcore", "False"),
        ("ServerCrosshair", "True"),
        ("ShowMapPlayerLocation", "True"),
        ("AllowThirdPersonPlayer", "True"),
        ("AllowFlyerCarryPvE", "True"),
        ("GlobalVoiceChat", "False"),
        ("ProximityChat", "False"),
        ("NoTributeDownloads", "False"),
        ("DifficultyOffset", "1.0"),
        ("OverrideOfficialDifficulty", "5.0"),
        ("XPMultiplier", "1.0"),
        ("TamingSpeedMultiplier", "1.0"),
        ("HarvestAmountMultiplier", "1.0"),
        ("HarvestHealthMultiplier", "1.0"),
        ("ResourcesRespawnPeriodMultiplier", "1.0"),
        ("DinoCountMultiplier", "1.0"),
        ("DinoCharacterFoodDrainMultiplier", "1.0"),
        ("PlayerCharacterWaterDrainMultiplier", "1.0"),
        ("PlayerCharacterFoodDrainMultiplier", "1.0"),
        ("PlayerCharacterStaminaDrainMultiplier", "1.0"),
        ("PlayerCharacterHealthRecoveryMultiplier", "1.0"),
        ("DayTimeSpeedScale", "1.0"),
        ("NightTimeSpeedScale", "2.0"),
        ("AutoSavePeriodMinutes", "15.0"),
        ("PvPStructureDecay", "False"),
        ("AllowCaveBuildingPvE", "True"),
        ("PreventSpawnAnimations", "False"),
        ("bDisableStructurePlacementCollision", "False"),
    ],
    "SessionSettings": [
        ("SessionName", ""),
        ("Port", ""),
        ("QueryPort", ""),
    ],
    "MessageOfTheDay": [
        ("Message", ""),
        ("Duration", "20"),
    ],
}

GAME_TEMPLATE = [
    ("ActiveMods", ""),
    ("bDisableStructureDecayPvE", "False"),
    ("PreventDinoTameable", "False"),
    ("MaxTamedDinos", "5000.0"),
    ("TamedDinoCharacterFoodDrainMultiplier", "1.0"),
    ("TamedDinoTorporDrainMultiplier", "1.0"),
    ("WildDinoTorporDrainMultiplier", "1.0"),
    ("PassiveTameIntervalMultiplier", "1.0"),
    ("GlobalSpoilingTimeMultiplier", "1.0"),
    ("GlobalItemDecompositionTimeMultiplier", "1.0"),
    ("GlobalCorpseDecompositionTimeMultiplier", "1.0"),
]

# Instanz-Attribut <-> INI-Eigenschaft
ALIASES = {
    "SessionName": "session_name",
    "Port": "port",
    "QueryPort": "query_port",
    "RCONPort": "rcon_port",
    "MaxPlayers": "max_players",
}


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
    def _read_ini(self, path: str) -> configparser.ConfigParser:
        cp = configparser.ConfigParser(strict=False, interpolation=None)
        cp.optionxform = str
        if os.path.exists(path):
            try:
                cp.read(path, encoding="utf-8-sig")
            except (configparser.Error, OSError):
                pass
        return cp

    def write_config(self, inst) -> None:
        """Ports, RCON, Name und Mods in die INIs schreiben (idempotent)."""
        os.makedirs(self.config_dir(inst), exist_ok=True)
        werte = {
            "RCONPort": str(inst.rcon_port),
            "ServerAdminPassword": self.admin_pw(inst),
            "MaxPlayers": str(inst.max_players),
        }
        cp = self._read_ini(self.gus_ini(inst))
        for section, liste in GUS_TEMPLATE.items():
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
        if not cp2.has_section(SECTION_GAME):
            cp2.add_section(SECTION_GAME)
        for key, val in GAME_TEMPLATE:
            if not cp2.has_option(SECTION_GAME, key):
                cp2.set(SECTION_GAME, key, val)
        cp2.set(SECTION_GAME, "ActiveMods", ",".join(str(m) for m in inst.mods))
        with open(self.game_ini(inst), "w", encoding="utf-8") as fh:
            cp2.write(fh, space_around_delimiters=False)

    # ---------------------------------------------------------- Einstellungen
    def _gruppierung(self, key: str) -> str:
        return GROUPS.get(key, "weitere")

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
                    if filekey == "game" and key.lower() == "activemods":
                        value = ",".join(str(m) for m in inst.mods)
                    alias = ALIASES.get(key)
                    if alias:
                        value = str(getattr(inst, alias, value))
                    label, hint = LABELS.get(key, (key, ""))
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
            alias = ALIASES.get(key)
            if alias:
                cur = getattr(inst, alias, "")
                try:
                    setattr(inst, alias, int(val) if isinstance(cur, int) else val)
                except (TypeError, ValueError):
                    pass
            if key.lower() == "activemods":
                inst.mods = [int(p) for p in val.replace(" ", "").split(",") if p.isdigit()]
            if key == "ServerAdminPassword":
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
    def mods_search(self, inst, query: str) -> dict:
        """ASE-Mods sind Workshop-IDs - Suche nur auf der Webseite."""
        import urllib.parse
        return {
            "provider": "steam",
            "results": [],
            "has_key": True,
            "note": ("ARK: Survival Evolved laedt Mods ueber Steam-Workshop-IDs. ID im Workshop "
                     "heraussuchen und in das Feld „Mods\" eintragen - der Server laedt sie beim "
                     "Start (-automanagedmods)."),
            "search_url": ("https://steamcommunity.com/workshop/browse/?appid=346110&searchtext=%s"
                           % urllib.parse.quote(query)),
        }
