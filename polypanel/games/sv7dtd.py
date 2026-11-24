"""7 Days to Die (Linux, nativ).

Steam-App-ID 294420, Start ueber `startserver.sh`, Konfiguration in
`serverconfig.xml`, Steuerung ueber Telnet (Standardport 8081).
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.parse
import urllib.request

from .base import GameProfile
from .sv7dtd_labels import LABELS

LOG_REL = os.path.join("logs", "output_log.txt")


def _udp_port_bound(port: int) -> bool:
    """Steht ein UDP-Port an (Spielport des 7D2D-Servers)?"""
    want = "%04X" % port
    for path in ("/proc/net/udp", "/proc/net/udp6"):
        try:
            with open(path, encoding="utf-8") as fh:
                for line in fh.readlines()[1:]:
                    teile = line.split()
                    if len(teile) > 1 and teile[1].split(":")[-1] == want:
                        return True
        except OSError:
            continue
    return False


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

    # Steuerbefehle fuer Spieleraktionen - 7D2D arbeitet mit Namen bzw. Entity-ID, nicht mit RCON-Namen
    player_commands = {
        "kick": "kick %s",
        "ban": "ban add %s",
        "unban": "ban remove %s",
    }
    # true: die Aktion nimmt den Spielernamen, nicht die Steam-ID
    player_action_by_name = True
    # Telnet kennt kein `ListPlayers` - die Spielerliste holt `lp` (Alias: listplayers)
    players_command = "lp"
    # `give <Spieler> <Itemname> <Anzahl>` - 7D2D kennt weder Blueprints noch Whitelist-Befehle
    give_command = "give %s %s %s"
    supports_whitelist = False
    settings_fields = (
        ("session_name", "Spieleserver-Name", "erscheint in der Serverliste", "text"),
        ("max_players", "Max. Spieler", "gleichzeitige Spieler", "int"),
        ("port", "Spiel-Port", "UDP, Spielverbindung", "int"),
        ("rcon_port", "Telnet-Port", "Steuerkanal (serverconfig.xml)", "int"),
        ("telnet_password", "Telnet-Passwort", "Passwort fuer den Steuerkanal", "password"),
        ("server_password", "Server-Passwort", "leer = oeffentlicher Server", "password"),
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
            from ..control import ControlError
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
            "ServerPassword": inst.server_password or "",
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
                text = pattern.sub(lambda m, wert=val: m.group(1) + wert.replace("&", "&amp;") + m.group(2), text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    # ---------------------------------------------------------- Einstellungen
    # Instanz-Attribut <-> XML-Eigenschaft: diese Werte fuehrt der Manager selbst
    ALIASES = {
        "ServerName": "session_name",
        "ServerPort": "port",
        "MaxPlayers": "max_players",
        "ServerPassword": "server_password",
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
        # Werte laut Kommentar in der serverconfig.xml des Spiels
        "Region": ["NorthAmericaEast", "NorthAmericaWest", "CentralAmerica", "SouthAmerica",
                   "Europe", "Russia", "Asia", "MiddleEast", "Africa", "Oceania"],
        # Welt: Navezgane (feste Karte) oder RWG (Zufallswelt). Eigene/pregenerierte Weltnamen
        # bleiben waehlbar, weil der aktuelle Wert immer mit in die Liste wandert.
        "GameWorld": ["Navezgane", "RWG"],
        "WorldGenSize": ["6144", "8192", "10240"],
        "GameDifficulty": ["0", "1", "2", "3", "4", "5"],
        "ServerVisibility": ["0", "1", "2"],
        "PlayerKillingMode": ["0", "1", "2", "3"],
        "DropOnDeath": ["0", "1", "2", "3", "4"],
        "DropOnQuit": ["0", "1", "2", "3", "4"],
        "ZombieMove": ["0", "1", "2", "3", "4"],
        "ZombieMoveNight": ["0", "1", "2", "3", "4"],
        "ZombieBMMove": ["0", "1", "2", "3", "4"],
        "ZombieFeralSense": ["0", "1", "2", "3"],
    }

    # --- Live-Spielregeln ---------------------------------------------------
    # Seit V2.0 stehen diese Werte nicht mehr einzeln in der serverconfig.xml -
    # FFP buendelt sie im `SandboxCode`. Zur Laufzeit sind sie aber ueber Telnet
    # (`setgamepref`) aenderbar; das Panel merkt sich die Wunschwerte und setzt
    # sie nach jedem Serverstart erneut.
    LIVE_PREFS = (
        ("BloodMoonFrequency", "Blutmond-Haeufigkeit (Tage)", "0 = kein Blutmond, 7 = jede Woche", "int", None, "blutmond"),
        ("BloodMoonEnemyCount", "Gegner im Blutmond", "Grundwert, skaliert mit der Spielerzahl", "int", None, "blutmond"),
        ("BloodMoonRange", "Blutmond-Fenster (Tage)", "0 = genau am Blutmondtag, sonst +/- N Tage", "int", None, "blutmond"),
        ("BloodMoonWarning", "Blutmond-Warnung ab (Spielstunde)", "Warnung erscheint ab dieser Stunde", "int", None, "blutmond"),
        ("GameDifficulty", "Schwierigkeit", "0 Scavenger, 1 Adventurer, 2 Nomad, 3 Warrior, 4 Survivalist, 5 Insane", "select", ["0", "1", "2", "3", "4", "5"], "regeln"),
        ("XPMultiplier", "XP-Multiplikator (%)", "100 = normal", "int", None, "regeln"),
        ("LootAbundance", "Loot-Menge (%)", "100 = normal", "int", None, "regeln"),
        ("LootRespawnDays", "Loot-Nachschub (Tage)", "Tage bis Loot in Containern nachwaechst", "int", None, "regeln"),
        ("AirDropFrequency", "Luftabwurf alle (Spieltage)", "0 = aus", "int", None, "regeln"),
        ("AirDropMarker", "Luftabwurf auf der Karte", "True = Position wird angezeigt", "select", ["True", "False"], "regeln"),
        ("DayNightLength", "Tag-Nacht-Laenge (Minuten)", "echte Minuten pro Spieltag, Standard 60", "int", None, "regeln"),
        ("DayLightLength", "Tageslicht (Spielstunden)", "Standard 18", "int", None, "regeln"),
        ("DeathPenalty", "Strafe beim Tod", "0 = keine, 1 = XP-Verlust, 2 = Rucksack, 3 = alles", "select", ["0", "1", "2", "3"], "regeln"),
        ("ZombieMove", "Zombie-Tempo (Tag)", "0 gehen, 1 joggen, 2 rennen, 3 sprinten, 4 Albtraum", "select", ["0", "1", "2", "3", "4"], "regeln"),
        ("ZombieMoveNight", "Zombie-Tempo (Nacht)", "0 gehen bis 4 Albtraum", "select", ["0", "1", "2", "3", "4"], "regeln"),
        ("ZombieBMMove", "Zombie-Tempo (Blutmond)", "0 gehen bis 4 Albtraum", "select", ["0", "1", "2", "3", "4"], "regeln"),
        ("ZombieFeralSense", "Wilde Zombies spueren dich", "0 aus, 1 tagsueber, 2 nachts, 3 immer", "select", ["0", "1", "2", "3"], "regeln"),
        ("BlockDamagePlayer", "Block-Schaden Spieler (%)", "100 = normal", "int", None, "regeln"),
        ("BlockDamageAI", "Block-Schaden Zombies (%)", "100 = normal", "int", None, "regeln"),
        ("BlockDamageAIBM", "Block-Schaden Zombies im Blutmond (%)", "100 = normal", "int", None, "regeln"),
        ("QuestProgressionDailyLimit", "Quests pro Tag", "0 = unbegrenzt", "int", None, "regeln"),
    )
    _LIVE_CACHE: dict = {}
    _PREFS_LAEUFT: set = set()

    def _live_werte(self, inst) -> dict:
        """Ist-Werte vom laufenden Server - ein `getgamepref` liefert alle, 15 s Cache."""
        zwischen = SevenDaysProfile._LIVE_CACHE.get(inst.name)
        if zwischen and time.time() - zwischen[0] < 15:
            return zwischen[1]
        if not _udp_port_bound(inst.port):
            return {}
        try:
            with self.control(inst, timeout=6) as tn:
                text = tn.command("getgamepref", timeout=6) or ""
        except Exception:      # noqa: BLE001 - ohne Server gelten die gespeicherten Werte
            return {}
        werte = {m.group(1): m.group(2).strip()
                 for m in re.finditer(r"GamePref\.([A-Za-z0-9_]+) = ([^\r\n]*)", text)}
        SevenDaysProfile._LIVE_CACHE[inst.name] = (time.time(), werte)
        return werte

    def _live_felder(self, inst) -> list[dict]:
        ist = self._live_werte(inst)
        gespeichert = dict(getattr(inst, "live_prefs", None) or {})
        felder = []
        for key, label, hint, typ, choices, gruppe in self.LIVE_PREFS:
            wert = ist.get(key, gespeichert.get(key, ""))
            feld = {"file": "live", "section": "", "key": key, "label": label,
                    "hint": hint, "type": typ, "value": str(wert), "group": gruppe}
            if choices:
                feld["type"] = "select"
                feld["choices"] = list(choices)
                if str(wert) and str(wert) not in feld["choices"]:
                    feld["choices"].insert(0, str(wert))
            felder.append(feld)
        return felder

    def apply_live_prefs(self, inst, werte: dict) -> list[str]:
        """Werte per Telnet setzen (`setgamepref`). Rueckgabe: tatsaechlich gesendete Keys."""
        gesetzt: list[str] = []
        if not werte:
            return gesetzt
        try:
            with self.control(inst, timeout=10) as tn:
                for key, wert in werte.items():
                    if not key or not str(wert).strip():
                        continue
                    tn.command("setgamepref %s %s" % (key, wert), timeout=6)
                    gesetzt.append(key)
        except Exception:       # noqa: BLE001 - kein Server: Werte bleiben gespeichert
            return gesetzt
        SevenDaysProfile._LIVE_CACHE.pop(inst.name, None)
        return gesetzt

    def _prefs_nachziehen(self, inst) -> None:
        """Gemerkte Live-Regeln nach einem Serverstart einmal anwenden."""
        werte = dict(getattr(inst, "live_prefs", None) or {})
        if not werte:
            return
        from .. import runner
        try:
            pid = str(runner.read_pid(inst) or "")
        except Exception:       # noqa: BLE001
            return
        if not pid:
            return
        marker = os.path.join(inst.directory, ".PolyPanel-prefs")
        try:
            with open(marker, encoding="utf-8") as fh:
                if fh.read().strip() == pid:
                    return
        except OSError:
            pass
        if inst.name in SevenDaysProfile._PREFS_LAEUFT:
            return
        SevenDaysProfile._PREFS_LAEUFT.add(inst.name)

        def _lauf() -> None:
            try:
                if self.apply_live_prefs(inst, werte):
                    with open(marker, "w", encoding="utf-8") as fh:
                        fh.write(pid)
            finally:
                SevenDaysProfile._PREFS_LAEUFT.discard(inst.name)
        threading.Thread(target=_lauf, daemon=True).start()

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
        out.extend(self._live_felder(inst))
        return out

    def apply_settings(self, inst, items) -> int:
        # Live-Regeln (setgamepref) haben keine Zeile in der serverconfig.xml.
        live = [i for i in items if isinstance(i, dict) and i.get("file") == "live"]
        items = [i for i in items if not (isinstance(i, dict) and i.get("file") == "live")]
        if live:
            store = dict(getattr(inst, "live_prefs", None) or {})
            neu = {}
            for i in live:
                key = i.get("key")
                if not key:
                    continue
                store[key] = str(i.get("value", "")).strip()
                neu[key] = store[key]
            inst.live_prefs = store
            self.apply_live_prefs(inst, neu)
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
            text = pattern.sub(lambda m, wert=val: m.group(1) + wert.replace("&", "&amp;").replace('"', "&quot;") + m.group(2), text)
            alias = self.ALIASES.get(name)
            if alias:
                cur = getattr(inst, alias, "")
                setattr(inst, alias, int(val) if isinstance(cur, int) and val.isdigit() else val)
            changed += 1
        if changed:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
        return changed + len(live)

    # ---------------------------------------------------------- Steuerkanal
    def control(self, inst, timeout: float = 10.0):
        from ..control import TelnetClient
        return TelnetClient("127.0.0.1", inst.rcon_port, inst.telnet_password, timeout=timeout)

    def ready(self, inst) -> bool:
        """7D2D ist bereit, wenn der Spielport gebunden ist.

        Fruehere Fassung klopfte an den Telnet-Port und schloss die Verbindung sofort wieder -
        der Server protokollierte daraufhin bei jeder Statusabfrage
        `IOException: Unable to write data to the transport connection: The socket has been shut down`.
        Der Spielport in /proc/net/udp verraet dasselbe, ohne dass sich jemand einloggt.
        """
        bereit = _udp_port_bound(inst.port)
        if bereit:
            self._prefs_nachziehen(inst)
        return bereit

    def graceful_stop(self, inst) -> list[str]:
        """7D2D kennt kein RCON-Quit: Welt speichern, beenden per Signal."""
        with self.control(inst, timeout=10) as tn:
            tn.command("save", timeout=15)
        return ["save ueber Telnet gesendet"]
