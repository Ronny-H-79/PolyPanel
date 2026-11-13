"""Space Engineers Dedicated Server (Linux nativ, App 298740).

Kein RCON: Steuerung ueber Prozess (Start/Stop), die XML-Konfiguration und die
Server-Konsole auf stdin. Pfade/Startzeile werden nach der Installation geprueft.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET

from .base import GameProfile

CFG_NAME = "SpaceEngineers-Dedicated.cfg"
TEMPLATE = os.path.join(os.path.dirname(__file__), "spaceengineers_template.cfg")
LOG_REL = os.path.join("Instance", "SpaceEngineersDedicated.log")

# Wichtige Felder mit deutschen Bezeichnungen (Rest kommt aus der XML)
LABELS = {
    "ServerName": ("Servername", "Name in der Serverliste"),
    "ServerPort": ("Spiel-Port", "UDP, Standard 27016"),
    "SteamPort": ("Steam-Port", "UDP, Steam-Netzwerk"),
    "WorldName": ("Weltname", "Save-Ordner der Welt"),
    "LoadWorld": ("Welt laden", "Pfad zur vorhandenen Welt, leer = neue"),
    "IP": ("Bind-Adresse", "0.0.0.0 = alle Schnittstellen"),
    "MaxPlayers": ("Max. Spieler", "gleichzeitige Spieler"),
    "GameMode": ("Spielmodus", "Survival oder Creative"),
    "OnlineMode": ("Online-Modus", "public, friends oder offline"),
    "Password": ("Server-Passwort", "leer = offen"),
    "PauseGameWhenEmpty": ("Pausieren ohne Spieler", "true/false"),
    "AutoSaveInMinutes": ("Autosave (Minuten)", "0 = aus"),
    "Scenario": ("Szenario", "z. B. StarSystem"),
    "Mods": ("Mods", "Workshop-IDs, kommagetrennt"),
    "ExperimentalMode": ("Experimental", "Nur ein Wunsch: SE schaltet selbst auf Experimental, sobald "
                                        "Einstellungen ueber den Vanilla-Werten liegen (MaxPlayers, "
                                        "MaxFloatingObjects, PhysicsIterations, Ingame-Scripts) oder die "
                                        "Hardware zu schwach gemeldet wird (z. B. VM-CPU). Der Client muss "
                                        "Experimental dann in den Spieloptionen aktivieren."),
    "ServerDescription": ("Beschreibung", "Text in der Serverliste"),
    "ServerPasswordHash": ("Passwort-Hash", "intern, nicht aendern"),
}


# Gruppierung fuer die Einstellungsseite (nur diese Gruppen kennt die UI)
_SRV = {"ServerName", "ServerPort", "SteamPort", "IP", "OnlineMode", "Password",
        "ServerPassword", "ServerDescription", "GroupID", "MaxPlayers"}
_WELT = {"WorldName", "LoadWorld", "PremadeCheckpointPath", "WorldSizeKm",
         "VoxelGeneratorVersion", "Scenario", "AsteroidAmount", "ScenarioEditMode",
         "EnableSunRotation", "SunRotationIntervalMinutes", "EnableEncounters", "EnableFlora"}
_SPIELER = {"Administrators", "Banned", "Mods", "CanJoinRunning", "EnableSpectator"}


def _group_of(name: str) -> str:
    if name in _SRV:
        return "server"
    if name in _WELT:
        return "welt"
    if name in _SPIELER:
        return "spieler"
    if name.startswith(("Remote", "Steam", "Master")):
        return "netz"
    return _SE_GRUPPE.get(name, "weitere")


class SpaceEngineersProfile(GameProfile):
    key = "spaceengineers"
    label = "Space Engineers"
    server_app_id = "298740"
    control_kind = "none"
    needs_wine = True    # es gibt nur SpaceEngineersDedicated.exe (.NET, Windows)
    default_game_port = 27016
    default_query_port = 27015
    default_control_port = 0          # kein RCON
    supports_mods = True
    has_control = False  # keine RCON/API-Anbindung
    use_pty = False      # .NET-Server bricht mit PTY sofort ab (exit 53)
    needs_display = True # SE legt ein (unsichtbares) Fenster an - ohne Display: nodrv_CreateWindow
    install_note = "Windows-Binary (.NET) unter Wine; kein RCON - Start/Stop und XML-Config"

    # So macht es auch das AMP-Template: native DLL-Overrides und die Linux-Bibliotheken
    # aus ./linux64 in den Suchpfad - ohne LD_LIBRARY_PATH scheitert der Start unter Wine.
    wine_overrides = "mscoree=n,b;mshtml=n,b"
    extra_env = {"LD_LIBRARY_PATH": "{dir}/linux64"}
    settings_fields = (
        ("session_name", "Servername", "Name in der Serverliste", "text"),
        ("max_players", "Max. Spieler", "gleichzeitige Spieler", "int"),
        ("port", "Spiel-Port", "UDP, Standard 27016", "int"),
        ("rcon_password", "Server-Passwort", "leer = offen", "password"),
    )

    # Ein gemeinsames Prefix fuer alle SE-Instanzen: dotnet48 nur einmal installieren
    SHARED_PREFIX = os.path.expanduser("~/.polypanel-wine-se")

    def wine_prefix(self, inst) -> str:
        return os.path.expanduser(inst.wine_prefix) if getattr(inst, "wine_prefix", "") else self.SHARED_PREFIX

    def runtime_ready(self, inst) -> bool:
        pref = self.wine_prefix(inst)
        # Fertig-Marker nach dem AMP-Rezept, oder: Wein-Mono + VC++ liegen im Prefix
        if os.path.exists(os.path.join(pref, ".se-runtime-ok")):
            return True
        mono = os.path.isdir(os.path.join(pref, "drive_c", "windows", "mono"))
        vc = os.path.exists(os.path.join(pref, "drive_c", "windows", "system32", "msvcp140.dll"))
        return bool(mono and vc)

    def post_install(self, inst, log=print) -> None:
        self.ensure_runtime(inst, log)

    def ensure_runtime(self, inst, log=print) -> bool:
        """Laufzeit wie im AMP-Template einrichten.

        AMP startet Space Engineers unter Wine mit: wine-mono (statt dotnet48), `win11`,
        `vcrun2022` und `corefonts`, alles unter Xvfb. Genau diese Kombination funktioniert;
        dotnet48 im 64-Bit-Prefix hinterlaesst dagegen eine kaputte machine.config
        („Section names beginning with config are reserved").
        """
        pref = self.wine_prefix(inst)
        if self.runtime_ready(inst):
            log("SE: Laufzeit bereits vorhanden (%s)" % pref)
            return True
        tricks = shutil.which("winetricks")
        if not tricks:
            log("SE: winetricks fehlt - bitte 'winetricks' installieren (Paket winetricks)")
            return False
        os.makedirs(pref, exist_ok=True)
        env = {**os.environ, "WINEPREFIX": pref, "WINEARCH": "win64", "WINEDEBUG": "-all"}
        # winetricks und msiexec starten Windows-Installer: ohne Display bricht das mit
        # Status 126 ab ("XDG_RUNTIME_DIR is invalid or not set"). Deshalb unter Xvfb.
        xvfb = shutil.which("xvfb-run")
        vorlauf = [xvfb, "-a"] if (xvfb and not os.environ.get("DISPLAY")) else []

        # 1) wine-mono: liefert .NET Framework fuer den Server
        if not os.path.isdir(os.path.join(pref, "drive_c", "windows", "mono")):
            msi = os.path.join(pref, "mono.msi")
            quelle = "https://dl.winehq.org/wine/wine-mono/9.1.0/wine-mono-9.1.0-x86.msi"
            log("SE: lade wine-mono (%s)" % quelle)
            try:
                import urllib.request
                urllib.request.urlretrieve(quelle, msi)
                log("SE: installiere wine-mono (2-3 min)")
                subprocess.run(vorlauf + ["wine", "msiexec", "/i", msi, "/qn", "/norestart"],
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                               timeout=900)
            except (OSError, subprocess.SubprocessError) as exc:
                log("SE: wine-mono fehlgeschlagen: %s" % exc)
                return False

        # 2) Prefix auf Windows 11, VC++ 2022 (x64) und Schriften
        for paket, marker, dauer in (("win11", ".win11-ok", "Sekunden"),
                                     ("vcrun2022", ".vcrun2022-ok", "2-3 min"),
                                     ("corefonts", ".corefonts-ok", "1 min")):
            if os.path.exists(os.path.join(pref, marker)):
                continue
            log("SE: winetricks %s (%s)" % (paket, dauer))
            try:
                rc = subprocess.run(vorlauf + [tricks, "-q", paket], env=env,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT,
                                    timeout=2400).returncode
            except (OSError, subprocess.TimeoutExpired) as exc:
                log("SE: %s fehlgeschlagen: %s" % (paket, exc))
                return False
            if rc != 0:
                log("SE: winetricks %s endete mit %s" % (paket, rc))
                return False
            open(os.path.join(pref, marker), "w").write("ok\n")

        ok = self.runtime_ready(inst)
        if ok:
            open(os.path.join(pref, ".se-runtime-ok"), "w").write("ok\n")
        log("SE: Laufzeit %s" % ("fertig" if ok else "unvollstaendig"))
        return ok

    def exe(self, inst) -> str:
        # Installation liefert nur die Windows-Variante (DedicatedServer64), daher Wine.
        return os.path.join(inst.directory, "DedicatedServer64", "SpaceEngineersDedicated.exe")

    def config_file(self, inst) -> str:
        for rel in (CFG_NAME, os.path.join("DedicatedServer", CFG_NAME)):
            p = os.path.join(inst.directory, rel)
            if os.path.exists(p):
                return p
        return os.path.join(inst.directory, CFG_NAME)

    def mods_search(self, inst, query: str) -> dict:
        """Steam-Workshop von Space Engineers durchsuchen (App 244850, ohne Key)."""
        from . import steam_workshop
        data = steam_workshop.hits("244850", query, limit=24)
        vorhanden = set(self.workshop_ids(inst))
        for treffer in data.get("results") or []:
            treffer["installed"] = str(treffer.get("id")) in vorhanden
        return data

    def workshop_ids(self, inst) -> list[str]:
        """Eingetragene Workshop-IDs aus <Mods> der Server-Config."""
        try:
            tree = ET.parse(self.config_file(inst))
        except (OSError, ET.ParseError):
            return []
        ids = []
        for item in tree.getroot().findall(".//Mods/ModItem"):
            pid = (item.findtext("PublishedFileId") or "").strip()
            if pid:
                ids.append(pid)
        return ids

    def mods_install(self, inst, mod_id: str, log=print) -> str:
        """Workshop-ID in <Mods> eintragen (SE laedt sie beim Start)."""
        from ..control import ControlError
        mid = str(mod_id).strip()
        if not mid.isdigit():
            raise ControlError("Das ist keine Workshop-ID (nur Ziffern)")
        path = self.config_file(inst)
        if not os.path.exists(path):
            raise ControlError("Server-Config fehlt noch - erst installieren")
        if mid in self.workshop_ids(inst):
            return "Mod %s ist bereits eingetragen." % mid
        try:
            tree = ET.parse(path)
        except (OSError, ET.ParseError) as exc:
            raise ControlError("Config nicht lesbar: %s" % exc) from exc
        root = tree.getroot()
        mods = root.find("Mods")
        if mods is None:
            mods = ET.SubElement(root, "Mods")
        item = ET.SubElement(mods, "ModItem")
        ET.SubElement(item, "Name").text = "Mod %s" % mid
        ET.SubElement(item, "PublishedFileId").text = mid
        if hasattr(ET, "indent"):
            ET.indent(tree, space="  ")
        tree.write(path, encoding="utf-8", xml_declaration=True)
        log("Workshop-ID %s eingetragen" % mid)
        return ("Workshop-ID %s eingetragen - Space Engineers lädt die Mod beim nächsten "
                "Start (Config: %s)." % (mid, os.path.basename(path)))

    def mods_path(self, inst) -> str:
        # SE laedt Mods aus Content\Mods (Workshop-Downloads landen dort)
        for rel in (os.path.join("Content", "Mods"), "Mods"):
            pfad = os.path.join(inst.directory, rel)
            if os.path.isdir(pfad):
                return pfad
        return os.path.join(inst.directory, "Mods")

    def log_path(self, inst) -> str:
        """SE schreibt pro Start eine eigene Logdatei - immer die neueste zeigen."""
        import glob
        dateien = glob.glob(os.path.join(inst.directory, "SpaceEngineersDedicated_*.log"))
        if dateien:
            return max(dateien, key=os.path.getmtime)
        return os.path.join(inst.directory, LOG_REL)

    def workdir(self, inst) -> str:
        # MUSS DedicatedServer64 sein, sonst findet der Server seine Bibliotheken nicht
        return os.path.dirname(self.exe(inst))

    @staticmethod
    def _win(path: str) -> str:
        return "Z:" + path.replace("/", chr(92))

    def save_world(self, inst) -> str:
        """Save-Ordner im Wine-Prefix (SE schreibt immer in AppData)."""
        user = "ronny"
        pref = self.wine_prefix(inst)
        users = os.path.join(pref, "drive_c", "users")
        if os.path.isdir(users):
            echte = [u for u in os.listdir(users) if u not in ("Public", "Default")]
            if echte:
                user = echte[0]
        bs = chr(92)
        return ("C:" + bs + "users" + bs + user + bs + "AppData" + bs + "Roaming"
                + bs + "SpaceEngineersDedicated" + bs + "Saves" + bs + inst.name)

    def premade_world(self, inst) -> str:
        return os.path.join(inst.directory, "Content", "CustomWorlds", "Star System")

    def launch_argv(self, inst) -> list[str]:
        # ohne diese Schalter startet nur der GUI-Konfigurator (bleibt stumm stehen)
        argv = [self.exe(inst), "-noconsole", "-ignorelastsession",
                "-ip", "0.0.0.0", "-path", self._win(inst.directory)]
        if inst.extra_args:
            argv.extend(inst.extra_args.split())
        return argv

    # ------------------------------------------------------------ Einstellungen
    def _read_cfg(self, inst) -> list[tuple[str, str]]:
        try:
            return self._parse_cfg(open(self.config_file(inst), encoding="utf-8", errors="replace").read())
        except OSError:
            return []

    def _parse_cfg(self, text: str) -> list[tuple[str, str]]:
        try:
            tree = ET.ElementTree(ET.fromstring(text))
        except ET.ParseError:
            return []
        out: list[tuple[str, str]] = []
        seen = set()

        def _add(tag, text):
            if tag in seen:
                return
            seen.add(tag)
            out.append((tag, text or ""))

        root = tree.getroot()
        # SessionSettings zuerst (Spielregeln), danach die Dedicated-Elemente des Wurzelknotens
        for node in root:
            tag = node.tag.split("}")[-1]
            if tag in ("SessionSettings", "DedicatedConfig"):
                for child in node:
                    _add(child.tag, child.text)
        for node in root:
            tag = node.tag.split("}")[-1]
            if tag not in ("SessionSettings", "DedicatedConfig"):
                _add(tag, node.text)
        return out

    # Feste Spielwerte als Auswahlliste (Enum-Werte laut SessionSettings-Referenz).
    # Achtung: BlockLimitsEnabled ist ein Enum - "true"/"false" macht die ganze Datei unlesbar
    # (SE faellt dann auf Standardwerte zurueck und meldet "Premade world not found").
    _BOOL = {"EnableIngameScripts", "PauseGameWhenEmpty", "IgnoreLastSession", "ScenarioEditMode",
             "EnableSaving", "EnableSpectator"}
    # Klartext-Beschriftungen fuer die Auswahl (Wert bleibt der Enum-Name)
    CHOICE_LABELS = {
        "BlockLimitsEnabled": {"NONE": "aus (NONE)", "GLOBALLY": "an – global (GLOBALLY)",
                               "PER_FACTION": "an – pro Fraktion (PER_FACTION)",
                               "PER_PLAYER": "an – pro Spieler (PER_PLAYER)"},
        "GameMode": {"Survival": "Überleben (Survival)", "Creative": "Kreativ (Creative)"},
        "OnlineMode": {"PUBLIC": "öffentlich", "FRIENDS": "nur Freunde",
                       "PRIVATE": "privat", "OFFLINE": "offline"},
    }
    CHOICES = {
        "BlockLimitsEnabled": ["NONE", "GLOBALLY", "PER_FACTION", "PER_PLAYER"],
        "OnlineMode": ["PUBLIC", "FRIENDS", "PRIVATE", "OFFLINE"],
        "GameMode": ["Survival", "Creative"],
        "VoxelGeneratorVersion": ["2", "3"],
    }

    def settings(self, inst) -> list[dict]:
        props = self._read_cfg(inst)
        if not props:
            # Noch nicht installiert: die mitgelieferte Vorlage liefert schon alle Felder,
            # danach werden die restlichen bekannten Optionen leer angeboten (Standard).
            vorlage = self._render_template(inst)
            if vorlage:
                props = self._parse_cfg(vorlage)
        if not props:
            return super().settings(inst)
        aliases = {"ServerName": "session_name", "MaxPlayers": "max_players",
                   "ServerPort": "port", "Password": "rcon_password"}
        out = []
        for name, value in props:
            alias = aliases.get(name)
            if alias:
                value = str(getattr(inst, alias, value))
            label, hint = LABELS.get(name, (name, ""))
            eintrag = {"file": "instance", "section": "", "key": name, "label": label,
                       "hint": hint, "type": "text", "value": str(value),
                       "group": _group_of(name)}
            if name in self.CHOICES:
                eintrag["type"] = "select"
                eintrag["choices"] = list(self.CHOICES[name])
                if name in self.CHOICE_LABELS:
                    eintrag["labels"] = dict(self.CHOICE_LABELS[name])
                if str(value) and str(value) not in eintrag["choices"]:
                    eintrag["choices"].insert(0, str(value))
            out.append(eintrag)
        # Optionen, die (noch) nicht in der Datei stehen, trotzdem anbieten: leer = Standard
        vorhanden = {name for name, _ in props}
        for name, (label, hint) in LABELS.items():
            if name in vorhanden:
                continue
            from .. import i18n as _i18n
            out.append({"file": "instance", "section": "", "key": name, "label": label,
                        "hint": (hint + " · " if hint else "") + _i18n.get("setg.not_set"),
                        "type": "text", "value": "", "group": _group_of(name)})
        return out

    def apply_settings(self, inst, items) -> int:
        path = self.config_file(inst)
        if not os.path.exists(path):
            self.write_config(inst)          # Datei fehlt (noch nicht installiert) -> aus der Vorlage
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return super().apply_settings(inst, items)
        aliases = {"ServerName": "session_name", "MaxPlayers": "max_players",
                   "ServerPort": "port", "Password": "rcon_password"}
        changed = 0
        for item in items:
            key, val = item.get("key"), str(item.get("value", ""))
            if not key:
                continue
            # Ein einziger ungueltiger Wert macht die komplette Datei unlesbar: SE faellt dann
            # still auf Standardwerte zurueck (Folge: "Premade world not found"). Darum hier sperren.
            if key in self.CHOICES and val and val not in self.CHOICES[key]:
                # "true"/"false" nicht in die Datei schreiben (macht sie unlesbar), aber
                # als Wunsch verstehen: an -> GLOBALLY, aus -> NONE
                ersatz = {"true": "GLOBALLY", "false": "NONE"}.get(val.lower())
                if ersatz and ersatz in self.CHOICES[key]:
                    val = ersatz
                else:
                    continue
            if key in self._BOOL and val and val not in ("true", "false"):
                continue
            pattern = re.compile(r"(<%s>)(.*?)(</%s>)" % (re.escape(key), re.escape(key)), re.S)
            if pattern.search(text):
                text = pattern.sub(lambda m: m.group(1) + val + m.group(3), text, count=1)
            elif val != "" and key in LABELS:
                # Option ist in der Datei noch nicht vorhanden: passend einsetzen
                eintrag = "    <%s>%s</%s>\n" % (key, val, key)
                if "</SessionSettings>" in text:
                    text = text.replace("  </SessionSettings>", eintrag + "  </SessionSettings>", 1)
            else:
                continue                  # leer und nicht vorhanden = Standard bleibt
            alias = aliases.get(key)
            if alias:
                cur = getattr(inst, alias, "")
                setattr(inst, alias, int(val) if isinstance(cur, int) and val.isdigit() else val)
            changed += 1
        if changed:
            open(path, "w", encoding="utf-8").write(text)
        return changed

    def _render_template(self, inst) -> str:
        """Vorlage mit den Werten der Instanz fuellen (Platzhalter ersetzen)."""
        try:
            text = open(TEMPLATE, encoding="utf-8").read()
        except OSError:
            return ""
        return (text.replace("{{SERVERNAME}}", inst.session_name)
                        .replace("{{MAXPLAYERS}}", str(inst.max_players))
                        .replace("{{PORT}}", str(inst.port))
                        .replace("{{STEAMPORT}}", str(inst.query_port or 8766))
                        .replace("{{IP}}", "0.0.0.0")
                        .replace("{{WORLDNAME}}", inst.name)
                        .replace("{{LOADWORLD}}", self.save_world(inst))
                        .replace("{{PREMADE}}", self._win(self.premade_world(inst)))
                        .replace("{{SCENARIO}}", "StarSystem")
                    .replace("{{ONLINEMODE}}", "PUBLIC" if inst.rcon_password else "FRIENDS"))

    def write_config(self, inst) -> None:
        path = self.config_file(inst)
        if not os.path.exists(path):
            # SE legt die Datei nicht selbst an - PolyPanel bringt die Vorlage mit
            text = self._render_template(inst)
            if not text:
                return
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, "w", encoding="utf-8").write(text)
            return
        text = open(path, encoding="utf-8", errors="replace").read()
        for key, val in (("ServerName", inst.session_name), ("MaxPlayers", str(inst.max_players)),
                         ("ServerPort", str(inst.port)), ("Password", inst.rcon_password or "")):
            text = re.sub(r"(<%s>)(.*?)(</%s>)" % (key, key),
                          lambda m: m.group(1) + val + m.group(3), text, count=1, flags=re.S)
        open(path, "w", encoding="utf-8").write(text)

    def ready(self, inst) -> bool:
        from .base import _tcp_open
        return _tcp_open("127.0.0.1", inst.port, timeout=2) or \
            os.path.exists(self.log_path(inst))

    def graceful_stop(self, inst) -> list[str]:
        # SE versteht Konsolenbefehle auf stdin: erst speichern, dann beenden
        from .. import runner
        steps = []
        for cmd in ("save", "stop"):
            try:
                steps.append("%s: %s" % (cmd, runner.send_console(inst, cmd)))
            except Exception as exc:            # noqa: BLE001 - Stop darf nie scheitern
                steps.append("%s fehlgeschlagen (%s)" % (cmd, exc.__class__.__name__))
                break
        return steps

# Restliche SessionSettings-Felder (deutsch)
LABELS.update({
    "GameMode": ("Spielmodus", "Survival oder Creative"),
    "InventorySizeMultiplier": ("Inventargroesse (Faktor)", "1 = normal, 10 = riesig"),
    "AssemblerSpeedMultiplier": ("Montierer-Geschwindigkeit", "Faktor"),
    "AssemblerEfficiencyMultiplier": ("Montierer-Effizienz", "Faktor"),
    "RefinerySpeedMultiplier": ("Raffinerie-Geschwindigkeit", "Faktor"),
    "OnlineMode": ("Online-Modus", "Public, Friends oder Offline"),
    "MaxPlayers": ("Max. Spieler", "gleichzeitige Spieler"),
    "MaxFloatingObjects": ("Max. freie Objekte", "schwebende Teile, Performance"),
    "MaxBackupSaves": ("Backup-Speicherstaende", "Anzahl automatischer Backups"),
    "EnvironmentHostility": ("Umgebung", "SAFE, NORMAL, EASY, HARD"),
    "AutoHealing": ("Auto-Heilung", "true/false"),
    "EnableCopyPaste": ("Kopieren/Einfuegen", "true = Blueprint-Copy erlaubt"),
    "WeaponsEnabled": ("Waffen", "true = Waffen aktiv"),
    "ShowPlayerNamesOnHud": ("Spielernamen im HUD", "true/false"),
    "ThrusterDamage": ("Triebwerksschaden", "true = Triebwerke verursachen Schaden"),
    "CargoShipsEnabled": ("Frachtschiffe", "true = NPC-Frachter unterwegs"),
    "EnableSpectator": ("Zuschauermodus", "true = Spectator erlaubt"),
    "RemoveTrash": ("Muell entfernen", "true = alte Objekte loeschen"),
    "WorldSizeKm": ("Weltgroesse (km)", "0 = unbegrenzt"),
    "RespawnShipDelete": ("Respawn-Schiff loeschen", "true = nach Verlassen entfernen"),
    "ResetOwnership": ("Eigentum zuruecksetzen", "true = Bloecke werden herrenlos"),
    "WelderSpeedMultiplier": ("Schweisser-Geschwindigkeit", "Faktor"),
    "GrinderSpeedMultiplier": ("Schleifer-Geschwindigkeit", "Faktor"),
    "RealisticSound": ("Realistischer Sound", "true/false"),
    "HackSpeedMultiplier": ("Hack-Geschwindigkeit", "Faktor"),
    "PermanentDeath": ("Permanenter Tod", "true = kein Respawn"),
    "AutoSaveInMinutes": ("Autosave (Minuten)", "0 = aus"),
    "SpawnShipTimeMultiplier": ("Respawn-Zeit (Faktor)", "hoeher = laenger"),
    "DestructibleBlocks": ("Zerstoerbare Bloecke", "true/false"),
    "EnableIngameScripts": ("Ingame-Skripte", "true = Programmable Block erlaubt"),
    "ViewDistance": ("Sichtweite", "in Metern"),
    "FloraDensity": ("Pflanzendichte", "0-100"),
    "EnableToolShake": ("Werkzeug-Ruckeln", "true/false"),
    "VoxelGeneratorVersion": ("Voxel-Generator", "Version der Weltgenerierung"),
    "EnableOxygen": ("Sauerstoff", "true = Sauerstoffsystem aktiv"),
    "EnableOxygenPressurization": ("Druckluft", "true = Raume luftdicht"),
    "Enable3rdPersonView": ("Third-Person-Kamera", "true/false"),
    "EnableEncounters": ("Begegnungen", "true = NPC-Stationen/Schiffe"),
    "EnableFlora": ("Pflanzen", "true = Flora vorhanden"),
    "EnableConvertToStation": ("Zu Station umbauen", "true = Grids umwandelbar"),
    "EnableSunRotation": ("Sonnenrotation", "true = Tag/Nacht-Zyklus"),
    "DisableRespawnShips": ("Respawn-Schiffe aus", "true = keine Startschiffe"),
    "ScenarioEditMode": ("Szenario-Editor", "true = Bearbeitungsmodus"),
    "Battle": ("Kampfmodus", "true = Battle-Szenario"),
    "Scenario": ("Szenario aktiv", "true = Szenario statt Sandbox"),
    "CanJoinRunning": ("Beitritt im Lauf", "true = spaeter einsteigen erlaubt"),
    "PhysicsIterations": ("Physik-Iterationen", "hoeher = genauer, langsamer"),
    "SunRotationIntervalMinutes": ("Sonnenumlauf (Minuten)", "Laenge eines Tages"),
    "EnableJetpack": ("Jetpack", "true/false"),
    "SpawnWithTools": ("Start mit Werkzeug", "true/false"),
    "StartInRespawnScreen": ("Start im Respawn-Screen", "true/false"),
    "EnableVoxelDestruction": ("Voxel-Zerstoerung", "true = Gestein zerstörbar"),
    "MaxDrones": ("Max. Drohnen", "Anzahl"),
    "EnableDrones": ("Drohnen", "true/false"),
    "EnableCyberhounds": ("Cyberhounds", "true/false"),
    "EnableSpiders": ("Spinnen", "true/false"),
    "FloraDensityMultiplier": ("Pflanzendichte (Faktor)", "Faktor auf die Basis"),
    "EnableStructuralSimulation": ("Struktur-Simulation", "true = Verbindungen brechen"),
    "MaxActiveFracturePieces": ("Max. Bruchstuecke", "Performance"),
})

# Restliche Optionen (ausgelagert, damit die Datei lesbar bleibt)
from .se_labels import EXTRA as _SE_EXTRA, GRUPPE as _SE_GRUPPE   # noqa: E402
LABELS.update(_SE_EXTRA)
