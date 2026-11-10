"""Whitelist und Bans einer Instanz."""
from __future__ import annotations

import os
import re

from .instance import Instance
from . import registry

WL_NAME = "PlayersExclusiveJoinList.txt"


def wl_path(inst: Instance) -> str:
    return os.path.join(inst.directory, "ShooterGame", "Saved", WL_NAME)


def read_whitelist(inst: Instance) -> list[str]:
    try:
        with open(wl_path(inst), encoding="utf-8", errors="replace") as fh:
            return [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    except OSError:
        return []


def write_whitelist(inst: Instance, ids: list[str]) -> None:
    path = wl_path(inst)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    seen: list[str] = []
    for raw in ids:
        value = str(raw).strip()
        if value and value not in seen:
            seen.append(value)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Steam-/EOS-IDs, eine pro Zeile (PolyPanel)\n")
        for value in seen:
            fh.write(value + "\n")


def _valid_id(player_id: str) -> str:
    """Nur Steam64 (Ziffern) oder Hex-UniqueNetId - der Wert landet in einer Textdatei."""
    pid = str(player_id).strip()
    if not (re.fullmatch(r"[0-9]{6,20}", pid) or re.fullmatch(r"[0-9a-fA-F]{8,32}", pid)):
        raise ValueError("ungueltige Spieler-ID")
    return pid


def add_to_whitelist(inst: Instance, player_id: str) -> None:
    player_id = _valid_id(player_id)
    ids = read_whitelist(inst)
    if str(player_id) not in ids:
        ids.append(str(player_id))
    write_whitelist(inst, ids)


def remove_from_whitelist(inst: Instance, player_id: str) -> None:
    player_id = _valid_id(player_id)
    write_whitelist(inst, [i for i in read_whitelist(inst) if i != str(player_id)])


def set_enabled(inst: Instance, enabled: bool) -> None:
    inst.exclusive_join = bool(enabled)
    registry.save(inst)


def info(inst: Instance) -> dict:
    return {
        "enabled": getattr(inst, "exclusive_join", False),
        "players": read_whitelist(inst),
        "file": wl_path(inst),
        "exists": os.path.exists(wl_path(inst)),
    }


def bans(inst: Instance) -> list[str]:
    return list(getattr(inst, "banned", []) or [])


def record_ban(inst: Instance, player_id: str) -> None:
    current = bans(inst)
    if str(player_id) not in current:
        current.append(str(player_id))
    inst.banned = current  # type: ignore[attr-defined]
    registry.save(inst)


def forget_ban(inst: Instance, player_id: str) -> None:
    inst.banned = [i for i in bans(inst) if i != str(player_id)]  # type: ignore[attr-defined]
    registry.save(inst)
