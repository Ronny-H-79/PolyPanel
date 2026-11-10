"""Satisfactory Dedicated Server (Linux, nativ).

Steam-App-ID 1690800, Start ueber `FactoryServer.sh`, drei Ports (Spiel, Query,
Beacon), Konfiguration unter `FactoryGame/Saved/Config/LinuxServer/`, Steuerung
ueber die HTTPS-API (`/api/v1`, Bearer-Token).
"""
from __future__ import annotations

import configparser
import hashlib
import io
import json
import os
import shutil
import tempfile
import time
import urllib.parse
import urllib.request
import zipfile

from .base import GameProfile
from ..control import ControlError

CONFIG_REL = os.path.join("FactoryGame", "Saved", "Config", "LinuxServer")
LOG_REL = os.path.join("FactoryGame", "Saved", "Logs", "FactoryGame.log")


def _safe_extract(z: zipfile.ZipFile, ziel: str) -> None:
    """Archiv entpacken, ohne ausserhalb von ``ziel`` zu schreiben."""
    basis = os.path.realpath(ziel)
    for name in z.namelist():
        voll = os.path.realpath(os.path.join(ziel, name))
        if voll != basis and not voll.startswith(basis + os.sep):
            raise ControlError("Archiv enthaelt unsichere Pfade: %s" % name)
    z.extractall(ziel)


def _archiv_info(z: zipfile.ZipFile) -> tuple[str, str, bool, str]:
    """Referenz, Wrapper-Ordner, GameFeature-Flag und Version aus dem .uplugin lesen.

    Die ficsit-Archive legen ihren Inhalt auf der Wurzel ab (kein Mod-Ordner);
    kommt doch ein einzelner Wrapper-Ordner, wird er beim Verschieben entfernt.
    """
    upl = sorted((n for n in z.namelist() if n.lower().endswith(".uplugin")),
                 key=lambda n: n.count("/"))
    if not upl:
        raise ControlError("Archiv enthaelt keine .uplugin - das ist keine Mod")
    teile = upl[0].split("/")
    ref = teile[-1][: -len(".uplugin")]
    if not ref or not all(c.isalnum() or c in "._-" for c in ref):
        raise ControlError("unbrauchbarer Mod-Name im Archiv: %r" % ref)
    wrapper = teile[0] if len(teile) > 1 else ""
    try:
        daten = json.loads(z.read(upl[0]).decode("utf-8-sig", "replace"))
    except (ValueError, OSError):
        daten = {}
    return (ref, wrapper, bool(daten.get("GameFeature")),
            str(daten.get("SemVersion") or daten.get("VersionName") or ""))


