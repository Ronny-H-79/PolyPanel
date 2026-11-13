"""Spielprofile - alles, was ein Spiel vom gemeinsamen Kern unterscheidet.

Der Kern (Prozessverwaltung, Backups, Web-UI, Zeitplan, Mehrinstanzen) bleibt
spielunabhaengig. Ein Profil liefert genau das, was spielspezifisch ist:
Startzeile, Konfigurationsdatei, Pfade und den Steuerkanal.

Die Felder sind Klassenattribute, damit Unterklassen sie einfach ueberschreiben
(`key`, `label`, `server_app_id`, ...); Instanzen brauchen keine Argumente.
"""
from __future__ import annotations

import os

try:
    from ..control import ControlError
except ImportError:      # pragma: no cover
    class ControlError(RuntimeError):
        pass
import socket


def _tcp_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class NullControl:
    """Platzhalter fuer Spiele ohne RCON/API: Status ja, Befehle nein."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def execute(self, command: str, timeout: float = 8.0) -> str:
        raise ControlError("Dieses Spiel hat keinen Steuerkanal (kein RCON/API)")

    command = execute


class GameProfile:
    key: str = ""                          # Kurzname in der Instanz-Config
    label: str = ""                        # Anzeigename im UI
    server_app_id: str = ""                # Steam-App-ID des Dedicated Servers
    control_kind: str = "source"           # source | telnet | https | none
    needs_wine: bool = False
    refuses_root: bool = False   # True = Server startet nicht als root (z. B. Satisfactory)
    default_game_port: int = 7777
    default_query_port: int = 27016
    default_control_port: int = 27025
    supports_mods: bool = False
    has_control: bool = True       # False = kein RCON/API vorhanden
    use_pty: bool = True          # False = direkt starten (kein PTY), z. B. .NET-Server
    wine_overrides: str = ""      # z. B. "mscoree,mshtml=" (deaktiviert .NET!)
    needs_display: bool = False   # True = DISPLAY/WAYLAND nicht entfernen
    supports_cluster: bool = False
    install_note: str = ""
    maps: tuple = ()              # ((Wert, Anzeigename), ...) - leer = keine Kartenauswahl

    # Einstellungen, die im Reiter "Einstellungen" erscheinen:
    # (Instanz-Attribut, Label, Hinweis, Typ)
    settings_fields: tuple = ()

    def settings(self, inst) -> list[dict]:
        """Nur die Einstellungen, die dieses Spiel wirklich hat."""
        out = []
        for attr, label, hint, typ in self.settings_fields:
            out.append({"file": "instance", "section": "", "key": attr, "label": label,
                        "hint": hint, "type": typ, "value": str(getattr(inst, attr, "")),
                        "group": "srv"})
        return out

    def apply_settings(self, inst, items) -> int:
        """Werte aus dem Formular uebernehmen; nur erlaubte Felder dieses Spiels."""
        allowed = {f[0] for f in self.settings_fields}
        changed = 0
        for item in items:
            key = item.get("key")
            if key not in allowed:
                continue
            val = item.get("value", "")
            cur = getattr(inst, key, "")
            if isinstance(cur, int):
                try:
                    val = int(str(val).strip())
                except (TypeError, ValueError):
                    continue
            setattr(inst, key, val)
            changed += 1
        return changed

    # ------------------------------------------------------------ Wine/Prefix
    def wine_prefix(self, inst) -> str:
        """Wine-Prefix fuer dieses Spiel ('' = Standard des Benutzers)."""
        return os.path.expanduser(inst.wine_prefix) if getattr(inst, "wine_prefix", "") else ""

    def mods_search(self, inst, query: str) -> dict:
        """Mod-Suche; {} = kein Anbieter vorhanden."""
        return {}

    def mods_install(self, inst, mod_id: str, log=print) -> str:
        raise ControlError("Für dieses Spiel gibt es keine automatische Mod-Installation")

    def mods_path(self, inst) -> str:
        """Ordner mit lokalen Mods ('' = keine Mod-Unterstuetzung)."""
        return ""

    def workshop_ids(self, inst) -> list[str]:
        """Eingetragene Workshop-IDs (nur Spiele, deren Mods Workshop-IDs sind)."""
        return []

    def workdir(self, inst) -> str:
        """Arbeitsverzeichnis beim Start (Standard: Instanzordner)."""
        return inst.directory

    def runtime_ready(self, inst) -> bool:
        """Sind die Laufzeit-Voraussetzungen erfuellt? (nativ: immer)"""
        return True

    def post_install(self, inst, log=print) -> None:
        """Wird nach einer SteamCMD-Installation aufgerufen (optional)."""
        return None

    # ---------------------------------------------------------------- Pfade
    def exe(self, inst) -> str:
        raise NotImplementedError

    def installed(self, inst) -> bool:
        return os.path.exists(self.exe(inst))

    # ------------------------------------------------------------ Startzeile
    def launch_argv(self, inst) -> list[str]:
        raise NotImplementedError

    # ---------------------------------------------------------- Konfigdatei
    def write_config(self, inst) -> None:
        raise NotImplementedError

    # ---------------------------------------------------------- Steuerkanal
    def players(self, inst) -> list[str] | None:
        """Spielerliste, wenn das Spiel eine eigene Abfrage braucht (None = ListPlayers)."""
        return None

    def control(self, inst, timeout: float = 10.0):
        if not self.has_control:
            return NullControl()
        raise NotImplementedError

    def ready(self, inst) -> bool:
        """Laeuft der Server schon? Vorgabe: Spielport ist offen (UDP)."""
        import socket as _socket
        try:
            s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
            s.settimeout(1.0)
            # UDP kennt kein connect-Handshake: ein belegter Port laesst sich nur
            # ueber einen Test-Datagrammversuch pruefen, deshalb hier TCP-Fallback.
            s.close()
        except OSError:
            pass
        return _tcp_open("127.0.0.1", inst.port)

    def graceful_stop(self, inst) -> list[str]:
        """Sauber herunterfahren ueber den Steuerkanal; Rueckgabe = Logzeilen.

        Vorgabe: nichts (der Prozess wird danach per Signal beendet).
        """
        return []
