"""Fehlermeldungen aus der Oberflaeche an einen Discord-Webhook.

Der Melde-Webhook ist eine Einstellung des **Panels** (``settings.json``), nicht der
Instanz - eine Adresse fuer alle Server. In der Meldung stehen Version, Instanz,
Karte, Betriebssystem, Python und ein Auszug aus dem Serverlog; Passwoerter und
Tokens werden vorher entfernt.
"""
from __future__ import annotations

import json
import os
import platform
import re
import sys
import time
import urllib.error
import urllib.request

from . import __version__
from .instance import Instance
from .paths import SETTINGS_PATH

TIMEOUT = 12
MAX_TEXT = 1500
MAX_LOG_LINES = 30
MAX_LOG_CHARS = 900          # Discord erlaubt 1024 Zeichen je Feldwert

# Zeilen und Fragmente, die nie mitgeschickt werden
_GEHEIM = re.compile(
    r"(password|passwort|rcon_password|admin_password|token|secret|apikey|api_key)",
    re.I,
)
_MUSTER = [
    (re.compile(r"(\?|\&|/)(ServerAdminPassword|ServerPassword|RCONPassword|SessionId)=[^&\s\"]*", re.I), r"\1\2=[entfernt]"),
    (re.compile(r'("?(?:password|passwort|token|secret)"?\s*[:=]\s*)"?[^"\s,}]*', re.I), r"\1[entfernt]"),
]


# ------------------------------------------------------------------ Einstellungen
def _lesen() -> dict:
    try:
        with open(SETTINGS_PATH, encoding="utf-8") as fh:
            daten = json.load(fh)
        return daten if isinstance(daten, dict) else {}
    except (OSError, ValueError):
        return {}


def _schreiben(daten: dict) -> None:
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    tmp = SETTINGS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(daten, fh, ensure_ascii=False, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, SETTINGS_PATH)


def webhook() -> str:
    return str(_lesen().get("report_webhook", "") or "")


def set_webhook(url: str) -> None:
    daten = _lesen()
    if url:
        daten["report_webhook"] = url.strip()
    else:
        daten.pop("report_webhook", None)
    _schreiben(daten)


def _saeubern(text: str) -> str:
    for muster, ersatz in _MUSTER:
        text = muster.sub(ersatz, text)
    return text


def logauszug(inst, zeilen: int = MAX_LOG_LINES) -> str:
    """Letzte Logzeilen, ohne Passwoerter/Token, gekuerzt auf MAX_LOG_CHARS."""
    pfad = inst.log_path
    try:
        with open(pfad, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            groesse = fh.tell()
            fh.seek(max(0, groesse - 64_000))
            roh = fh.read().decode("utf-8", "replace")
    except OSError:
        return ""
    brauchbar = [z for z in roh.splitlines() if z.strip() and not _GEHEIM.search(z)]
    auszug = "\n".join(brauchbar[-zeilen:])
    return _saeubern(auszug)[-MAX_LOG_CHARS:]


# ------------------------------------------------------------------ Senden
def _felder(inst) -> list[dict]:
    karte = getattr(inst, "map", "") or ""
    return [
        {"name": "Panel", "value": "PolyPanel %s" % __version__, "inline": True},
        {"name": "Instanz", "value": "%s (%s)" % (getattr(inst, "name", "?"), karte), "inline": True},
        {"name": "System", "value": "%s · Python %s" % (platform.platform(terse=True),
                                                        sys.version.split()[0]), "inline": False},
    ]


def senden(inst, text: str, schritte: str = "") -> dict:
    """Meldung abschicken. Gibt {"ok": bool, "fehler": str} zurueck."""
    text = (text or "").strip()
    if not text:
        return {"ok": False, "fehler": "leere Meldung"}
    url = webhook()
    if not url:
        return {"ok": False, "fehler": "kein Melde-Webhook gesetzt"}

    beschreibung = _saeubern(text)[:MAX_TEXT]
    felder = _felder(inst)
    if schritte.strip():
        felder.append({"name": "Schritte", "value": _saeubern(schritte.strip())[:900], "inline": False})
    auszug = logauszug(inst)
    if auszug:
        felder.append({"name": "Log (Ende)", "value": "```\n%s\n```" % auszug[:990], "inline": False})

    daten = {
        "username": "PolyPanel",
        "content": "**Fehlermeldung aus dem Panel**",
        "embeds": [{
            "title": "Meldung von einem Nutzer",
            "description": beschreibung,
            "color": 0xE74C3C,
            "fields": felder[:8],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "footer": {"text": "%s · %s" % (getattr(inst, "name", "?"), __version__)},
        }],
    }
    anfrage = urllib.request.Request(
        url, data=json.dumps(daten).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "PolyPanel/%s" % __version__},
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=TIMEOUT) as antwort:
            antwort.read()
    except urllib.error.HTTPError as exc:
        try:
            antwort = exc.read().decode("utf-8", "replace")[:300]
        except Exception:                       # noqa: BLE001
            antwort = ""
        return {"ok": False, "fehler": "HTTP %s vom Webhook %s" % (exc.code, antwort)}
    except Exception as exc:                     # noqa: BLE001 - nie nach aussen werfen
        return {"ok": False, "fehler": "%s: %s" % (exc.__class__.__name__, exc)}
    return {"ok": True, "fehler": ""}


def test(inst) -> dict:
    return senden(inst, "Testmeldung aus dem Panel - wenn du das liest, ist der Melde-Webhook in Ordnung.")
