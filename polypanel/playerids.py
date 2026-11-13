"""Dauerhafte Spieler-IDs (ARKID) einer Instanz ermitteln.

Warum: `GiveItemToPlayer` braucht die **dauerhafte Spieler-ID** (ARKID, z. B. 840709058) —
nicht die EOS-/Steam-ID aus `ListPlayers` (00023634c152…). Mit der falschen ID meldet RCON
trotzdem „ok", im Inventar landet aber nichts.

Quellen, in dieser Reihenfolge:
1. **`.arkprofile`-Dateien** (`Saved/SavedArks/<Map>/<EOS-ID>.arkprofile`, aeltere Ableger auch
   unter `Saved/SaveGames/…`). Der Dateiname ist die EOS-ID, im Inhalt steht die Property
   `PlayerDataID` (UInt64) = ARKID und `PlayerName`.
2. **Server-Log** (`ShooterGame.log`): Zeilen wie
   `AdminCmd: fly (PlayerName: sorbid79, ARKID: 840709058, PlatformID: 00023634…)`.
3. `PlayerCache.sav` / `AwesomeAdminTools/Logs.sav` (aeltere Server-Variante).
"""

import glob
import os
import re
import struct
import subprocess
import threading
import time
from typing import Any

_CACHE: dict[str, tuple[float, dict[str, str]]] = {}
_LOCK = threading.Lock()
_TTL = 120.0