class SatisfactoryProfile(GameProfile):
    key = "satisfactory"
    label = "Satisfactory (Dedicated Server)"
    server_app_id = "1690800"
    control_kind = "https"
    needs_wine = False
    default_game_port = 7777
    default_query_port = 15777
    default_control_port = 7777      # API laeuft auf dem Spielport
    supports_mods = True
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
        # Sortiert wird nach "downloads": "popularity" ist ein interner Score, damit
        # kamen die Treffer unsortiert zurueck und relevante Mods fehlten oben.
        data = self._gql("{getMods(filter:{search:%s,limit:30,order_by:downloads,order:desc})"
                         "{count mods{id name short_description downloads logo}}}" % q)
        mods = (data.get("getMods") or {}).get("mods") or []
        # Die ficsit-Suche matcht auch Beschreibungen ("train" trifft "Follow Terrain").
        # Treffer mit dem Begriff im Namen zuerst, danach nach Downloads.
        wort = (begriff or query).strip().lower()
        mods.sort(key=lambda m: (0 if wort and wort in (m.get("name") or "").lower() else 1,
                                 -(m.get("downloads") or 0)))
        return {"provider": "ficsit.app",
                "search_url": "https://ficsit.app/mods?q=%s" % urllib.parse.quote(query),
                "results": [{"id": m["id"], "name": m["name"],
                             "description": (m.get("short_description") or "")[:160],
                             "downloads": m.get("downloads") or 0,
                             "thumbnail": m.get("logo") or ""} for m in mods[:25]]}

    def mods_install(self, inst, mod_id: str, log=print) -> str:
        data = self._gql("{getMod(modId:%s){name versions{id version hash created_at link}}}"
                         % json.dumps(mod_id))
        mod = data.get("getMod") or {}
        versionen = [v for v in (mod.get("versions") or []) if v.get("link")]
        if not versionen:
            raise ControlError("keine Version gefunden")
        # Die API liefert die Versionen nicht garantiert in Reihenfolge - neueste nehmen.
        versionen.sort(key=lambda v: v.get("created_at") or "", reverse=True)
        ver = versionen[0]
        pfad = ver["link"]
        if not pfad.startswith("http"):
            pfad = "https://api.ficsit.app" + pfad

        log("lade %s %s" % (mod.get("name"), ver.get("version")))
        req = urllib.request.Request(pfad, headers={"User-Agent": "PolyPanel"})
        with urllib.request.urlopen(req, timeout=120) as resp:
            rohdaten = resp.read()
        if ver.get("hash") and hashlib.sha256(rohdaten).hexdigest() != ver["hash"]:
            raise ControlError("Download unvollstaendig (Pruefsumme passt nicht)")
        log("%.1f MB geladen" % (len(rohdaten) / 1024 / 1024))

        # Die Archive haben ihren Inhalt auf der Wurzel (Binaries/, Content/,
        # <Name>.uplugin). Direkt nach Mods/ entpackt ueberschreiben sich die Mods
        # gegenseitig und SML findet keine Mod - deshalb immer in einen eigenen
        # Ordner, GameFeatures zusaetzlich unter Mods/GameFeatures/.
        with zipfile.ZipFile(io.BytesIO(rohdaten)) as z:
            ref, wrapper, gamefeature, semver = _archiv_info(z)
            ziel = self.mods_path(inst)
            if gamefeature:
                ziel = os.path.join(ziel, "GameFeatures")
            os.makedirs(ziel, exist_ok=True)
            tmp = tempfile.mkdtemp(prefix=".mod-install-", dir=inst.directory)
            try:
                _safe_extract(z, tmp)
            except Exception:
                shutil.rmtree(tmp, ignore_errors=True)
                raise

        quelle = os.path.join(tmp, wrapper) if wrapper else tmp
        ziel_dir = os.path.join(ziel, ref)
        # Alte Fassung ausserhalb von Mods/ sichern: eine Kopie mit .uplugin im
        # Mod-Ordner waere fuer SML eine zweite Mod mit derselben Referenz.
        if os.path.isdir(ziel_dir):
            bdir = os.path.join(inst.directory, ".mods-backup")
            os.makedirs(bdir, exist_ok=True)
            alt = os.path.join(bdir, "%s-%s" % (ref, time.strftime("%Y%m%d-%H%M%S")))
            shutil.move(ziel_dir, alt)
            log("alte Fassung gesichert: %s" % alt)
        shutil.move(quelle, ziel_dir)
        shutil.rmtree(tmp, ignore_errors=True)
        if ver.get("hash"):                 # Markierung, die der Mod Manager erwartet
            try:
                with open(os.path.join(ziel_dir, ".smm"), "w", encoding="utf-8") as fh:
                    fh.write(ver["hash"])
            except OSError:
                pass
        return "%s %s installiert (%s)" % (mod.get("name"),
                                           semver or ver.get("version"),
                                           os.path.relpath(ziel_dir, inst.directory))

    def graceful_stop(self, inst) -> list[str]:
        """Die API kann den Server sauber herunterfahren (Save inklusive)."""
        api = self.control(inst, timeout=15)
        api.shutdown(force=False)
        return ["Shutdown ueber API gesendet"]
