"""StarRupture Dedicated Server (Windows-Payload, Steam-App 3809400).

StarRupture liefert nur einen **Windows**-Server; unter Linux laeuft er wie ARK
unter Wine. Es gibt keinen RCON- und keinen HTTP-Kanal, also steuert das Panel
Prozess (Start/Stop/Update), Konfigdatei und Ports.

Am echten 20-GB-Installationsbaum verifiziert (VPS, 2026-11-15):
- `StarRuptureServerEOS.exe` (273 KB) im Wurzelverzeichnis ist nur ein
  **Bootstrapper** und startet unter Wine nicht zuverlaessig. Das laufende
  Programm ist `StarRupture/Binaries/Win64/StarRuptureServerEOS-Win64-Shipping.exe`
  (233 MB); dieses bootet bis "Starting Game" - es wird direkt gestartet.
- Ohne X-Server bricht Wine mit exit 44 ab ("no driver could be loaded"),
  deshalb xvfb-run. Zusaetzlich muss vc_redist im Prefix liegen
  (`Engine/Extras/Redist/en-us/vc_redist.x64.exe`) - erledigt `prepare_start`.
- Konfiguration: **`DSSettings.txt` im Serverwurzelverzeichnis, Inhalt ist JSON**
  (kein INI): SessionName, SaveGameInterval, StartNewGame, LoadSavedGame, SaveGameName.
- Ports stehen in der Startzeile (`-Port=`, `-QueryPort=`), Standard UDP 7777.
- Erste Sitzung: im Spiel "Join Game" -> "Dedicated Server" -> IP:Port ->
  "Manage Server". Ohne EOS-Anmeldung erscheint der Server nicht im Browser
  ("Autologin attempt failed"), direkte Verbindung per IP:Port geht trotzdem.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess

from .base import GameProfile

BOOTSTRAPPER = "StarRuptureServerEOS.exe"
SHIPPING = os.path.join("StarRupture", "Binaries", "Win64",
                        "StarRuptureServerEOS-Win64-Shipping.exe")
CFG_NAME = "DSSettings.txt"
MARKER = ".PolyPanel-vcredist"


def _udp_port_bound(port: int) -> bool:
    """Laeuft ein UDP-Listener auf diesem Port? (kein Handshake, /proc lesen)"""
    ziel = "%04X" % port
    for pfad in ("/proc/net/udp", "/proc/net/udp6"):
        try:
            with open(pfad, encoding="utf-8") as fh:
                next(fh, None)
                for zeile in fh:
                    teile = zeile.split()
                    if len(teile) > 1 and teile[1].split(":")[-1] == ziel:
                        return True
        except OSError:
            continue
    return False


def _xvfb() -> list[str]:
    """Ohne Display bricht der UE5-Server unter Wine mit exit 44 ab."""
    if os.environ.get("DISPLAY"):
        return []
    xvfb = shutil.which("xvfb-run")
    return [xvfb, "-a"] if xvfb else []


class StarRuptureProfile(GameProfile):
    key = "starrupture"
    label = "StarRupture (Dedicated Server)"
    server_app_id = "3809400"

    needs_wine = True
    needs_display = True             # UE5 braucht ein Fenster (exit 44 ohne X-Server)
    has_control = False              # kein RCON/API
    supports_mods = False
    supports_cluster = False
    supports_whitelist = False
    use_pty = True

    default_game_port = 7777
    default_query_port = 7778
    default_control_port = 0         # kein Steuerkanal
    default_max_players = 8

    install_note = ("Windows-Server unter Wine/Proton. Erste Sitzung im Spiel anlegen: "
                    "\"Join Game\" -> \"Dedicated Server\" -> IP:Port -> \"Manage Server\". "
                    "Konfiguration: DSSettings.txt (JSON) im Serverordner.")

    settings_fields = (
        ("session_name", "Session-Name", "Ordnername der Welt unter StarRupture/Saved/SaveGames", "text"),
        ("max_players", "Max. Spieler", "Vanilla-Grenze liegt bei 8", "int"),
        ("port", "Spielport (UDP)", "Standard 7777", "int"),
        ("server_password", "Server-Passwort", "Passwort beim Beitreten (leer = offen)", "password"),
        ("admin_password", "Admin-Passwort", "fuer \"Manage Server\" im Spiel", "password"),
    )

    # ----------------------------------------------------------------- Pfade
    def exe(self, inst) -> str:
        echt = os.path.join(inst.directory, SHIPPING)
        if os.path.exists(echt):
            return echt
        for muster in ("*/Binaries/Win64/*Server*-Shipping.exe", BOOTSTRAPPER, "*.exe"):
            treffer = sorted(glob.glob(os.path.join(inst.directory, muster)))
            if treffer:
                return treffer[0]
        return echt

    def workdir(self, inst) -> str:
        # Muss die Serverwurzel sein: dort liegt DSSettings.txt, und dort legt das
        # Spiel StarRupture/Saved an.
        return inst.directory

    def config_path(self, inst) -> str:
        return os.path.join(inst.directory, CFG_NAME)

    def log_path(self, inst) -> str:
        return os.path.join(inst.directory, "StarRupture", "Saved", "Logs", "StarRupture.log")

    # ------------------------------------------------------------ Startzeile
    def launch_prefix(self, inst) -> list[str]:
        """xvfb-run vor wine: der UE5-Server bricht ohne X-Server mit exit 44 ab."""
        return _xvfb()

    def launch_argv(self, inst) -> list[str]:
        argv = [self.exe(inst), "-log"]
        port = int(getattr(inst, "port", self.default_game_port) or self.default_game_port)
        argv.append("-Port=%d" % port)
        qport = int(getattr(inst, "query_port", 0) or 0)
        if qport and qport != port:
            argv.append("-QueryPort=%d" % qport)
        if getattr(inst, "extra_args", ""):
            argv.extend(inst.extra_args.split())
        return argv

    # ---------------------------------------------------------- Konfigdatei
    def write_config(self, inst) -> None:
        """DSSettings.txt als JSON schreiben - vorhandene Werte bleiben erhalten.

        Die Datei ist kein INI; ein falsches Format (oder ein ueberzaehliges Komma)
        haelt den Server beim Start an. Deshalb wird sie als JSON gelesen und
        geschrieben und bei Schaeden neu aufgebaut.
        """
        pfad = self.config_path(inst)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        daten = {}
        if os.path.exists(pfad):
            try:
                with open(pfad, encoding="utf-8", errors="replace") as fh:
                    roh = fh.read().strip()
                if roh:
                    geladen = json.loads(roh)
                    if isinstance(geladen, dict):
                        daten = geladen
            except (OSError, ValueError):
                daten = {}

        name = (getattr(inst, "session_name", "") or inst.name).strip() or "StarRupture"
        daten.setdefault("SessionName", name)
        daten.setdefault("SaveGameInterval", "300")
        daten.setdefault("StartNewGame", "true")
        daten.setdefault("LoadSavedGame", "false")
        daten.setdefault("SaveGameName", "AutoSave0.sav")
        if not str(daten.get("SessionName") or "").strip():
            daten["SessionName"] = name

        # Existiert die Welt schon, darf ein Neustart sie nicht neu erzeugen:
        # dann StartNewGame=false + LoadSavedGame=true (sonst steht man nach jedem
        # Restart in einer leeren Welt neben dem alten Speicherstand).
        speicher = os.path.join(inst.directory, "StarRupture", "Saved", "SaveGames",
                                str(daten["SessionName"]),
                                str(daten.get("SaveGameName") or "AutoSave0.sav"))
        if os.path.exists(speicher):
            daten["StartNewGame"] = "false"
            daten["LoadSavedGame"] = "true"

        # Passwoerter nur schreiben, wenn sie gesetzt sind - ein leeres Feld soll
        # ein bereits im Spiel vergebenes Passwort nicht ueberschreiben.
        for feld, schluessel in (("server_password", "ServerPassword"),
                                 ("admin_password", "AdminPassword")):
            wert = (getattr(inst, feld, "") or "").strip()
            if wert:
                daten[schluessel] = wert

        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(daten, fh, indent=2)
            fh.write("\n")

    # -------------------------------------------------- Laufzeit vorbereiten
    def prepare_start(self, inst, log=print) -> None:
        """VC++-Runtime einmalig in den Wine-Prefix legen (sonst startet UE5 nicht)."""
        marke = os.path.join(inst.directory, MARKER)
        if os.path.exists(marke):
            return
        quelle = os.path.join(inst.directory, "Engine", "Extras", "Redist", "en-us",
                              "vc_redist.x64.exe")
        if not os.path.exists(quelle):
            log("StarRupture: vc_redist.x64.exe fehlt - Installation unvollstaendig?")
            return
        env = {**os.environ, "WINEDEBUG": "-all"}
        if getattr(inst, "wine_prefix", ""):
            env["WINEPREFIX"] = os.path.expanduser(inst.wine_prefix)
        log("StarRupture: installiere VC++-Runtime im Wine-Prefix (einmalig)")
        try:
            lauf = subprocess.run(_xvfb() + ["wine", quelle, "/quiet", "/norestart"],
                                  cwd=inst.directory, env=env, timeout=900,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        except (OSError, subprocess.SubprocessError) as exc:
            log("StarRupture: vc_redist fehlgeschlagen: %s" % exc)
            return
        if lauf.returncode in (0, 3010):
            with open(marke, "w", encoding="utf-8") as fh:
                fh.write("ok\n")
            log("StarRupture: VC++-Runtime eingerichtet")
        else:
            log("StarRupture: vc_redist exit %s - Start trotzdem versuchen" % lauf.returncode)

    # ---------------------------------------------------------- Steuerkanal
    def ready(self, inst) -> bool:
        """Bereit = der UDP-Spielport ist belegt (kein Handshake verfuegbar)."""
        return _udp_port_bound(int(getattr(inst, "port", self.default_game_port)))

    def players(self, inst):
        """Ohne Steuerkanal gibt es keine belastbare Spielerliste."""
        return None
