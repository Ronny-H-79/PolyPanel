"""Instanz-Konfiguration und Pfade."""
from __future__ import annotations

import configparser
import json
import os
from dataclasses import dataclass, asdict, field

from . import games

SERVER_APP_ID = "2430930"
EXE_REL = os.path.join("ShooterGame", "Binaries", "Win64", "ArkAscendedServer.exe")
CONFIG_REL = os.path.join("ShooterGame", "Saved", "Config", "WindowsServer")
LOG_REL = os.path.join("ShooterGame", "Saved", "Logs", "ShooterGame.log")


@dataclass
class Instance:
    name: str
    directory: str
    game: str = games.DEFAULT_GAME       # Spielprofil: ark | satisfactory | 7d2d
    map: str = "Ragnarok_WP"
    session_name: str = "ARK Test"
    port: int = 7790
    query_port: int = 27016
    rcon_port: int = 27025
    rcon_password: str = ""
    mods: list[int] = field(default_factory=list)
    wine_bin: str = "wine"
    wine_prefix: str = ""
    extra_args: str = ""
    max_players: int = 20
    admin_password: str = ""
    restart_times: list[str] = field(default_factory=list)
    # Zeitplan-Aufgaben: {"id","action","time":"HH:MM","days":[1..7] (leer = taeglich),"arg","on"}
    tasks: list[dict] = field(default_factory=list)
    backup_times: list[str] = field(default_factory=list)
    warn_minutes: int = 5
    backups_keep: int = 10
    snapshot_keep: int = 3               # Auto-Snapshots behalten, aeltere werden entfernt
    snapshot_times: list[str] = field(default_factory=list)   # Uhrzeiten fuer Auto-Snapshots
    exclusive_join: bool = False
    banned: list[str] = field(default_factory=list)
    hang_seconds: int = 300
    max_restarts_per_hour: int = 4
    webhook_url: str = ""
    headless: bool = True
    cluster_id: str = ""                 # leer = Name der Instanz
    cluster_dir: str = ""                # leer = <instanz>/clusters (gemeinsam nutzbar)
    cluster_transfer_filtering: bool = True   # True = -NoTransferFromFiltering setzen
    beacon_port: int = 15000             # Satisfactory: dritter Port
    api_token: str = ""                  # Satisfactory: Bearer-Token der HTTPS-API
    telnet_password: str = ""            # 7 Days to Die: TelnetPassword

    # ------------------------------------------------------------------ Profil
    @property
    def profile(self) -> games.GameProfile:
        return games.get(self.game)

    # ------------------------------------------------------------------ Pfade
    @property
    def exe(self) -> str:
        return self.profile.exe(self)

    @property
    def ark_exe(self) -> str:
        return os.path.join(self.directory, EXE_REL)

    @property
    def config_dir(self) -> str:
        return os.path.join(self.directory, CONFIG_REL)

    @property
    def gus_ini(self) -> str:
        return os.path.join(self.config_dir, "GameUserSettings.ini")

    @property
    def game_ini(self) -> str:
        return os.path.join(self.config_dir, "Game.ini")

    @property
    def log_path(self) -> str:
        prof = self.profile
        if hasattr(prof, "log_path"):
            return prof.log_path(self)
        return os.path.join(self.directory, LOG_REL)

    @property
    def pid_file(self) -> str:
        return os.path.join(self.directory, ".noah2games.pid")

    @property
    def console_log(self) -> str:
        return os.path.join(self.directory, ".noah2games-console.log")

    @property
    def mods_dir(self) -> str:
        return os.path.join(self.directory, "ShooterGame", "Binaries", "Win64", "ShooterGame", "Mods")

    # ------------------------------------------------------------------ Ini
    def write_ini(self) -> None:
        """Spielspezifische Konfiguration schreiben (idempotent)."""
        self.profile.write_config(self)

    def control(self, timeout: float = 10.0):
        """Steuerkanal des Spiels (RCON, Telnet oder HTTPS-API)."""
        return self.profile.control(self, timeout=timeout)

    def ark_write_ini(self) -> None:
        """Schreibt Ports/RCON/Mods in die GameUserSettings.ini (idempotent)."""
        os.makedirs(self.config_dir, exist_ok=True)
        cp = configparser.ConfigParser(strict=False)
        cp.optionxform = str
        metadata = ""
        if os.path.exists(self.gus_ini):
            with open(self.gus_ini, encoding="utf-8-sig") as fh:
                first = fh.readline().rstrip("\r\n")
            if first.startswith(";METADATA"):
                metadata = first
            cp.read(self.gus_ini, encoding="utf-8-sig")

        for section in ("ServerSettings", "SessionSettings", "MessageOfTheDay"):
            if not cp.has_section(section):
                cp.add_section(section)

        values = {
            "ServerSettings": {
                "RCONEnabled": "True",
                "RCONPort": str(self.rcon_port),
                "ServerAdminPassword": self.admin_password or self.rcon_password,
                "ServerPassword": "",
                "MaxPlayers": str(self.max_players),
                "ServerPVE": "True",
                "DifficultyOffset": "1.0",
                "ServerCrosshair": "True",
                "ShowMapPlayerLocation": "True",
            },
            "SessionSettings": {
                "SessionName": self.session_name,
                "Port": str(self.port),
                "QueryPort": str(self.query_port),
            },
        }
        for section, kv in values.items():
            for key, val in kv.items():
                cp.set(section, key, val)
        with open(self.gus_ini, "w", encoding="utf-8") as fh:
            if metadata:
                fh.write(metadata + "\n")
            cp.write(fh, space_around_delimiters=False)

        # Mods in Game.ini -> ActiveMods
        cp2 = configparser.ConfigParser(strict=False)
        cp2.optionxform = str
        if os.path.exists(self.game_ini):
            cp2.read(self.game_ini, encoding="utf-8-sig")
        if not cp2.has_section("/script/shootergame.shootergamemode"):
            cp2.add_section("/script/shootergame.shootergamemode")
        cp2.set(
            "/script/shootergame.shootergamemode",
            "ActiveMods",
            ",".join(str(m) for m in self.mods),
        )
        with open(self.game_ini, "w", encoding="utf-8") as fh:
            cp2.write(fh, space_around_delimiters=False)

    # ------------------------------------------------------------------ JSON
    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "Instance":
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    @property
    def cluster_name(self) -> str:
        return (self.cluster_id or self.name).strip()

    @property
    def cluster_path(self) -> str:
        raw = (self.cluster_dir or "").strip()
        if not raw:
            return os.path.join(self.directory, "clusters")
        return os.path.expanduser(raw)

    # ------------------------------------------------------------------ Start
    def launch_argv(self) -> list[str]:
        """Startzeile des jeweiligen Spiels."""
        return self.profile.launch_argv(self)

    def ark_launch_argv(self) -> list[str]:
        # Map-URL wie bei AMP: ASA liest Port, RCON und Admin-Passwort aus der URL.
        # ServerAdminPassword MUSS die letzte ?-Option sein, sonst schluckt sie den Rest.
        url = "%s?listen?Port=%d?QueryPort=%d?RCONEnabled=True?RCONServerGameLogBuffer=600?RCONPort=%d" % (
            self.map, self.port, self.query_port, self.rcon_port)
        if self.rcon_password:
            url += "?ServerAdminPassword=" + self.rcon_password
        argv = [
            self.exe,
            url,
            "-server",
            "-log",
            "-NoBattlEye",
            "-servergamelog",
            "-servergamelogincludetribelogs",
            "-ServerPlatform=All",
            "-MaxPlayers=%d" % self.max_players,
            "-ClusterDirOverride=" + self.cluster_path,
            "-clusterid=" + self.cluster_name,
        ]
        if self.cluster_transfer_filtering:
            argv.append("-NoTransferFromFiltering")
        if self.exclusive_join:
            argv.append("-exclusivejoin")
        if self.mods:
            argv.append("-mods=%s" % ",".join(str(m) for m in self.mods))
        if self.extra_args:
            argv.extend(self.extra_args.split())
        return argv
