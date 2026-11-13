#!/usr/bin/env python3
"""Weiterleitung fuer Panel-Fehlermeldungen.

Das Panel schickt seine Meldung an DIESEN Dienst (oeffentliche Adresse des Betreibers),
der Dienst reicht sie an die Discord-Webhook-Adresse weiter. Damit steht die
Discord-Adresse nur hier auf dem Server und nie im Panel-Repo.

Nur Standardbibliothek. Aufruf:  python3 report-relay.py [--config /etc/report-relay.conf]

Konfiguration (KEY=WERT, # als Kommentar):
    DISCORD_URL=https://discord.com/api/webhooks/...
    PATH_KEY=<zufaelliger Schluessel, Teil der Adresse>
    LISTEN=127.0.0.1
    PORT=8787
    RATE_PER_IP=10          # Meldungen je IP und Stunde
    RATE_TOTAL=120          # Meldungen insgesamt je Stunde
    MAX_BYTES=65536
"""
from __future__ import annotations

import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULTS = {
    "DISCORD_URL": "",
    "PATH_KEY": "",
    "LISTEN": "127.0.0.1",
    "PORT": "8787",
    "RATE_PER_IP": "10",
    "RATE_TOTAL": "120",
    "MAX_BYTES": "65536",
    "TIMEOUT": "12",
}
CONF = dict(DEFAULTS)


def lade_config(pfad: str) -> dict:
    daten = dict(DEFAULTS)
    try:
        with open(pfad, encoding="utf-8") as fh:
            for zeile in fh:
                zeile = zeile.strip()
                if not zeile or zeile.startswith("#") or "=" not in zeile:
                    continue
                schluessel, wert = zeile.split("=", 1)
                daten[schluessel.strip()] = wert.strip().strip('"').strip("'")
    except OSError as exc:
        sys.exit("Konfiguration nicht lesbar (%s): %s" % (pfad, exc))
    return daten


class Begrenzer:
    """Einfache Gleitfenster-Begrenzung je IP und insgesamt."""

    def __init__(self, pro_ip: int, gesamt: int, fenster: int = 3600) -> None:
        self.pro_ip = pro_ip
        self.gesamt = gesamt
        self.fenster = fenster
        self.je_ip: dict[str, list[float]] = defaultdict(list)
        self.alle: list[float] = []

    def erlaubt(self, ip: str) -> bool:
        jetzt = time.time()
        self.alle = [t for t in self.alle if jetzt - t < self.fenster]
        eig = [t for t in self.je_ip[ip] if jetzt - t < self.fenster]
        self.je_ip[ip] = eig
        if len(self.alle) >= self.gesamt or len(eig) >= self.pro_ip:
            return False
        self.alle.append(jetzt)
        eig.append(jetzt)
        return True


class Weiterleitung(BaseHTTPRequestHandler):
    server_version = "ReportRelay/1.0"
    sys_version = ""
    begrenzer: Begrenzer = None          # type: ignore[assignment]

    # ------------------------------------------------------------------ Hilfen
    def log_message(self, format: str, *args) -> None:   # noqa: A002,A003
        sys.stdout.write("%s  %s  %s\n" % (time.strftime("%F %T"), self.client_address[0],
                                            format % args))
        sys.stdout.flush()

    def _antwort(self, code: int, daten: dict) -> None:
        blob = json.dumps(daten, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(blob)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(blob)

    # ------------------------------------------------------------------ Routen
    def do_GET(self) -> None:                            # noqa: N802
        if self.path.split("?")[0] in ("/health", "/healthz"):
            self._antwort(200, {"ok": True})
            return
        self._antwort(404, {"ok": False, "fehler": "unbekannter Pfad"})

    def do_POST(self) -> None:                           # noqa: N802
        pfad = self.path.split("?")[0].rstrip("/")
        schluessel = CONF.get("PATH_KEY", "")
        if not schluessel or not hmac.compare_digest(pfad, "/report/" + schluessel):
            self._antwort(404, {"ok": False, "fehler": "unbekannter Pfad"})
            return
        try:
            laenge = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            laenge = 0
        if laenge <= 0 or laenge > int(CONF["MAX_BYTES"]):
            self._antwort(413, {"ok": False, "fehler": "Meldung zu gross oder leer"})
            return
        roh = self.rfile.read(laenge)
        try:
            daten = json.loads(roh.decode("utf-8", "replace"))
        except ValueError:
            self._antwort(400, {"ok": False, "fehler": "kein JSON"})
            return
        if not isinstance(daten, dict):
            self._antwort(400, {"ok": False, "fehler": "JSON-Objekt erwartet"})
            return
        # Nur weiterleiten, was Discord kennt - kein Freifeld fuer Fremde
        erlaubt = {k: daten[k] for k in ("content", "embeds", "username", "avatar_url")
                   if k in daten}
        if not erlaubt.get("content") and not erlaubt.get("embeds"):
            self._antwort(400, {"ok": False, "fehler": "leere Meldung"})
            return
        # erst jetzt zaehlen: ungueltige Anfragen sollen kein Kontingent verbrauchen
        if not self.begrenzer.erlaubt(self.client_address[0]):
            self._antwort(429, {"ok": False, "fehler": "zu viele Meldungen - bitte spaeter"})
            return
        ziel = CONF["DISCORD_URL"]
        if not ziel:
            self._antwort(500, {"ok": False, "fehler": "DISCORD_URL fehlt in der Konfiguration"})
            return
        anfrage = urllib.request.Request(
            ziel, data=json.dumps(erlaubt, ensure_ascii=False).encode(),
            headers={"Content-Type": "application/json", "User-Agent": "ReportRelay/1.0"},
        )
        try:
            with urllib.request.urlopen(anfrage, timeout=float(CONF["TIMEOUT"])) as antwort:
                antwort.read()
        except urllib.error.HTTPError as exc:
            text = ""
            try:
                text = exc.read().decode("utf-8", "replace")[:200]
            except Exception:                            # noqa: BLE001
                pass
            self._antwort(502, {"ok": False, "fehler": "Discord: HTTP %s %s" % (exc.code, text)})
            return
        except Exception as exc:                         # noqa: BLE001
            self._antwort(502, {"ok": False, "fehler": "Weiterleitung fehlgeschlagen: %s"
                                % exc.__class__.__name__})
            return
        self._antwort(200, {"ok": True})


def main(argv: list[str]) -> None:
    pfad = "/etc/report-relay.conf"
    if "--config" in argv:
        pfad = argv[argv.index("--config") + 1]
    CONF.update(lade_config(pfad))
    if not CONF["PATH_KEY"]:
        sys.exit("PATH_KEY fehlt in %s - ohne Schluessel nimmt der Dienst nichts an." % pfad)
    ziel = CONF["DISCORD_URL"]
    lokal = ziel.startswith(("http://127.0.0.1", "http://localhost"))
    if not (ziel.startswith("https://") or lokal):
        sys.exit("DISCORD_URL fehlt oder ist keine https-Adresse (%s)." % pfad)
    Weiterleitung.begrenzer = Begrenzer(int(CONF["RATE_PER_IP"]), int(CONF["RATE_TOTAL"]))
    adresse = (CONF["LISTEN"], int(CONF["PORT"]))
    server = ThreadingHTTPServer(adresse, Weiterleitung)
    print("Report-Relay auf %s:%s, Pfad /report/<key>, %s Meldungen/Stunde je IP"
          % (adresse[0], adresse[1], CONF["RATE_PER_IP"]), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("beendet", flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
