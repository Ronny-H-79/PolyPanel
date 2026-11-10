"""Discord-Benachrichtigungen fuer noah2games.

Alle Meldungen laufen ueber den Webhook der Instanz (`webhook_url`). Ist keiner
gesetzt, wird nur ins lokale Log geschrieben - nie eine Ausnahme nach aussen.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request

COLORS = {
    "crash": 0xE74C3C,      # rot
    "hang": 0xE67E22,       # orange
    "update": 0x3498DB,     # blau
    "backup": 0x2ECC71,     # gruen
    "info": 0x95A5A6,       # grau
}


def log_path(inst) -> str:
    return os.path.join(inst.directory, ".noah2games-notify.log")


def _write_log(inst, line: str) -> None:
    try:
        with open(log_path(inst), "a", encoding="utf-8") as fh:
            fh.write("%s  %s\n" % (time.strftime("%F %T"), line))
    except OSError:
        pass


def _payload(inst, title: str, text: str, kind: str = "info", fields=None) -> dict:
    embed = {
        "title": title[:250],
        "description": (text or "")[:1800],
        "color": COLORS.get(kind, COLORS["info"]),
        "footer": {"text": "noah2games · %s" % inst.name},
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    if fields:
        embed["fields"] = [
            {"name": str(k)[:100], "value": str(v)[:1000], "inline": True}
            for k, v in list(fields.items())[:8]
        ]
    return {"username": "noah2games", "embeds": [embed]}


def _post(url: str, data: bytes, timeout: int = 10) -> None:
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json", "User-Agent": "noah2games"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        resp.read()


def send(inst, title: str, text: str = "", kind: str = "info", fields=None) -> bool:
    """Meldung senden. Blockiert nicht (eigener Thread), Fehler nur ins Log."""
    _write_log(inst, "%s: %s" % (title, text))

    def run() -> None:
        url = getattr(inst, "webhook_url", "") or ""
        if not url:
            return
        try:
            _post(url, json.dumps(_payload(inst, title, text, kind, fields)).encode())
        except Exception as exc:  # noqa: BLE001 - darf nie stoppen
            _write_log(inst, "webhook fehlgeschlagen: %s: %s" % (exc.__class__.__name__, exc))

    threading.Thread(target=run, daemon=True).start()
    return True


def test(inst, url: str = "") -> dict:
    """Webhook sofort pruefen (synchron, fuer den Test-Knopf in der Oberflaeche)."""
    target = url or getattr(inst, "webhook_url", "") or ""
    if not target:
        return {"ok": False, "error": "kein Webhook gesetzt"}
    try:
        _post(target, json.dumps(_payload(
            inst, "Test von noah2games", "Wenn du das liest, stimmt der Webhook.", "update",
            {"Instanz": inst.name},
        )).encode())
        return {"ok": True}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": "%s: %s" % (exc.__class__.__name__, exc)}
