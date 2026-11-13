"""Spielerlisten der verschiedenen Spiele auswerten.

ARK (RCON `ListPlayers`) liefert `0. Name, 7656119..., ...`, 7 Days to Die (Telnet `lp`) liefert
`0. id=171, Name, pos=(...), remote=..., pltfmid=7656119..., crossid=eos_..., ip=..., ping=...`.
Beides landet in derselben Struktur: id, name, steamid.
"""
import re

# ARK: "0. Name, 76561198..., ..." (Steam-ID als zweites Feld, Zeile endet dort)
_ARK = re.compile(r"^\s*(\d+)\.\s*([^,]+),\s*([0-9A-Za-z]{15,32})")
# 7D2D: "0. id=171, Name, pos=(x, y, z), remote=..., pltfmid=..., crossid=..."
_SDTD = re.compile(r"^\s*(\d+)[.,]\s+id=([^,]*),\s*([^,]*)")
_PLAT = re.compile(r"pltfmid=([^,\s]+)")
_CROSS = re.compile(r"crossid=([^,\s]+)")


def parse(out: str) -> list[dict[str, str]]:
    """Zeilen einer Spielerausgabe in {id, name, steamid} umsetzen."""
    found: list[dict[str, str]] = []
    for line in (out or "").splitlines():
        m = _ARK.match(line)
        if m:
            found.append({"id": m.group(1), "name": m.group(2).strip(), "steamid": m.group(3)})
            continue
        m = _SDTD.match(line)
        if m:
            plat = _PLAT.search(line)
            cross = _CROSS.search(line)
            kennung = (plat.group(1) if plat else "") or (cross.group(1) if cross else "")
            found.append({"id": m.group(2).strip(), "name": m.group(3).strip(), "steamid": kennung})
    return found
