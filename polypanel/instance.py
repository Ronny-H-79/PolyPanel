"""Instanz-Konfiguration und Pfade."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field

from . import games

SERVER_APP_ID = "2430930"
EXE_REL = os.path.join("ShooterGame", "Binaries", "Win64", "ArkAscendedServer.exe")
LOADER_REL = os.path.join("ShooterGame", "Binaries", "Win64", "ArkApi", "AsaApiLoader.exe")
CONFIG_REL = os.path.join("ShooterGame", "Saved", "Config", "WindowsServer")
LOG_REL = os.path.join("ShooterGame", "Saved", "Logs", "ShooterGame.log")


def _read_lines(path: str) -> tuple[list[str], bool]:
    """Datei als Zeilen lesen; zweiter Wert: nutzt sie CRLF?"""
    with open(path, "rb") as fh:
        raw = fh.read()
    text = raw.decode("utf-8-sig", "replace")
    crlf = "\r\n" in text
    if crlf:
        text = text.replace("\r\n", "\n")
    return text.split("\n"), crlf


def _write_lines(path: str, lines: list[str], crlf: bool) -> None:
    text = "\n".join(lines)
    if crlf:
        text = text.replace("\n", "\r\n")
    with open(path, "wb") as fh:
        fh.write(text.encode("utf-8"))


def _find_section(lines: list[str], section: str) -> tuple[int, int]:
    """Start- und Endindex einer Sektion (Ende = naechste Sektionszeile oder Dateiende)."""
    want = section.strip().lower()
    start = -1
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not (stripped.startswith("[") and stripped.endswith("]")):
            continue
        name = stripped[1:-1].strip().lower()
        if start < 0 and name == want:
            start = idx
        elif start >= 0:
            return start, idx
    return start, len(lines)


def _update_key(path: str, section: str, key: str, value: str, overwrite: bool = True) -> None:
    """Eine einzelne INI-Zeile setzen, ohne den Rest der Datei anzufassen.

    Bewusst kein configparser: der wirft doppelte Schluessel weg (ARK braucht sie:
    hunderte EngramEntryAutoUnlocks) und normalisiert Schreibweisen. Hier bleibt
    jede andere Zeile Byte fuer Byte erhalten, inklusive Kommentare und CRLF.
    """
    if os.path.exists(path):
        lines, crlf = _read_lines(path)
    else:
        lines, crlf = [], True
        os.makedirs(os.path.dirname(path), exist_ok=True)

    start, end = _find_section(lines, section)
    if start < 0:
        if lines and lines[-1].strip():
            lines.append("")
        lines.append("[%s]" % section)
        lines.append("%s=%s" % (key, value))
    else:
        want = key.strip().lower()
        idx_key = -1
        for idx in range(start + 1, end):
            stripped = lines[idx].strip()
            if stripped.lower().startswith(want + "=") or stripped.lower().startswith(want + " ="):
                idx_key = idx
                break
        if idx_key >= 0:
            if overwrite:
                lines[idx_key] = "%s=%s" % (key, value)
        else:
            lines.insert(end, "%s=%s" % (key, value))
    _write_lines(path, lines, crlf)


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
    # Mods, die immer oben in der Liste stehen sollen (z. B. Stacking-Mods).
    # Die Reihenfolge in `mods` ist die Ladeliste in -mods= und in der Game.ini.
    mods_pinned: list[int] = field(default_factory=list)
    wine_bin: str = "wine"
    wine_prefix: str = ""
    extra_args: str = ""
    max_players: int = 20
    admin_password: str = ""
    # Passwort, das Spieler beim Beitreten eingeben (Spiele mit Join-Passwort)
    server_password: str = ""
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
    asaapi: bool = False                 # ARK: Start ueber ArkApi/AsaApiLoader.exe (Plugins im Spiel)
    # Gesetzt, wenn der Loader nach einem ARK-Update nicht passt: Start dann ohne Plugins.
    asaapi_fallback: bool = False
    cluster_id: str = ""                 # leer = Name der Instanz
    cluster_dir: str = ""                # leer = <instanz>/clusters (gemeinsam nutzbar)
    cluster_transfer_filtering: bool = True   # True = -NoTransferFromFiltering setzen
    beacon_port: int = 15000             # Satisfactory: dritter Port
    api_token: str = ""                  # Satisfactory: Bearer-Token der HTTPS-API
    telnet_password: str = ""            # 7 Days to Die: TelnetPassword
    # 7 Days to Die V2.0: Spielregeln (Blutmond, Loot, XP ...) stecken im SandboxCode.
    # Das Panel merkt sich die Wunschwerte hier und setzt sie per setgamepref.
    live_prefs: dict = field(default_factory=dict)
    # SFTP-Zugang: eigener Benutzer je Instanz, Chroot auf den Instanzordner
    sftp_enabled: bool = False
    sftp_user: str = ""
    sftp_password: str = ""
    sftp_port: int = 0                   # 0 = Basis-Port + laufende Nummer

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
    def loader_exe(self) -> str:
        """ARK: AsaApi-Lader (Plugins im Spiel); andere Spiele haben keinen."""
        if self.game != "ark":
            return ""
        return os.path.join(self.directory, LOADER_REL)

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
        return os.path.join(self.directory, ".PolyPanel.pid")

    @property
    def console_log(self) -> str:
        return os.path.join(self.directory, ".PolyPanel-console.log")

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
        """Schreibt Ports/RCON/Mods in die INIs - zeilenweise, ohne configparser.

        Frueher wurde die ganze Datei ueber `configparser` neu geschrieben. Der haelt
        pro Sektion nur einen Wert je Schluessel und wirft alles Weitere weg - ARK
        braucht aber hunderte Wiederholungen in derselben Sektion
        (`EngramEntryAutoUnlocks`, `ConfigOverrideItemMaxQuantity`, ...). Aus 1182
        Zeilen wurden so 128, aus 121 KB 18 KB. Deshalb: nur einzelne Zeilen setzen.
        """
        os.makedirs(self.config_dir, exist_ok=True)
        # Diese Werte gehoeren dem Panel: Startzeile, RCON, Passwoerter, Ports.
        # Sie werden bei jedem Start durchgesetzt.
        erzwingen = {
            "ServerSettings": {
                "RCONEnabled": "True",
                "RCONPort": str(self.rcon_port),
                "ServerAdminPassword": self.admin_pw,
                "ServerPassword": self.server_password,
                "MaxPlayers": str(self.max_players),
            },
            "SessionSettings": {
                "SessionName": self.session_name,
                "Port": str(self.port),
                "QueryPort": str(self.query_port),
            },
        }
        # Sinnvolle Startwerte: nur setzen, wenn der Schluessel fehlt. Ein
        # Admin-Wert in der INI bleibt damit stehen.
        ergaenzen = {
            "ServerSettings": {
                "ServerPVE": "True",
                "DifficultyOffset": "1.0",
                # Max-Level der wilden Dinos: OverrideOfficialDifficulty x 30 = 300
                "OverrideOfficialDifficulty": "10.0",
                "ServerCrosshair": "True",
                "ShowMapPlayerLocation": "True",
            },
        }
        for section, kv in erzwingen.items():
            for key, val in kv.items():
                _update_key(self.gus_ini, section, key, val)
        for section, kv in ergaenzen.items():
            for key, val in kv.items():
                _update_key(self.gus_ini, section, key, val, overwrite=False)

        # Mods in Game.ini -> ActiveMods (nur diese eine Zeile ersetzen)
        _update_key(self.game_ini, "/Script/ShooterGame.ShooterGameMode",
                    "ActiveMods", ",".join(str(m) for m in self.mods))

    # ------------------------------------------------------------------ JSON
    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(asdict(self), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> Instance:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        known = {f for f in cls.__dataclass_fields__}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})

    @property
    def admin_pw(self) -> str:
        """Admin-Passwort der Instanz (bei ARK zugleich das RCON-Passwort).

        ARK liest `?ServerAdminPassword=` aus der Startzeile und schreibt den Wert beim Start in die
        Konfigdatei zurueck. Startzeile und Datei muessen deshalb denselben Wert haben, sonst ist ein
        in der Datei gepflegtes Admin-Passwort nach jedem Neustart/Update weg.
        """
        return self.admin_password or self.rcon_password

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
        if self.admin_pw:
            url += "?ServerAdminPassword=" + self.admin_pw
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
