"""Satisfactory Dedicated Server (Linux, nativ).

Steam-App-ID 1690800, Start ueber `FactoryServer.sh`, drei Ports (Spiel, Query,
Beacon), Konfiguration unter `FactoryGame/Saved/Config/LinuxServer/`, Steuerung
ueber die HTTPS-API (`/api/v1`, Bearer-Token).
"""
from __future__ import annotations

import configparser
import io
import json
import os
import urllib.parse
import urllib.request
import zipfile

from .base import GameProfile

CONFIG_REL = os.path.join("FactoryGame", "Saved", "Config", "LinuxServer")
LOG_REL = os.path.join("FactoryGame", "Saved", "Logs", "FactoryGame.log")


class SatisfactoryProfile(GameProfile):
    key = "satisfactory"
    label = "Satisfactory (Dedicated Server)"
    server_app_id = "1690800"
    control_kind = "https"
    needs_wine = False
    default_game_port = 7777
    default_query_port = 15777
    default_control_port = 7777      # API laeuft auf dem Spielport
    supports_mods = False
    install_note = "nativ, kein Wine; Beacon-Port 15000 zusaetzlich freigeben"
    settings_fields = (
        ("session_name", "Spieleserver-Name", "erscheint in der Serverliste", "text"),
        ("max_players", "Max. Spieler", "gleichzeitige Spieler", "int"),
        ("port", "Spiel-Port", "UDP, Spielverbindung", "int"),
        ("query_port", "Query-Port", "UDP, Serverabfrage", "int"),
        ("beacon_port", "Beacon-Port", "UDP, fuer die Serverliste", "int"),
        ("rcon_password", "Server-Passwort", "leer = kein Passwort", "password"),
        ("api_token", "API-Token", "im Server-Konsolbefehl server.GenerateAPIToken erzeugen", "password"),
    )

    # ---------------------------------------------------------------- Pfade
    def exe(self, inst) -> str:
        return os.path.join(inst.directory, "FactoryServer.sh")

    @property
    def config_dir(self) -> str:
        return ""

    def mods_path(self, inst) -> str:
        return os.path.join(inst.directory, "FactoryGame", "Mods")

    def log_path(self, inst) -> str:
        return os.path.join(inst.directory, LOG_REL)

    def server_ini(self, inst) -> str:
        return os.path.join(inst.directory, CONFIG_REL, "GameUserSettings.ini")

    def engine_ini(self, inst) -> str:
        return os.path.join(inst.directory, CONFIG_REL, "Engine.ini")

    # ------------------------------------------------------------ Startzeile
    def launch_argv(self, inst) -> list[str]:
        argv = [
            "/bin/sh",
            "FactoryServer.sh",
            "-multihome=0.0.0.0",
            "-Port=%d" % inst.port,
            "-QueryPort=%d" % inst.query_port,
            "-BeaconPort=%d" % inst.beacon_port,
        ]
        if inst.extra_args:
            argv.extend(inst.extra_args.split())
        return argv

    # ---------------------------------------------------------- Konfigdatei
    def write_config(self, inst) -> None:
        """Ports/Name/Passwort in die INI schreiben (Satisfactory liest sie beim Start)."""
        cfg_dir = os.path.join(inst.directory, CONFIG_REL)
        os.makedirs(cfg_dir, exist_ok=True)

        cp = configparser.ConfigParser(strict=False)
        cp.optionxform = str
        path = self.server_ini(inst)
        if os.path.exists(path):
            cp.read(path, encoding="utf-8-sig")
        section = "/Script/FactoryGame.FGServerSettings"
        if not cp.has_section(section):
            cp.add_section(section)
        cp.set(section, "ServerName", inst.session_name)
        if inst.rcon_password:
            cp.set(section, "ServerPassword", inst.rcon_password)
        if inst.api_token:
            cp.set(section, "ServerApiToken", inst.api_token)
        cp.set(section, "MaxPlayers", str(inst.max_players))
        with open(path, "w", encoding="utf-8") as fh:
            cp.write(fh, space_around_delimiters=False)

        # Ports gehoeren in die Engine.ini (CLI-Parameter haben Vorrang)
        ecp = configparser.ConfigParser(strict=False)
        ecp.optionxform = str
        epath = self.engine_ini(inst)
        if os.path.exists(epath):
            ecp.read(epath, encoding="utf-8-sig")
        if not ecp.has_section("URL"):
            ecp.add_section("URL")
        ecp.set("URL", "Port", str(inst.port))
        with open(epath, "w", encoding="utf-8") as fh:
            ecp.write(fh, space_around_delimiters=False)

    # ---------------------------------------------------------- Steuerkanal
    def control(self, inst, timeout: float = 10.0):
        from ..control import SatisfactoryApi
        return SatisfactoryApi("127.0.0.1", inst.port, inst.api_token, timeout=timeout)

    def ready(self, inst) -> bool:
        """Satisfactory ist bereit, wenn die HTTPS-API antwortet."""
        from ..control import SatisfactoryApi, ControlError
        try:
            SatisfactoryApi("127.0.0.1", inst.port, inst.api_token, timeout=3).connect()
            return True
        except ControlError:
            return False

    def players(self, inst) -> list[str] | None:
        """Satisfactory kennt kein ListPlayers - Spieler kommen aus QueryServerState."""
        try:
            with self.control(inst, timeout=10) as api:
                data = api._post("QueryServerState")
        except Exception:                       # noqa: BLE001 - Status darf nicht scheitern
            # ohne API-Token liefert der Server 403 "insufficient_scope" - kein Fehler
            return []
        try:
            states = data["serverGameState"]["playerStates"]
        except (KeyError, TypeError):
            return []
        return [p.get("playerName", "?") for p in states if isinstance(p, dict)]


    # ------------------------------------------------------------ Mods (ficsit.app)
    API = "https://api.ficsit.app/v2/query"

    def _gql(self, query: str, timeout: float = 20.0) -> dict:
        payload = json.dumps({"query": query}).encode()
        req = urllib.request.Request(self.API, data=payload,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        if data.get("errors"):
            raise ControlError("ficsit.app: %s" % data["errors"][0].get("message", "Fehler"))
        return data.get("data") or {}

    def mods_search(self, inst, query: str) -> dict:
        from .. import translate
        begriff = translate.query_english(query)      # ficsit.app ist englisch indexiert
        q = json.dumps(begriff if begriff else query)
        # order_by/order sind GraphQL-Enums - unquoted, sonst lehnt ficsit die Abfrage ab.
        # Ohne Sortierung liefert die API beliebige Treffer, das wirkt wie "findet nichts".
        data = self._gql("{getMods(filter:{search:%s,limit:25,order_by:popularity,order:desc})"
                         "{count mods{id name short_description downloads logo}}}" % q)
        mods = (data.get("getMods") or {}).get("mods") or []
        return {"provider": "ficsit.app",
                "search_url": "https://ficsit.app/mods?q=%s" % urllib.parse.quote(query),
                "results": [{"id": m["id"], "name": m["name"],
                             "description": (m.get("short_description") or "")[:160],
                             "downloads": m.get("downloads") or 0,
                             "thumbnail": m.get("logo") or ""} for m in mods]}

    def mods_install(self, inst, mod_id: str, log=print) -> str:
        data = self._gql('{getMod(modId:%s){name versions(filter:{limit:1}){version link}}}'
                         % json.dumps(mod_id))
        mod = data.get("getMod") or {}
        versionen = mod.get("versions") or []
        if not versionen:
            raise ControlError("keine Version gefunden")
        ver = versionen[0]
        pfad = "https://api.ficsit.app" + ver["link"]

        ziel = self.mods_path(inst)
        os.makedirs(ziel, exist_ok=True)
        log("lade %s %s" % (mod.get("name"), ver.get("version")))
        req = urllib.request.Request(pfad, headers={"User-Agent": "noah2games"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            rohdaten = resp.read()
        log("%.1f MB geladen" % (len(rohdaten) / 1024 / 1024))
        with zipfile.ZipFile(io.BytesIO(rohdaten)) as z:
            z.extractall(ziel)
        return "%s %s nach %s entpackt" % (mod.get("name"), ver.get("version"), ziel)

    def graceful_stop(self, inst) -> list[str]:
        """Die API kann den Server sauber herunterfahren (Save inklusive)."""
        api = self.control(inst, timeout=15)
        api.shutdown(force=False)
        return ["Shutdown ueber API gesendet"]
