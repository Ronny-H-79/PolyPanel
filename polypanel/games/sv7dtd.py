"""7 Days to Die (Linux, nativ).

Steam-App-ID 294420, Start ueber `startserver.sh`, Konfiguration in
`serverconfig.xml`, Steuerung ueber Telnet (Standardport 8081).
"""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
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

    # ------------------------------------------------------------ NexusMods
    NEXUS_KEY = os.path.expanduser("~/.config/polypanel/nexus.key")

    @classmethod
    def nexus_key(cls) -> str:
        try:
            with open(cls.NEXUS_KEY, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return ""

    @classmethod
    def set_nexus_key(cls, key: str) -> None:
        os.makedirs(os.path.dirname(cls.NEXUS_KEY), exist_ok=True)
        with open(cls.NEXUS_KEY, "w", encoding="utf-8") as fh:
            fh.write(key.strip() + "\n")
        os.chmod(cls.NEXUS_KEY, 0o600)

    def _nexus(self, pfad: str, timeout: float = 20.0):
        req = urllib.request.Request("https://api.nexusmods.com/v1" + pfad, headers={
            "apikey": self.nexus_key(), "User-Agent": "PolyPanel",
            "accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", "replace"))

    NEXUS_API = "https://api.nexusmods.com/v3/mods/search"

    def _nexus_top(self, limit: int = 50):
        """Top-Mods des Spiels nach Downloads (die API kennt keinen Suchbegriff)."""
        key = self.nexus_key()
        if not key:
            return []
        body = {"filters": {"games": ["7daystodie"]},
                "sort": {"field": "downloads", "direction": "desc"},
                "pagination": {"type": "page", "page": 1, "page_size": min(limit, 100)}}
        req = urllib.request.Request(self.NEXUS_API, data=json.dumps(body).encode(),
                                     headers={"apikey": key, "User-Agent": "PolyPanel",
                                              "Content-Type": "application/json",
                                              "accept": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=25) as resp:
            daten = json.loads(resp.read().decode("utf-8", "replace"))
        return ((daten.get("data") or {}).get("mods")) or []

    def mods_search(self, inst, query: str) -> dict:
        treffer, fehler = [], ""
        if self.nexus_key():
            try:
                for m in self._nexus_top():
                    name = m.get("name") or ""
                    if query.lower() in name.lower() or query.lower() in (m.get("summary") or "").lower():
                        treffer.append({
                            "id": m.get("game_scoped_id") or m.get("id"),
                            "name": name,
                            "description": (m.get("summary") or "")[:160],
                            "downloads": m.get("downloads") or 0,
                            "url": "https://www.nexusmods.com/7daystodie/mods/%s"
                                   % (m.get("game_scoped_id") or ""),
                            "source": "nexus",
                        })
            except Exception as exc:            # noqa: BLE001 - Suche darf nicht scheitern
                fehler = "Nexus: %s" % exc.__class__.__name__
        if not treffer:
            # Rueckfall: 7D2D-Mods liegen oft auf GitHub (offene API, ohne Key)
            try:
                url = ("https://api.github.com/search/repositories?q=%s&sort=stars&order=desc&per_page=15"
                       % urllib.parse.quote("%s 7d2d in:name,description" % query))
                req = urllib.request.Request(url, headers={"User-Agent": "PolyPanel",
                                                           "accept": "application/vnd.github+json"})
                with urllib.request.urlopen(req, timeout=20) as resp:
                    daten = json.loads(resp.read().decode("utf-8", "replace"))
                for m in (daten.get("items") or []):
                    treffer.append({"id": m.get("full_name"), "name": m.get("name") or "",
                                    "description": (m.get("description") or "")[:160],
                                    "downloads": m.get("stargazers_count") or 0,
                                    "url": m.get("html_url") or "",
                                    "source": "github", "installable": True})
            except Exception:                   # noqa: BLE001
                pass
        return {"provider": "nexus+github" if self.nexus_key() else "github",
                "results": treffer, "has_key": bool(self.nexus_key()), "error": fehler,
                "note": ("Top-Mods (Nexus, nach Downloads) plus GitHub-Treffer - lokal nach "
                         "Eingabe gefiltert. Mod-Ordner nach Mods/ legen."),
                "search_url": "https://www.nexusmods.com/7daystodie/search/?gsearch=%s"
                              % urllib.parse.quote(query)}


    def mods_install(self, inst, mod_id: str, log=print) -> str:
        """7D2D-Mod aus einem GitHub-Repo holen (ZIP) und nach Mods/ entpacken."""
        if "/" not in mod_id:
            raise ControlError("Für Nexus-Mods gibt es keinen API-Download (Premium nötig) - "
                               "bitte über die Webseite laden")
        import io as _io
        import zipfile as _zip
        kopf = {"User-Agent": "PolyPanel", "accept": "application/vnd.github+json"}

        def _get(url: str) -> bytes:
            with urllib.request.urlopen(urllib.request.Request(url, headers=kopf), timeout=60) as r:
                return r.read()

        info = json.loads(_get("https://api.github.com/repos/" + mod_id).decode("utf-8", "replace"))
        branch = info.get("default_branch") or "main"
        log("lade %s (%s)" % (mod_id, branch))
        rohdaten = _get("https://github.com/%s/archive/refs/heads/%s.zip" % (mod_id, branch))
        log("%.1f MB geladen" % (len(rohdaten) / 1024 / 1024))

        ziel = self.mods_path(inst)
        os.makedirs(ziel, exist_ok=True)
        with _zip.ZipFile(_io.BytesIO(rohdaten)) as z:
            namen = [n for n in z.namelist() if n.strip()]
            oben = {n.split("/")[0] for n in namen}
            wurzel = oben.pop() if len(oben) == 1 else ""

            # Ordner mit ModInfo.xml sind die eigentlichen Mods (7D2D erwartet Mods/<Name>/ModInfo.xml)
            mods = sorted({n.rsplit("/", 1)[0] for n in namen if n.endswith("ModInfo.xml")})
            if not mods:
                z.extractall(os.path.join(ziel, os.path.basename(mod_id)))
                return "%s nach %s/%s entpackt (keine ModInfo.xml gefunden)" % (
                    mod_id, ziel, os.path.basename(mod_id))

            eingetragen = []
            for modordner in mods:
                teile = modordner.split("/")
                if wurzel and teile and teile[0] == wurzel:
                    teile = teile[1:]
                if len(teile) > 2:              # zu tief verschachtelt
                    continue
                name = teile[-1]
                praefix = modordner + "/"
                for eintrag in z.infolist():
                    if not eintrag.filename.startswith(praefix):
                        continue
                    relativ = eintrag.filename[len(praefix):]
                    if not relativ:
                        continue
                    pfad = os.path.join(ziel, name, relativ)
                    if eintrag.is_dir():
                        os.makedirs(pfad, exist_ok=True)
                    else:
                        os.makedirs(os.path.dirname(pfad), exist_ok=True)
                        with open(pfad, "wb") as fh:
                            fh.write(z.read(eintrag))
                eingetragen.append(name)
            if not eingetragen:
                z.extractall(os.path.join(ziel, os.path.basename(mod_id)))
                return "%s nach %s/%s entpackt" % (mod_id, ziel, os.path.basename(mod_id))
        return "%s: %s nach %s entpackt" % (mod_id, ", ".join(eingetragen), ziel)

    def mods_path(self, inst) -> str:
        return os.path.join(inst.directory, "Mods")

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

    # Eigenschaften mit festen Werten bekommen eine Auswahlliste statt eines Textfelds.
    # 7D2D kennt fuer Region genau diese Bezeichner (serverconfig.xml, <property name="Region">).
    CHOICES = {
        "Region": ["None", "NorthAmericaEast", "NorthAmericaWest", "NorthAmericaCentral",
                   "SouthAmerica", "Europe", "MiddleEast", "Asia", "Africa", "Oceania"],
    }

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
            eintrag = {"file": "instance", "section": "", "key": name,
                       "label": label, "hint": hint_de, "type": typ,
                       "value": str(value), "group": self._gruppierung(name)}
            if name in self.CHOICES:
                eintrag["type"] = "select"
                eintrag["choices"] = list(self.CHOICES[name])
                if str(value) not in eintrag["choices"] and str(value):
                    # unbekannter Wert aus einer aelteren Config bleibt waehlbar
                    eintrag["choices"].insert(0, str(value))
            out.append(eintrag)
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