# ------------------------------------------------------------------ Hilfsmittel
def _strings(pfad: str, minimum: int = 4) -> list[str]:
    """Textzeilen aus einer Binaerdatei - ohne Abhaengigkeit von `strings`."""
    try:
        with open(pfad, "rb") as fh:
            roh = fh.read()
    except OSError:
        return []
    treffer = [m.group().decode("ascii", "ignore")
               for m in re.finditer(rb"[\x20-\x7e]{%d,}" % minimum, roh)]
    if treffer:
        return treffer
    try:
        return subprocess.run(["strings", "-n", str(minimum), pfad],
                              capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return []


def _arkid_aus_profil(pfad: str) -> int:
    """Liest die Property `PlayerDataID` (UInt64) aus einer .arkprofile."""
    try:
        with open(pfad, "rb") as fh:
            roh = fh.read()
    except OSError:
        return 0

    i_name = roh.find(b"PlayerDataID")
    i_type = roh.find(b"UInt64Property", i_name if i_name >= 0 else 0)
    if i_name < 0 or i_type < 0:
        return 0

    pos = i_type + len(b"UInt64Property") + 1          # Ende des Typnamens
    if pos + 13 > len(roh):
        return 0
    size = struct.unpack_from("<i", roh, pos + 4)[0]
    mit_guid = roh[pos + 8]
    wert_pos = pos + 9 + (16 if mit_guid else 0)
    if size not in (4, 8) or wert_pos + 8 > len(roh):
        return 0
    wert = struct.unpack_from("<Q", roh, wert_pos)[0]
    return wert if 1_000_000 <= wert <= 5_000_000_000 else 0


def _name_aus_profil(pfad: str) -> str:
    """Spielername aus der .arkprofile (Property PlayerName)."""
    try:
        with open(pfad, "rb") as fh:
            roh = fh.read()
    except OSError:
        return ""
    i = roh.find(b"PlayerName")
    if i < 0:
        return ""
    rest = roh[i + len(b"PlayerName") + 1:i + 160]
    # zwischen Property-Name und Wert steht der Typname "StrProperty"
    j = rest.find(b"StrProperty")
    if j < 0:
        return ""
    p = j + len(b"StrProperty") + 1
    if p + 12 > len(rest):
        return ""
    size = struct.unpack_from("<i", rest, p + 4)[0]
    if not (0 < size < 120):
        return ""
    name = rest[p + 9:p + 9 + size].split(b"\x00")[0].decode("utf-8", "ignore")
    # Nur brauchbare Namen durchlassen (keine Steuerzeichen, 2-40 Zeichen)
    if not (2 <= len(name) <= 40) or any(ord(c) < 32 for c in name):
        return ""
    return name


# ------------------------------------------------------------------ Quellen
def _aus_profilen(inst: Any) -> dict[str, str]:
    mapping: dict[str, str] = {}
    basis = getattr(inst, "directory", "") or ""
    if not basis or not os.path.isdir(basis):
        return mapping
    muster = [
        os.path.join(basis, "**", "SavedArks", "*", "*.arkprofile"),
        os.path.join(basis, "**", "SaveGames", "**", "*.arkprofile"),
    ]
    gesehen = set()
    for form in muster:
        for pfad in glob.glob(form, recursive=True):
            if pfad in gesehen:
                continue
            gesehen.add(pfad)
            eos = os.path.basename(pfad).split(".", 1)[0].lower()
            wert = _arkid_aus_profil(pfad)
            if not wert:
                continue
            kennung = str(wert)
            mapping[eos] = kennung
            name = _name_aus_profil(pfad)
            if name:
                mapping.setdefault(name, kennung)
    return mapping


def _aus_log(inst: Any) -> dict[str, str]:
    mapping: dict[str, str] = {}
    basis = getattr(inst, "directory", "") or ""
    if not basis or not os.path.isdir(basis):
        return mapping
    for pfad in glob.glob(os.path.join(basis, "**", "Logs", "ShooterGame*.log"), recursive=True):
        for zeile in _strings(pfad, 20):
            m = re.search(r"\(PlayerName: ([^,]+), ARKID: (\d+), PlatformID: ([0-9a-zA-Z]+)\)", zeile)
            if m:
                name, arkid, plattform = m.group(1).strip(), m.group(2), m.group(3).lower()
                mapping[plattform] = arkid
                mapping.setdefault(name, arkid)
    return mapping


def _aus_saves(inst: Any) -> dict[str, str]:
    """Alte Variante: PlayerCache.sav und AwesomeAdminTools/Logs.sav."""
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
                    mapping[eos] = pid
                    if pname:
                        mapping.setdefault(pname, pid)
                pid = pname = eos = None
    return mapping


# ------------------------------------------------------------------ oeffentlich
def karte(inst: Any, neu_laden: bool = False) -> dict[str, str]:
    schluessel = getattr(inst, "name", "") or ""
    with _LOCK:
        eintrag = _CACHE.get(schluessel)
        if not neu_laden and eintrag and time.time() - eintrag[0] < _TTL:
            return eintrag[1]

    mapping: dict[str, str] = {}
    for quelle in (_aus_profilen, _aus_log, _aus_saves):
        try:
            for schluessel_name, wert in quelle(inst).items():
                mapping.setdefault(schluessel_name, wert)
        except Exception:                     # noqa: BLE001 - eine Quelle darf ausfallen
            continue

    with _LOCK:
        _CACHE[schluessel] = (time.time(), mapping)
    return mapping


def aufloesen(inst: Any, eos: str = "", name: str = "") -> str:
    """Liefert die ARKID zu EOS-ID oder Name; leer, wenn unbekannt."""
    for neu in (False, True):
        mapping = karte(inst, neu_laden=neu)
        if eos and (eos.lower() in mapping or eos in mapping):
            return mapping.get(eos.lower()) or mapping.get(eos, "")
        if name and name in mapping:
            return mapping[name]
    return ""


def pfade(inst: Any) -> dict:
    basis = getattr(inst, "directory", "") or ""
    ergebnis = {"basis": basis, "existiert": False, "oben": [], "profile": [],
                "id_karte": 0, "sav_dateien": []}
    if not basis or not os.path.isdir(basis):
        return ergebnis
    ergebnis["existiert"] = True
    try:
        ergebnis["oben"] = sorted(os.listdir(basis))[:20]
    except OSError:
        pass
    ergebnis["profile"] = glob.glob(os.path.join(basis, "**", "*.arkprofile"), recursive=True)[:20]
    ergebnis["sav_dateien"] = glob.glob(os.path.join(basis, "**", "*.sav"), recursive=True)[:20]
    ergebnis["id_karte"] = len(karte(inst, neu_laden=True))
    return ergebnis


def diagnose(inst: Any) -> str:
    d = pfade(inst)
    return ("Profile: %d, .sav: %d, zugeordnete Spieler: %d"
            % (len(d["profile"]), len(d["sav_dateien"]), d["id_karte"]))
