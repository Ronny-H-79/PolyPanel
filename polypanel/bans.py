"""Eigene Liste gesperrter Spieler je Instanz.

ARK liefert die Ban-Liste nicht ueber RCON (`ListBannedPlayers` antwortet mit
"Server received, But no response", `GetBanList` ebenso). Damit man trotzdem eine Liste
mit Entbannen-Knoepfen hat, merkt sich das Panel selbst, wen es gebannt hat:
EOS-ID, Name (falls bekannt) und Zeitpunkt. Die Datei liegt neben der Instanz.

Wichtig: Das ist eine **Panel-eigene** Liste. Wer ausserhalb des Panels bannt (Konsole,
anderes Tool), taucht hier nicht auf - dafuer bleibt das Feld "Entbannen" mit EOS-ID.
"""

import json
import os
import time
from typing import Any

DATEI = "bans.json"


def _pfad(inst: Any) -> str:
    return os.path.join(inst.directory, DATEI)


def laden(inst: Any) -> list[dict]:
    try:
        with open(_pfad(inst), encoding="utf-8") as fh:
            daten = json.load(fh)
        if isinstance(daten, list):
            return [d for d in daten if isinstance(d, dict) and d.get("eos")]
    except (OSError, ValueError):
        pass
    return []


def _speichern(inst: Any, eintraege: list[dict]) -> None:
    pfad = _pfad(inst)
    tmp = pfad + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(eintraege, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, pfad)


def merken(inst: Any, eos: str, name: str = "") -> None:
    eos = (eos or "").strip()
    if not eos:
        return
    eintraege = [e for e in laden(inst) if e.get("eos") != eos]
    eintraege.append({
        "eos": eos,
        "name": (name or "").strip(),
        "zeit": time.strftime("%Y-%m-%d %H:%M"),
    })
    _speichern(inst, eintraege)


def vergessen(inst: Any, eos: str) -> None:
    eos = (eos or "").strip()
    _speichern(inst, [e for e in laden(inst) if e.get("eos") != eos])
