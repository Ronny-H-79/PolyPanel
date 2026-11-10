"""7 Days to Die (Linux, nativ).

Steam-App-ID 294420, Start ueber `startserver.sh`, Konfiguration in
`serverconfig.xml`, Steuerung ueber Telnet (Standardport 8081).
"""
from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET

from .base import GameProfile
from .sv7dtd_labels import LABELS

LOG_REL = os.path.join("logs", "output_log.txt")


class SevenDaysProfile(GameProfile):
    key = "7d2d"
    label = "7 Days to Die"
    server_app_id = "294420"
    control_kind = "telnet"
    needs_wine = False
    default_game_port = 26900
    default_query_port = 26901
    default_control_port = 8081
    supports_mods = True          # Mods als Ordner unter Mods/
    install_note = "nativ; Telnet muss in der serverconfig.xml aktiv sein"
    settings_fields = (
        ("session_name", "Spieleserver-Name", "erscheint in der Serverliste", "text"),
        ("max_players", "Max. Spieler", "gleichzeitige Spieler", "int"),
        ("port", "Spiel-Port", "UDP, Spielverbindung", "int"),
        ("rcon_port", "Telnet-Port", "Steuerkanal (serverconfig.xml)", "int"),
        ("telnet_password", "Telnet-Passwort", "Passwort fuer den Steuerkanal", "password"),
        ("rcon_password", "Server-Passwort", "leer = oeffentlicher Server", "password"),
    )

    # ---------------------------------------------------------------- Pfade
    def exe(self, inst) -> str:
        return os.path.join(inst.directory, "startserver.sh")

    def config_file(self, inst) -> str:
        return os.path.join(inst.directory, "serverconfig.xml")

    def log_path(self, inst) -> str:
        # 7D2D legt selbst eine Datei an: output_log__JJJJ-MM-TT__HH-MM-SS.txt.
        # Der -logfile-Parameter wird ignoriert, deshalb hier suchen.
        import glob
        kandidaten = []
        kandidaten += glob.glob(os.path.join(inst.directory, "output_log__*.txt"))
        kandidaten += glob.glob(os.path.join(inst.directory, "logs", "output_log*.txt"))
        fest = os.path.join(inst.directory, LOG_REL)
        if os.path.exists(fest):
            kandidaten.append(fest)
        if kandidaten:
            return max(kandidaten, key=os.path.getmtime)
        return inst.console_log

    # ------------------------------------------------------------ Startzeile
    def launch_argv(self, inst) -> list[str]:
        os.makedirs(os.path.join(inst.directory, "logs"), exist_ok=True)   # 7D2D legt sie nicht an
        argv = ["/bin/sh", "startserver.sh",
                "-configfile=serverconfig.xml"]
        if inst.extra_args:
            argv.extend(inst.extra_args.split())
        return argv

    # ---------------------------------------------------------- Konfigdatei
    def write_config(self, inst) -> None:
        """Die Eigenschaften in serverconfig.xml ersetzen (Datei bleibt sonst unangetastet)."""
        path = self.config_file(inst)
        values = {
            "ServerName": inst.session_name,
            "ServerPort": str(inst.port),
            "ServerPassword": inst.rcon_password or "",
            "MaxPlayers": str(inst.max_players),
            "TelnetEnabled": "true",
            "TelnetPort": str(inst.rcon_port),
            "TelnetPassword": inst.telnet_password or "",
        }
        if not os.path.exists(path):
            # Erststart: SteamCMD legt die Datei an; ohne sie nichts schreiben
            return
        with open(path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        for key, val in values.items():
            pattern = re.compile(r'(<property\s+name="%s"\s+value=")[^"]*(")' % re.escape(key))
            if pattern.search(text):
                text = pattern.sub(lambda m: m.group(1) + val.replace("&", "&amp;") + m.group(2), text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    # ---------------------------------------------------------- Einstellungen
    # Instanz-Attribut <-> XML-Eigenschaft: diese Werte fuehrt der Manager selbst
    ALIASES = {
        "ServerName": "session_name",
        "ServerPort": "port",
        "MaxPlayers": "max_players",
        "ServerPassword": "rcon_password",
        "TelnetPort": "rcon_port",
        "TelnetPassword": "telnet_password",
    }

    GRUPPEN = {
        "server": ("ServerName", "ServerDescription", "ServerWebsiteURL", "ServerPassword",
                   "ServerLoginConfirmationText", "Region", "Language", "EACEnabled",
                   "HideCommandExecutionLog", "MaxPlayers", "ServerVisibility",
                   "ServerMaxAllowedViewDistance", "ServerMaxWorldTransferSpeedKiBs",
                   "IgnoreEOSSanctions", "ClientAllowMods", "SandboxCode", "AdminFileName",
                   "MaxUncoveredMapChunksPerPlayer", "PersistentPlayerProfiles",
                   "ServerAllowCrossplay", "ServerAllowClientMods"),
        "netz": ("ServerPort", "ServerQueryPort", "TelnetEnabled", "TelnetPort", "TelnetPassword",
                 "WebDashboardEnabled", "WebDashboardPort", "WebDashboardUrl", "RCONEnabled",
                 "RCONPort", "RCONPassword"),
        "welt": ("GameWorld", "WorldGenSeed", "WorldGenSize", "GameName", "GameMode",
                 "GameDifficulty", "BlockDurabilityModifier", "LootAbundance", "LootRespawnDays",
                 "AirDropFrequency", "AirDropMarker", "PartySharedKillRange", "PlayerKillingMode",
                 "MaxSpawnedZombies", "MaxSpawnedAnimals", "BloodMoonFrequency",
                 "BloodMoonRange", "BloodMoonWarning", "EnemySpawnMode", "IsBloodMoon",
                 "AllowSpawnNearBackpack", "BedrollExpiryTime", "BedRollDeadZoneSize",
                 "MaxChunkAge", "SaveDataLimit", "QuestProgressionDailyLimit"),
        "spieler": ("DropOnDeath", "DropOnQuit", "DeathPenalty", "PlayerSafeZoneLevel",
                    "PlayerSafeZoneHours", "XPMultiplier", "CraftingSkillpointCostMultiplier"),
    }

    def _gruppierung(self, name: str) -> str:
        for gruppe, keys in self.GRUPPEN.items():
            if name in keys:
                return gruppe
        return "weitere"

    def _read_props(self, inst) -> list[tuple[str, str, str]]:
        """Alle Eigenschaften aus serverconfig.xml inkl. Kommentar als Hinweis."""
        path = self.config_file(inst)
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return []
        tokens = []
        for match in re.finditer(r"(<!--(?P<comment>.*?)-->)|(<property\s+name=\"(?P<name>[^\"]+)\"\s+value=\"(?P<value>[^\"]*)\"\s*/>)",
                                 text, re.S):
            if match.group("comment") is not None:
                tokens.append(("c", " ".join(match.group("comment").split())))
            else:
                tokens.append(("p", (match.group("name"), match.group("value"))))
        # In der 7D2D-Vorlage steht der erklaerende Kommentar HINTER der Eigenschaft.
        props: list[tuple[str, str, str]] = []
        for idx, (kind, payload) in enumerate(tokens):
            if kind != "p":
                continue
            name, value = payload
            hint = ""
            for kind2, payload2 in tokens[idx + 1:]:
                if kind2 == "p":
                    break
                if payload2 and not payload2.startswith("****"):
                    hint = payload2[:400]
                    break
            props.append((name, value, hint))
        return props

    def settings(self, inst) -> list[dict]:
        props = self._read_props(inst)
        if not props:
            return super().settings(inst)          # vor der Installation: Kerneinstellungen
        out = []
        for name, value, hint in props:
            alias = self.ALIASES.get(name)
            if alias:
                value = str(getattr(inst, alias, value))
            typ = "text"
            if re.fullmatch(r"-?\d+", str(value)):
                typ = "int"
            elif str(value).lower() in ("true", "false"):
                typ = "bool"
            if "password" in name.lower() or "token" in name.lower():
                typ = "password"
            label, hint_de = LABELS.get(name, (name, hint))
            out.append({"file": "instance", "section": "", "key": name,
                        "label": label, "hint": hint_de, "type": typ,
                        "value": str(value), "group": self._gruppierung(name)})
        return out

    def apply_settings(self, inst, items) -> int:
        path = self.config_file(inst)
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return super().apply_settings(inst, items)
        changed = 0
        for item in items:
            name, val = item.get("key"), str(item.get("value", ""))
            if not name:
                continue
            pattern = re.compile(r'(<property\s+name="%s"\s+value=")[^"]*(")' % re.escape(name))
            if not pattern.search(text):
                continue
            text = pattern.sub(lambda m: m.group(1) + val.replace("&", "&amp;").replace('"', "&quot;") + m.group(2), text)
            alias = self.ALIASES.get(name)
            if alias:
                cur = getattr(inst, alias, "")
                setattr(inst, alias, int(val) if isinstance(cur, int) and val.isdigit() else val)
            changed += 1
        if changed:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return changed

    # ---------------------------------------------------------- Steuerkanal
    def control(self, inst, timeout: float = 10.0):
        from ..control import TelnetClient
        return TelnetClient("127.0.0.1", inst.rcon_port, inst.telnet_password, timeout=timeout)

    def ready(self, inst) -> bool:
        """7D2D ist bereit, wenn der Telnet-Port Verbindungen annimmt."""
        from .base import _tcp_open
        return _tcp_open("127.0.0.1", inst.rcon_port, timeout=2)

    def graceful_stop(self, inst) -> list[str]:
        """7D2D kennt kein RCON-Quit: Welt speichern, beenden per Signal."""
        with self.control(inst, timeout=10) as tn:
            tn.command("save", timeout=15)
        return ["save ueber Telnet gesendet"]
