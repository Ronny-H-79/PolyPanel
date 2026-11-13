"""Dauerhafte Spieler-IDs einer Instanz ermitteln.

Warum das nötig ist: `GiveItemToPlayer` erwartet die **dauerhafte** Spieler-ID (eine Zahl wie
761591001), nicht die EOS-/Steam-ID aus `ListPlayers` (`00023634c152…`). Mit der falschen ID
meldet RCON trotzdem „ok", im Inventar landet aber nichts.

Quellen, beide auf der Platte der Instanz:
- `AwesomeAdminTools/Logs.sav` — Zeilen wie „… gave … for 237249734." (nur AAT-Nutzer)
- `PlayerCache.sav` — kennt alle Spieler; Aufbau je Eintrag:
  `PlayerID_x` → StrProperty → <id>, `PlayerName_y` → <name>, `EosName_z` → <Loginname>

Die Zuordnung gilt pro Server, deshalb wird nichts global gespeichert.
"""

import os
import re
import subprocess
import threading
import time
from typing import Any

_CACHE: dict[str, tuple[float, dict[str, str]]] = {}
_LOCK = threading.Lock()
_TTL = 120.0


def _strings(pfad: str, minimum: int) -> list[str]:
    """Textzeilen aus einer Binärdatei lesen - ohne Abhängigkeit von `strings`.

    UE-Saves speichern ihre Strings als UTF-16LE. Deshalb werden beide Kodierungen
    ausgelesen; `strings` (binutils) dient nur als Notnagel, falls es installiert ist.
    """
    try:
        with open(pfad, "rb") as fh:
            roh = fh.read()
    except OSError:
        return []

    treffer: list[str] = []
    # ASCII
    for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minimum, roh):
        treffer.append(m.group().decode("ascii", "ignore"))
    # UTF-16LE (jedes zweite Byte 0x00)
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){%d,}" % minimum, roh):
        treffer.append(m.group().decode("utf-16-le", "ignore"))

    if treffer:
        return treffer
    try:
        return subprocess.run(["strings", "-n", str(minimum), pfad],
                              capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return []


def _aus_saves(inst: Any) -> dict[str, str]:
    mapping: dict[str, str] = {}
    basis = getattr(inst, "directory", "") or ""
    if not basis or not os.path.isdir(basis):
        return mapping

    for dirpath, _dirs, files in os.walk(basis):
        if "Logs.sav" not in files or not dirpath.endswith("AwesomeAdminTools"):
            continue
        for line in _strings(os.path.join(dirpath, "Logs.sav"), 10):
            m = re.search(r"^UTC \d+/\d+/\d+, [^:]+:\d+ [AP]M: (.+?) "
                          r"(?:spawned|gave|added).*for (\d+)\.", line)
            if m:
                mapping[m.group(1).strip()] = m.group(2)

    for dirpath, _dirs, files in os.walk(basis):
        if "PlayerCache.sav" not in files:
            continue
        zeilen = _strings(os.path.join(dirpath, "PlayerCache.sav"), 4)
        pid = pname = eos = None
        for i, line in enumerate(zeilen):
            if line.startswith("PlayerID_"):
                pid = zeilen[i + 2].strip() if i + 2 < len(zeilen) else None
            elif line.startswith("PlayerName_"):
                pname = zeilen[i + 2].strip() if i + 2 < len(zeilen) else None
            elif line.startswith("EosName_"):
                eos = zeilen[i + 2].strip() if i + 2 < len(zeilen) else None
                if pid and eos:
                    mapping[eos] = pid              # Loginname -> dauerhafte ID
                    if pname:
                        mapping.setdefault(pname, pid)
                pid = pname = eos = None
    return mapping


def karte(inst: Any, neu_laden: bool = False) -> dict[str, str]:
    """Zuordnung Name/EOS -> dauerhafte ID (mit kurzem Zwischenspeicher)."""
    schluessel = getattr(inst, "name", "") or ""
    with _LOCK:
        eintrag = _CACHE.get(schluessel)
        if not neu_laden and eintrag and time.time() - eintrag[0] < _TTL:
            return eintrag[1]
    mapping = _aus_saves(inst)
    with _LOCK:
        _CACHE[schluessel] = (time.time(), mapping)
    return mapping


def aufloesen(inst: Any, eos: str = "", name: str = "") -> str:
    """Liefert die dauerhafte ID zu EOS-ID oder Name; leer, wenn unbekannt."""
    mapping = karte(inst)
    if eos and eos in mapping:
        return mapping[eos]
    if name and name in mapping:
        return mapping[name]
    # Zweiter Versuch mit frisch gelesenen Saves (Spieler war gerade neu auf dem Server)
    mapping = karte(inst, neu_laden=True)
    if eos and eos in mapping:
        return mapping[eos]
    if name and name in mapping:
        return mapping[name]
    return ""


def diagnose(inst: Any) -> str:
    """Kurze Auskunft fuer die Oberflaeche, wenn keine ID gefunden wurde."""
    basis = getattr(inst, "directory", "") or ""
    if not basis or not os.path.isdir(basis):
        return "Instanzordner nicht gefunden: %s" % (basis or "?")
    saves = []
    for dirpath, _dirs, files in os.walk(basis):
        for name in ("PlayerCache.sav", "Logs.sav"):
            if name in files:
                saves.append(name)
    anzahl = len(karte(inst, neu_laden=True))
    return "gefundene Speicherdateien: %d, zugeordnete Spieler: %d" % (len(saves), anzahl)
