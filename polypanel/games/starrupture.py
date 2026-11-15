"""StarRupture Dedicated Server (Windows-Payload, Steam-App 3809400).

Creepy Jars Koop-Survival liefert nur einen **Windows**-Server aus; unter Linux
laeuft er wie ARK unter Wine/Proton. Es gibt keinen RCON- und keinen HTTP-Kanal,
also steuert das Panel nur Prozess (Start/Stop/Update), Konfigdatei und Ports.

Stand der Recherche (offizielle Anleitung + Community-Guides):
- App-ID 3809400 (SteamCMD, anonymous)
- Startdatei heisst je nach Build `StarRuptureServer.exe` oder
  `StarRuptureServerEOS.exe` - deshalb wird sie gesucht statt geraten.
- Netzwerk: **UDP 7777** (Spielport); Query-/Beacon-Port ist nicht dokumentiert.
- Konfiguration: `DSSettings.txt` im Serverordner (Schluessel-Werte).
- Sitzung: Der Server startet eine Sitzung, die im Spiel ueber "Manage Server"
  erstellt oder geladen wird - ein Weltname in der Startzeile ist nicht belegt.

Unbekannte Punkte sind absichtlich defensiv umgesetzt (Startdatei suchen,
Startzeile minimal, Konfigdatei best effort), damit ein Installationslauf sie
verifizieren kann, statt dass das Profil an einer geratenen Zeile scheitert.
"""
from __future__ import annotations

import glob
import os

from .base import GameProfile

# Kandidaten in absteigender Wahrscheinlichkeit; danach greift die Suche.
EXE_NAMES = ("StarRuptureServerEOS.exe", "StarRuptureServer.exe", "StarRuptureServer-Win64-Shipping.exe")
EXE_GLOBS = (
    "*.exe",
    os.path.join("Binaries", "Win64", "*.exe"),
    os.path.join("*", "Binaries", "Win64", "*.exe"),
    os.path.join("StarRupture", "Binaries", "Win64", "*.exe"),
)
CFG_NAME = "DSSettings.txt"


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


class StarRuptureProfile(GameProfile):
    key = "starrupture"
    label = "StarRupture (Dedicated Server)"
    server_app_id = "3809400"

    needs_wine = True
    has_control = False              # kein RCON/API
    supports_mods = False
    supports_cluster = False
    supports_whitelist = False
    use_pty = True

    default_game_port = 7777
    default_query_port = 7778
    default_control_port = 0         # kein Steuerkanal
    default_max_players = 8

    install_note = ("Windows-Server unter Wine/Proton. Die Welt wird im Spiel ueber "
                    "\"Manage Server\" erstellt oder geladen; Konfiguration in DSSettings.txt.")

    settings_fields = (
        ("session_name", "Server-Name", "Name der Sitzung in der Serverliste", "text"),
        ("max_players", "Max. Spieler", "Vanilla-Grenze liegt bei 8", "int"),
        ("port", "Spielport (UDP)", "Standard 7777", "int"),
    )

    # ----------------------------------------------------------------- Pfade
    def _exe_kandidaten(self, inst) -> list[str]:
        out = [os.path.join(inst.directory, n) for n in EXE_NAMES]
        for muster in EXE_GLOBS:
            out.extend(sorted(glob.glob(os.path.join(inst.directory, muster))))
        return out

    def exe(self, inst) -> str:
        for pfad in self._exe_kandidaten(inst):
            name = os.path.basename(pfad).lower()
            if name in ("starruptureserver.exe", "starruptureservereos.exe") \
                    or name.startswith("starruptureserver"):
                return pfad
        # nichts Passendes gefunden: ersten Kandidaten nennen, damit die
        # Oberflaeche einen Pfad zeigt statt einer leeren Zeile
        kand = [p for p in self._exe_kandidaten(inst) if os.path.exists(p)]
        return kand[0] if kand else os.path.join(inst.directory, EXE_NAMES[0])

    def workdir(self, inst) -> str:
        exe = self.exe(inst)
        return os.path.dirname(exe) if exe else inst.directory

    def config_path(self, inst) -> str:
        """DSSettings.txt liegt neben der Startdatei."""
        return os.path.join(self.workdir(inst), CFG_NAME)

    def log_path(self, inst) -> str:
        for muster in ("Saved/Logs/*.log", "Logs/*.log", "*.log"):
            treffer = sorted(glob.glob(os.path.join(inst.directory, muster)))
            if treffer:
                return treffer[-1]
        return os.path.join(inst.directory, "StarRuptureServer.log")

    # ------------------------------------------------------------ Startzeile
    def launch_argv(self, inst) -> list[str]:
        # Bewusst minimal: nur -log. Weitere Flags sind nicht offiziell belegt und
        # koennen den Server am Start hindern; Name/Menge/Port stehen in DSSettings.txt.
        return [self.exe(inst), "-log"]

    # ---------------------------------------------------------- Konfigdatei
    def write_config(self, inst) -> None:
        """DSSettings.txt schreiben (Name, Port, Spielerzahl, Passwort wenn gesetzt)."""
        pfad = self.config_path(inst)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        werte = [("ServerName", getattr(inst, "session_name", "") or inst.name),
                 ("Port", str(getattr(inst, "port", self.default_game_port))),
                 ("MaxPlayers", str(getattr(inst, "max_players", self.default_max_players)))]
        if getattr(inst, "server_password", ""):
            werte.append(("Password", inst.server_password))
        alt = {}
        if os.path.exists(pfad):
            try:
                for zeile in open(pfad, encoding="utf-8", errors="replace"):
                    if "=" in zeile and not zeile.strip().startswith(("#", ";")):
                        k, _, v = zeile.partition("=")
                        alt[k.strip()] = v.strip()
            except OSError:
                alt = {}
        for k, v in werte:
            alt[k] = v
        inhalt = "\n".join("%s=%s" % (k, alt[k]) for k in sorted(alt)) + "\n"
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(inhalt)

    # ---------------------------------------------------------- Steuerkanal
    def ready(self, inst) -> bool:
        """Bereit = der UDP-Spielport ist belegt (kein Handshake verfuegbar)."""
        return _udp_port_bound(int(getattr(inst, "port", self.default_game_port)))

    def players(self, inst):
        """Ohne Steuerkanal gibt es keine belastbare Spielerliste."""
        return None
